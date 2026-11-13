#!/usr/bin/env python3
"""Daily USSSA tournament scraper for nxtplaylabs.com.

For each USSSA state/sport site in usssa_sites.json it:
  1. reads the public event list (/events/, /events/page/2/, ...) to find event pages
  2. fetches each event page (conditional GET, so unchanged pages cost a 304 after the first run)
  3. pulls facts only: name, dates, entry fee, age groups, stature, ballpark + address, organizer
  4. keeps events whose ballpark is within radius_miles of center_zip and that haven't ended
  5. writes ingest/feeds/usssa-<site>.json and a change report (new / changed / removed events)

Polite by design: honors robots.txt, identifies itself with a contact address, waits
delay_seconds between requests, backs off on 429/503, and only reads public event pages.
If a site can't be reached, its previous feed is left untouched.

Usage:
  python3 ingest/scrapers/usssa.py              # all sites
  python3 ingest/scrapers/usssa.py --site mobaseball.usssa.com
  python3 ingest/scrapers/usssa.py --base-url http://localhost:8800   # test against a local copy
Then run ingest/build_tournaments.py to rebuild tournaments.json.

Exit codes: 0 = ran (see report), 2 = every site failed.
Standard library only.
"""
import argparse, datetime as dt, email.utils, gzip, hashlib, html, json, math, pathlib, re, sys, time
import urllib.error, urllib.parse, urllib.request, urllib.robotparser
from html.parser import HTMLParser

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CONFIG = HERE / "usssa_sites.json"
FEEDS = ROOT / "ingest" / "feeds"
CACHE = ROOT / "ingest" / "cache" / "usssa"
REPORTS = ROOT / "ingest" / "reports"
ZIPS = ROOT / "assets" / "zip"

EVENT_HREF = re.compile(r"""href=["']((?:https?://[^"'/]+)?/event/([A-Za-z0-9][A-Za-z0-9._~%-]*)/?)["']""", re.I)
COMPARE_FIELDS = ("name", "start", "end", "fee", "ages", "venue", "address", "city", "state", "zip", "format", "organizer", "url")


# ---------------------------------------------------------------- HTTP
class Fetcher:
    def __init__(self, cfg, log):
        self.ua = cfg["user_agent"]
        self.delay = max(1.0, float(cfg.get("delay_seconds", 2)))
        self.robots = {}
        self.last = 0.0
        self.log = log
        self.requests = 0

    def _robots(self, base):
        if base not in self.robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                status, body, _ = self._get(base + "/robots.txt", {}, check_robots=False)
                rp.parse(body.splitlines() if status == 200 else [])
            except Exception:
                rp.parse([])  # unreachable robots.txt: treat as no rules, like most crawlers
            self.robots[base] = rp
        return self.robots[base]

    def _get(self, url, headers, check_robots=True):
        if check_robots:
            p = urllib.parse.urlsplit(url)
            if not self._robots(f"{p.scheme}://{p.netloc}").can_fetch(self.ua, url):
                return "robots", "", {}
        wait = self.last + self.delay - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": self.ua, "Accept-Encoding": "gzip",
                                                   "Accept": "text/html,application/xhtml+xml", **headers})
        for attempt in range(3):
            self.last = time.monotonic()
            self.requests += 1
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    raw = r.read()
                    if r.headers.get("Content-Encoding") == "gzip":
                        raw = gzip.decompress(raw)
                    return r.status, raw.decode(r.headers.get_content_charset() or "utf-8", "replace"), dict(r.headers)
            except urllib.error.HTTPError as e:
                if e.code == 304:
                    return 304, "", dict(e.headers)
                if e.code in (429, 503) and attempt < 2:
                    retry = e.headers.get("Retry-After")
                    pause = int(retry) if retry and retry.isdigit() else 30 * (attempt + 1)
                    self.log(f"  {e.code} on {url}; waiting {pause}s")
                    time.sleep(min(pause, 300))
                    continue
                return e.code, "", dict(e.headers)
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if attempt < 2:
                    time.sleep(10 * (attempt + 1))
                    continue
                raise
        return 599, "", {}

    def get(self, url, etag=None, last_modified=None):
        h = {}
        if etag:
            h["If-None-Match"] = etag
        if last_modified:
            h["If-Modified-Since"] = last_modified
        return self._get(url, h)


# ---------------------------------------------------------------- parsing
class TextAndTables(HTMLParser):
    """Collects visible text as lines, table rows as cell lists, JSON-LD blocks, <title> and meta tags."""
    BLOCK = {"p", "div", "li", "ul", "ol", "tr", "table", "section", "article", "header", "footer",
             "h1", "h2", "h3", "h4", "h5", "h6", "br", "dt", "dd", "dl", "span"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines, self.cur = [], []
        self.rows, self.row, self.cell = [], None, None
        self.ld, self.in_ld, self.ld_buf = [], False, []
        self.skip = 0
        self.title, self.in_title = "", False
        self.meta = {}
        self.links = []  # (href, text)
        self.a_href, self.a_text = None, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script" and (a.get("type") or "").lower() == "application/ld+json":
            self.in_ld, self.ld_buf = True, []
            return
        if tag in ("script", "style", "noscript", "svg"):
            self.skip += 1
            return
        if tag == "title":
            self.in_title = True
        if tag == "meta" and a.get("content"):
            k = (a.get("name") or a.get("property") or "").lower()
            if k:
                self.meta[k] = a["content"]
        if tag == "a":
            self.a_href, self.a_text = a.get("href"), []
        if tag == "tr":
            self.row = []
        if tag in ("td", "th"):
            self.cell = []
        if tag in self.BLOCK:
            self._flush()

    def handle_endtag(self, tag):
        if tag == "script" and self.in_ld:
            self.in_ld = False
            self.ld.append("".join(self.ld_buf))
            return
        if tag in ("script", "style", "noscript", "svg"):
            self.skip = max(0, self.skip - 1)
            return
        if tag == "title":
            self.in_title = False
        if tag == "a" and self.a_href is not None:
            self.links.append((self.a_href, " ".join("".join(self.a_text).split())))
            self.a_href = None
        if tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        if tag == "tr" and self.row is not None:
            if any(self.row):
                self.rows.append(self.row)
            self.row = None
        if tag in self.BLOCK:
            self._flush()

    def handle_data(self, data):
        if self.in_ld:
            self.ld_buf.append(data)
            return
        if self.skip:
            return
        if self.in_title:
            self.title += data
        if self.cell is not None:
            self.cell.append(data)
        if self.a_href is not None:
            self.a_text.append(data)
        self.cur.append(data)

    def _flush(self):
        t = " ".join("".join(self.cur).split())
        if t:
            self.lines.append(t)
        self.cur = []

    def close(self):
        super().close()
        self._flush()


def _ld_events(blocks):
    out = []
    def walk(o):
        if isinstance(o, list):
            for x in o:
                walk(x)
        elif isinstance(o, dict):
            if o.get("startDate") and o.get("name"):
                out.append(o)
            for v in o.values():
                if isinstance(v, (dict, list)):
                    walk(v)
    for b in blocks:
        try:
            walk(json.loads(b))
        except ValueError:
            continue
    return out


ADDR = re.compile(r"^(?P<street>.+?),\s*(?P<city>[^,]+?),\s*(?P<state>[A-Z]{2}),?\s*(?P<zip>\d{5})(?:-\d{4})?$")


def _after_label(text, label, pattern):
    m = re.search(label + r"\s*:?\s*" + pattern, text, re.I)
    return m.group(1).strip() if m else ""


def parse_event(page, url, site, public_url=None):
    public_url = public_url or url
    p = TextAndTables()
    p.feed(page)
    p.close()
    text = "\n".join(p.lines)
    flat = " ".join(p.lines)

    ld = (_ld_events(p.ld) or [{}])[0]
    rec = {"name": html.unescape(str(ld.get("name") or "")).strip()}

    # "The X is a USSSA Baseball event in Liberty, MO and will be held from 06/12/2026 to 06/14/2026"
    desc = p.meta.get("description", "") + " " + flat
    m = re.search(r"is a USSSA [\w ]+? event in (.+?) and will be held from (\d{1,2}/\d{1,2}/\d{4}) to (\d{1,2}/\d{1,2}/\d{4})", desc)
    if ld.get("startDate"):
        rec["start"] = str(ld["startDate"])[:10]
        rec["end"] = str(ld.get("endDate") or ld["startDate"])[:10]
    elif m:
        rec["start"] = dt.datetime.strptime(m.group(2), "%m/%d/%Y").date().isoformat()
        rec["end"] = dt.datetime.strptime(m.group(3), "%m/%d/%Y").date().isoformat()
    if not rec["name"]:
        t = re.sub(r"\s+-\s+USSSA.*$", "", " ".join(p.title.split()))
        rec["name"] = re.sub(r"\s*\(\d{4}\)\s*(-.*)?$", "", t).strip()

    rec["fee"] = _after_label(flat, r"Entry Fee", r"(\$[\d,]+(?:\.\d\d)?(?:\s*-\s*\$[\d,]+(?:\.\d\d)?)?)")
    rec["ages"] = _after_label(flat, r"Age Groups", r"(\d{1,2}U\s*-\s*(?:\d{1,2}U|HS))")
    stature = _after_label(text, r"\nStature", r"([^\n]{2,60})") or _after_label(flat, r"Stature", r"([A-Za-z][A-Za-z '/&.-]{2,40}?)(?=\s+(?:Age Groups|Entry Fee|Event Details|Gate Fee|Admission)|$)")
    gg = _after_label(flat, r"Game Guarantee", r"(\d+)")
    rec["format"] = "; ".join(x for x in (stature, f"{gg}-game guarantee" if gg else "") if x)

    # Ballparks: table rows whose address cell looks like "street, City, ST, 12345"
    venues = []
    for row in p.rows:
        for i, cell in enumerate(row[1:], 1):
            a = ADDR.match(cell)
            if a and row[0] and not row[0].lower().startswith("venue"):
                venues.append((row[0], a))
                break
    loc = ld.get("location") if isinstance(ld.get("location"), dict) else {}
    addr = loc.get("address") if isinstance(loc.get("address"), dict) else {}
    if not venues and addr.get("streetAddress"):
        a = ADDR.match(str(addr["streetAddress"]))
        if a:
            venues.append((loc.get("name") or "", a))
    if venues:
        name0, a = venues[0]
        rec.update(venue=name0 + (f" (+{len(venues) - 1} more)" if len(venues) > 1 else ""),
                   address=a["street"], city=a["city"], state=a["state"], zip=a["zip"])
    elif m:  # fall back to the city named in the description
        cm = re.match(r"(.+?),\s*([A-Z]{2})$", m.group(1).strip())
        if cm:
            rec.update(city=cm.group(1), state=cm.group(2))

    org = re.search(r"please contact:\s*\n?([^\n]{2,80})", text, re.I)
    if org and not re.search(r"@|\d{3}[.\-) ]\d{3}", org.group(1)):
        rec["organizer"] = org.group(1).strip()

    reg = next((urllib.parse.urljoin(public_url, h) for h, t in p.links if t.lower() == "register" and h and not h.startswith("#")), "")
    rec["url"] = reg if reg.startswith("http") else public_url
    rec["sport"] = site["sport"]
    rec["sanction"] = "usssa"
    rec["source"] = {"name": site.get("label") or site["host"], "url": public_url}
    return {k: v for k, v in rec.items() if v not in ("", None)}


def list_event_links(page, base, host):
    """Event page links on this site, as (slug, url-to-fetch). Links to other sites are ignored."""
    seen, out = set(), []
    ok = {urllib.parse.urlsplit(base).netloc, host}
    for full, slug in EVENT_HREF.findall(page):
        parts = urllib.parse.urlsplit(urllib.parse.urljoin(base + "/", full))
        if parts.netloc not in ok:
            continue
        u = base + parts.path.rstrip("/") + "/"  # same path, fetched from base (the real site or a test mirror)
        if u not in seen:
            seen.add(u)
            out.append((slug.lower(), u))
    return out


# ---------------------------------------------------------------- geo
class Geo:
    def __init__(self):
        self.s = {}

    def get(self, z):
        if not re.fullmatch(r"\d{5}", z or ""):
            return None
        if z[0] not in self.s:
            f = ZIPS / f"{z[0]}.json"
            self.s[z[0]] = json.loads(f.read_text()) if f.exists() else {}
        return self.s[z[0]].get(z)


def miles(a, b):
    r = math.radians
    h = math.sin(r(b[0] - a[0]) / 2) ** 2 + math.cos(r(a[0])) * math.cos(r(b[0])) * math.sin(r(b[1] - a[1]) / 2) ** 2
    return 2 * 3958.8 * math.asin(min(1, math.sqrt(h)))


# ---------------------------------------------------------------- run
def site_slug(host):
    return host.split(".")[0]


def run_site(site, cfg, f, geo, center, today, base_override, log, limit=None):
    host = site["host"]
    base = base_override.rstrip("/") + "/" + host if base_override else f"https://{host}"
    cache_dir = CACHE / site_slug(host)
    cache_dir.mkdir(parents=True, exist_ok=True)
    stats = {"list_pages": 0, "event_pages": 0, "fetched": 0, "not_modified": 0, "kept": 0,
             "out_of_area": 0, "ended": 0, "no_location": 0, "errors": 0, "robots_blocked": 0}

    # 1. event list
    links, seen = [], set()
    for n in range(1, int(cfg.get("max_list_pages", 40)) + 1):
        url = f"{base}/events/" if n == 1 else f"{base}/events/page/{n}/"
        status, body, _ = f.get(url)
        if status == "robots":
            stats["robots_blocked"] += 1
            log(f"  robots.txt disallows {url}; skipping site")
            return None, stats
        if status != 200:
            if n == 1:
                raise RuntimeError(f"event list returned {status}")
            break
        stats["list_pages"] += 1
        new = [(s, u) for s, u in list_event_links(body, base, host) if u not in seen]
        if not new:
            break
        for s, u in new:
            seen.add(u)
            links.append((s, u))
    log(f"  {len(links)} event pages listed across {stats['list_pages']} list pages")

    # 2. event pages
    records = []
    budget = int(cfg.get("max_event_fetches", 1500))
    for slug, url in links:
        if limit and len(records) >= limit:
            log(f"  stopping at --limit {limit}")
            break
        stats["event_pages"] += 1
        cpath = cache_dir / (re.sub(r"[^a-z0-9._-]", "_", slug)[:120] + ".json")
        cached = json.loads(cpath.read_text()) if cpath.exists() else None
        rec = None
        if cached and cached.get("record", {}).get("end") and cached["record"]["end"] < today.isoformat():
            rec = cached["record"]  # already over; no need to ask again
        elif budget <= 0:
            rec = cached["record"] if cached else None
        else:
            budget -= 1
            try:
                status, body, headers = f.get(url, (cached or {}).get("etag"), (cached or {}).get("last_modified"))
            except Exception as e:
                stats["errors"] += 1
                log(f"  error {url}: {e}")
                rec = cached["record"] if cached else None
                status = None
            if status == 304 and cached:
                stats["not_modified"] += 1
                rec = cached["record"]
            elif status == 200:
                stats["fetched"] += 1
                digest = hashlib.sha256(body.encode()).hexdigest()
                if cached and cached.get("sha256") == digest:
                    rec = cached["record"]
                else:
                    try:
                        rec = parse_event(body, url, site, f"https://{host}/event/{slug}/")
                    except Exception as e:  # one odd page shouldn't sink the run
                        stats["errors"] += 1
                        log(f"  parse error {url}: {e}")
                        rec = cached["record"] if cached else None
                cpath.write_text(json.dumps({"url": url, "etag": headers.get("ETag") or headers.get("Etag"),
                                             "last_modified": headers.get("Last-Modified"), "sha256": digest,
                                             "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                                             "record": rec}, indent=1))
            elif status == "robots":
                stats["robots_blocked"] += 1
            elif status is not None:
                stats["errors"] += 1
                log(f"  HTTP {status} {url}")
                rec = cached["record"] if cached else None
        if not rec or not rec.get("start"):
            continue
        if rec.get("end", rec["start"]) < today.isoformat():
            stats["ended"] += 1
            continue
        g = geo.get(rec.get("zip"))
        if not g:
            stats["no_location"] += 1
            continue
        if miles(center, (g[0], g[1])) > float(cfg["radius_miles"]):
            stats["out_of_area"] += 1
            continue
        rec = dict(rec, source=dict(rec.get("source", {}), externalId=slug))
        records.append(rec)
    stats["kept"] = len(records)
    return records, stats


def diff(old, new):
    key = lambda r: (r.get("source") or {}).get("url") or r.get("name")
    o, n = {key(r): r for r in old}, {key(r): r for r in new}
    changes = {"new": [], "changed": [], "removed": []}
    for k, r in n.items():
        if k not in o:
            changes["new"].append({"name": r.get("name"), "start": r.get("start"), "url": k})
        else:
            fields = [f for f in COMPARE_FIELDS if o[k].get(f) != r.get(f)]
            if fields:
                changes["changed"].append({"name": r.get("name"), "url": k,
                                           "fields": {f: [o[k].get(f), r.get(f)] for f in fields}})
    for k, r in o.items():
        if k not in n:
            changes["removed"].append({"name": r.get("name"), "start": r.get("start"), "url": k})
    return changes


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--site", action="append", help="only this host (repeatable)")
    ap.add_argument("--base-url", help="fetch from a local mirror instead of https://<host> (testing)")
    ap.add_argument("--today", help="YYYY-MM-DD (testing)")
    ap.add_argument("--delay", type=float, help="override delay_seconds (testing)")
    ap.add_argument("--limit", type=int, help="stop after this many kept events in total (smoke test)")
    ap.add_argument("--out", help="write feeds and report to this folder instead of ingest/feeds + ingest/reports")
    args = ap.parse_args()

    cfg = json.loads(CONFIG.read_text())
    if args.delay is not None:
        cfg["delay_seconds"] = args.delay
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    geo = Geo()
    c = geo.get(cfg["center_zip"])
    if not c:
        sys.exit(f"center_zip {cfg['center_zip']} not found")
    center = (c[0], c[1])
    log = lambda s: print(s, flush=True)
    f = Fetcher(cfg, log)
    if args.base_url:
        f.delay = cfg["delay_seconds"]  # robots.txt is read from the mirror too

    sites = [s for s in cfg["sites"] if not args.site or s["host"] in args.site]
    report = {"ran_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
              "center_zip": cfg["center_zip"], "radius_miles": cfg["radius_miles"], "sites": {}}
    feeds_dir = pathlib.Path(args.out) if args.out else FEEDS
    reports_dir = pathlib.Path(args.out) if args.out else REPORTS
    feeds_dir.mkdir(parents=True, exist_ok=True)
    failures, total = 0, 0
    for site in sites:
        if args.limit and total >= args.limit:
            break
        host = site["host"]
        log(f"{host}")
        feed_path = feeds_dir / f"usssa-{site_slug(host)}.json"
        old = json.loads(feed_path.read_text()).get("tournaments", []) if feed_path.exists() else []
        try:
            records, stats = run_site(site, cfg, f, geo, center, today, args.base_url, log,
                                      (args.limit - total) if args.limit else None)
        except Exception as e:
            failures += 1
            log(f"  FAILED: {e}; keeping the previous feed")
            report["sites"][host] = {"status": "failed", "error": str(e)}
            continue
        if records is None:
            report["sites"][host] = {"status": "skipped", **stats}
            continue
        total += len(records)
        changes = diff(old, records)
        feed_path.write_text(json.dumps({
            "source": {"name": site.get("label") or host, "url": f"https://{host}/events/"},
            "generated_by": "ingest/scrapers/usssa.py",
            "tournaments": sorted(records, key=lambda r: (r["start"], r["name"])),
        }, indent=2) + "\n")
        report["sites"][host] = {"status": "ok", **stats,
                                 "new": len(changes["new"]), "changed": len(changes["changed"]),
                                 "removed": len(changes["removed"]), "changes": changes}
        log(f"  kept {stats['kept']} · new {len(changes['new'])} · changed {len(changes['changed'])} · "
            f"removed {len(changes['removed'])} · fetched {stats['fetched']} · unchanged {stats['not_modified']} · "
            f"out of area {stats['out_of_area']} · errors {stats['errors']}")

    ok = [s for s in report["sites"].values() if s.get("status") == "ok"]
    report["summary"] = {
        "sites_ok": len(ok), "sites_failed": failures, "requests": f.requests,
        "new": sum(s["new"] for s in ok), "changed": sum(s["changed"] for s in ok), "removed": sum(s["removed"] for s in ok),
        "has_updates": any(s["new"] or s["changed"] or s["removed"] for s in ok),
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "usssa-latest.json").write_text(json.dumps(report, indent=2) + "\n")
    s = report["summary"]
    log(f"done: {s['sites_ok']} sites ok, {s['sites_failed']} failed · {s['new']} new, {s['changed']} changed, "
        f"{s['removed']} removed · {s['requests']} requests · report: {reports_dir / 'usssa-latest.json'}")
    return 2 if sites and failures == len(sites) else 0


if __name__ == "__main__":
    sys.exit(main())
