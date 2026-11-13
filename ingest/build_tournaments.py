#!/usr/bin/env python3
"""Merge every tournament feed into tournaments.json.

Feeds live in ingest/feeds/. Each is either
  - JSON: a list of tournament records, or {"source": {...}, "tournaments": [...]}
  - CSV:  one tournament per row, with a header row (see ingest/feeds/submissions.csv)

Steps: validate -> normalize -> geocode from ZIP -> drop past events -> dedupe -> write.
Records that can't be fixed are skipped and listed in the report; nothing is guessed.

Usage:
  python3 ingest/build_tournaments.py            # write tournaments.json
  python3 ingest/build_tournaments.py --check    # report only, don't write
  python3 ingest/build_tournaments.py --keep-past
Standard library only, so it runs anywhere (GitHub Actions included).
"""
import argparse, csv, datetime as dt, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FEEDS = ROOT / "ingest" / "feeds"
CONFIG = ROOT / "ingest" / "config.json"
OUT = ROOT / "tournaments.json"
ZIPS = ROOT / "assets" / "zip"

STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA", "colorado": "CO",
    "connecticut": "CT", "delaware": "DE", "district of columbia": "DC", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD", "massachusetts": "MA",
    "michigan": "MI", "minnesota": "MN", "mississippi": "MS", "missouri": "MO", "montana": "MT",
    "nebraska": "NE", "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}
SPORTS = {"baseball": "baseball", "softball": "softball", "fastpitch": "softball", "fast pitch": "softball",
          "fastpitch softball": "softball"}
SANCTION_ALIASES = {
    "usssa": "usssa", "u.s.s.s.a.": "usssa", "usssa baseball": "usssa", "usssa fastpitch": "usssa",
    "pbr": "pbr", "prep baseball": "pbr", "prep baseball report": "pbr", "pbr tournaments": "pbr", "pbt": "pbr",
    "usa softball": "usa-softball", "asa": "usa-softball", "usa-softball": "usa-softball",
    "perfect game": "perfect-game", "pg": "perfect-game", "perfect-game": "perfect-game",
    "top gun": "top-gun-events", "top gun events": "top-gun-events", "tge": "top-gun-events",
    "top-gun-events": "top-gun-events",
}
AGE_MIN, AGE_MAX = 6, 18


class Skip(Exception):
    pass


def slug(s):
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


def parse_date(v):
    v = str(v or "").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%b %d %Y", "%B %d %Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return dt.datetime.strptime(v, fmt).date()
        except ValueError:
            pass
    raise Skip(f"bad date {v!r}")


def parse_ages(v):
    """'8U - 14U' -> 8U..14U; '13u,14u' -> 13U,14U; 'HS' -> 18U."""
    if isinstance(v, list):
        v = ",".join(map(str, v))
    v = str(v or "").upper().replace("HS", "18U")
    out = set()
    for part in re.split(r"[,/;|]", v):
        nums = [int(n) for n in re.findall(r"(\d{1,2})\s*U?", part)]
        nums = [n for n in nums if AGE_MIN <= n <= AGE_MAX]
        if len(nums) >= 2 and "-" in part:
            out.update(range(min(nums), max(nums) + 1))
        else:
            out.update(nums)
    return [f"{n}U" for n in sorted(out)]


def parse_fee(v):
    """1450 / '$275 - $325' / 'TBA' -> (min, max)"""
    if isinstance(v, (int, float)):
        return float(v), None
    nums = [float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", str(v or ""))]
    if not nums:
        return None, None
    lo, hi = min(nums), max(nums)
    return lo, (hi if hi != lo else None)


def money(x):
    return int(x) if x is not None and float(x).is_integer() else x


class Geo:
    def __init__(self):
        self.shards = {}

    def get(self, z):
        if not re.fullmatch(r"\d{5}", z or ""):
            return None
        if z[0] not in self.shards:
            p = ZIPS / f"{z[0]}.json"
            self.shards[z[0]] = json.loads(p.read_text()) if p.exists() else {}
        return self.shards[z[0]].get(z)


def normalize(r, source, geo, sanction_ids, warn):
    name = " ".join(str(r.get("name") or "").split())
    if not name:
        raise Skip("missing name")
    sport = SPORTS.get(str(r.get("sport") or "").strip().lower())
    if not sport:
        raise Skip(f"unknown sport {r.get('sport')!r}")
    start = parse_date(r.get("start"))
    end = parse_date(r.get("end")) if r.get("end") else start
    if end < start:
        raise Skip("end date before start date")

    raw_s = r.get("sanctions") or r.get("sanction") or ""
    if isinstance(raw_s, str):
        raw_s = [x for x in re.split(r"[,/;|]|\s+\+\s+", raw_s) if x.strip()]
    sanctions = []
    for s in raw_s:
        key = SANCTION_ALIASES.get(s.strip().lower(), slug(s))
        if key not in sanction_ids:
            warn(f"unknown sanctioning body {s!r} (add it to ingest/config.json)")
        if key not in sanctions:
            sanctions.append(key)

    zip_ = re.sub(r"\D", "", str(r.get("zip") or ""))[:5]
    zip_ = zip_.zfill(5) if zip_ else ""
    state = str(r.get("state") or "").strip()
    state = STATES.get(state.lower(), state.upper())
    city = " ".join(str(r.get("city") or "").split())
    g = geo.get(zip_)
    if zip_ and not g:
        warn(f"ZIP {zip_} not found; event won't show in distance searches")
    if g:
        if not city:
            city = g[2]
        if not state:
            state = g[3]
        elif state != g[3]:
            warn(f"ZIP {zip_} is in {g[3]}, record says {state}")
    if not city or len(state) != 2:
        raise Skip("missing city/state (and no usable ZIP)")

    fee, fee_max = parse_fee(r.get("fee"))
    if r.get("feeMax") not in (None, ""):
        fee_max = parse_fee(r.get("feeMax"))[0]
    url = str(r.get("url") or "").strip()
    if url and not re.match(r"^https?://", url, re.I):
        warn(f"dropping non-http url {url!r}")
        url = ""

    src = dict(source)
    if isinstance(r.get("source"), dict):
        src.update(r["source"])
    for k in ("name", "url", "externalId"):
        if r.get(f"source_{k}"):
            src[k] = r[f"source_{k}"]

    out = {
        "id": slug(r.get("id") or f"{name}-{city}-{start.isoformat()}"),
        "name": name,
        "sport": sport,
        "sanction": sanctions[0] if sanctions else "",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "city": city,
        "state": state,
        "zip": zip_,
        "venue": " ".join(str(r.get("venue") or "").split()),
        "address": " ".join(str(r.get("address") or "").split()),
        "ages": parse_ages(r.get("ages")),
        "fee": money(fee),
        "feeMax": money(fee_max),
        "format": " ".join(str(r.get("format") or "").split()),
        "organizer": " ".join(str(r.get("organizer") or "").split()),
        "url": url,
    }
    if len(sanctions) > 1:
        out["sanctions"] = sanctions
    # The site geocodes from zip itself, so lat/lng are only kept when a source gives them.
    if r.get("lat") not in (None, "") and r.get("lng") not in (None, ""):
        out["lat"], out["lng"] = float(r["lat"]), float(r["lng"])
    if src.get("name"):
        out["source"] = {k: v for k, v in src.items() if v}
    return {k: v for k, v in out.items() if v not in ("", None, [])}


NOISE = re.compile(r"\b(19|20)\d{2}\b|\b(the|annual|\d+(st|nd|rd|th)|usssa|pbr|pg|tournament|classic|presented by.*|powered by.*)\b")


def dedupe_key(t):
    place = t.get("zip") or f"{t['city'].lower()}|{t['state']}"
    name = re.sub(r"[^a-z0-9]+", " ", NOISE.sub(" ", t["name"].lower())).strip()
    return (t["sport"], t["start"], place, name)


def merge(a, b):
    """Combine two records for the same event. The first record (feeds are read in file-name
    order) keeps its id, name and values; the second only fills fields the first left blank.
    Age groups and sanctioning bodies are combined."""
    out = dict(a)
    for k, v in b.items():
        if k == "ages":
            out[k] = sorted(set(a.get(k, [])) | set(v), key=lambda s: int(s[:-1]))
        elif out.get(k) in (None, "", []):
            out[k] = v
    sanc = []
    for t in (a, b):
        for s in t.get("sanctions") or [t.get("sanction")]:
            if s and s not in sanc:
                sanc.append(s)
    if sanc:
        out["sanction"] = sanc[0]
        if len(sanc) > 1:
            out["sanctions"] = sanc
    return out


def read_feed(path):
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {}, data
        return data.get("source") or {}, data.get("tournaments") or []
    if path.suffix == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as f:
            return {}, [{k.strip(): (v or "").strip() for k, v in row.items() if k} for row in csv.DictReader(f)]
    return {}, []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report only, don't write tournaments.json")
    ap.add_argument("--keep-past", action="store_true", help="keep events that already ended")
    ap.add_argument("--today", help="override today's date (YYYY-MM-DD), for testing")
    args = ap.parse_args()

    cfg = json.loads(CONFIG.read_text())
    sanction_ids = {s["id"] for s in cfg.get("sanctions", [])}
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    geo = Geo()
    merged, order = {}, []
    skipped, warnings, counts, past, dupes = [], [], {}, 0, 0

    for path in sorted(FEEDS.glob("*")):
        if path.name.startswith("_sample") and not cfg.get("sample"):
            continue
        if path.suffix not in (".json", ".csv"):
            continue
        source, rows = read_feed(path)
        # A hand-made feed can name the automated feeds that supersede it ("replacedBy"); once any of
        # those has events, the hand-made one is skipped so the same tournaments aren't listed twice.
        if path.suffix == ".json":
            meta = json.loads(path.read_text(encoding="utf-8"))
            repl = meta.get("replacedBy", []) if isinstance(meta, dict) else []
            live = [n for n in repl if (FEEDS / n).exists() and read_feed(FEEDS / n)[1]]
            if live:
                print(f"  {path.name}: skipped (replaced by {', '.join(live)})")
                continue
        counts[path.name] = 0
        for i, r in enumerate(rows, 1):
            where = f"{path.name} #{i}"
            def warn(msg, where=where):
                warnings.append(f"{where}: {msg}")
            try:
                t = normalize(r, source, geo, sanction_ids, warn)
            except Skip as e:
                skipped.append(f"{where}: {e} ({str(r.get('name') or '')[:40]})")
                continue
            if not args.keep_past and dt.date.fromisoformat(t["end"]) < today:
                past += 1
                continue
            counts[path.name] += 1
            k = dedupe_key(t)
            if k in merged:
                merged[k] = merge(merged[k], t)
                dupes += 1
            else:
                merged[k] = t
                order.append(k)

    tournaments = sorted((merged[k] for k in order), key=lambda t: (t["start"], t["name"]))
    seen = {}
    for t in tournaments:  # ids must be unique: they are page URLs
        n = seen.get(t["id"], 0)
        seen[t["id"]] = n + 1
        if n:
            t["id"] = f"{t['id']}-{n + 1}"

    out = {
        "_readme": "Generated by ingest/build_tournaments.py from ingest/feeds/. Edit the feeds (or ingest/config.json), not this file, then rerun the script. Each tournament gets a page at /tournaments/<id>.",
        "sample": bool(cfg.get("sample")),
        "updated": today.isoformat(),
        "sports": cfg.get("sports", []),
        "sanctions": cfg.get("sanctions", []),
        "tournaments": tournaments,
    }

    print(f"{len(tournaments)} tournaments written" if not args.check else f"{len(tournaments)} tournaments (check only)")
    for name, c in counts.items():
        print(f"  {name}: {c} kept")
    print(f"  merged duplicates: {dupes} · past events dropped: {past} · skipped: {len(skipped)} · warnings: {len(warnings)}")
    for s in skipped:
        print("  SKIP", s)
    for w in warnings:
        print("  WARN", w)
    if not args.check:
        OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
