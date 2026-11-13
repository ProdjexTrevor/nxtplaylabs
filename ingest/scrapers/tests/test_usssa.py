#!/usr/bin/env python3
"""End-to-end test for usssa.py against the local copy in tests/fixtures (no internet needed).

Runs the scraper three times against a local web server:
  1. first run: everything is fetched and parsed
  2. second run: nothing changed, so pages come back 304 and no updates are reported
  3. after editing one event and dropping another from the list: 1 changed, 1 removed
Feeds, cache and report are written to a temporary copy of the repo, never the real one.
Usage: python3 ingest/scrapers/tests/test_usssa.py
"""
import functools, http.server, json, os, pathlib, shutil, subprocess, sys, tempfile, threading, time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent


def main():
    tmp = pathlib.Path(tempfile.mkdtemp())
    repo = tmp / "repo"
    for d in ("ingest", "assets/zip"):
        shutil.copytree(ROOT / d, repo / d, ignore=shutil.ignore_patterns("cache", "reports"))
    for f in (repo / "ingest" / "feeds").glob("usssa-ks*.json"):
        f.unlink()
    site = tmp / "site"
    shutil.copytree(HERE / "fixtures", site)

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    handler = functools.partial(Quiet, directory=str(site))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"

    def run():
        r = subprocess.run([sys.executable, str(repo / "ingest/scrapers/usssa.py"), "--site", "ksfastpitch.usssa.com",
                            "--base-url", base, "--today", "2026-11-13", "--delay", "0"],
                           capture_output=True, text=True)
        print(r.stdout)
        assert r.returncode == 0, r.stderr
        return json.loads((repo / "ingest/reports/usssa-latest.json").read_text())["sites"]["ksfastpitch.usssa.com"]

    fails = []
    def check(cond, msg):
        print(("  ok   " if cond else "  FAIL ") + msg)
        if not cond:
            fails.append(msg)

    # 1. first run
    r = run()
    feed = json.loads((repo / "ingest/feeds/usssa-ksfastpitch.json").read_text())["tournaments"]
    by = {t["name"]: t for t in feed}
    check(r["kept"] == 2, f"kept 2 KC-area events (got {r['kept']})")
    check(r["out_of_area"] == 1 and r["ended"] == 1 and r["no_location"] == 1, "Wichita out of area, old event ended, TBA has no location")
    s = by.get("Spring Slam KC", {})
    check(s.get("start") == "2027-03-12" and s.get("end") == "2027-03-14", "dates from structured data")
    check(s.get("fee") == "$200 - $450" and s.get("ages") == "8U - 18U", "fee range and age groups")
    check(s.get("zip") == "66218" and s.get("city") == "Shawnee" and s.get("address") == "20000 Johnson Drive", "ballpark address parsed")
    check(s.get("venue") == "Mid-America Sports Complex (+1 more)", "first venue named, others counted")
    check(s.get("format", "").startswith("State Qualifier"), f"stature kept as format (got {s.get('format')!r})")
    check(s.get("organizer") == "USSSA KC", "organizer from contact block")
    check(s.get("url") == "https://usssa.com/fastpitch/event_home/?eventID=999001", "register link used as registration URL")
    check(s.get("source", {}).get("url") == "https://ksfastpitch.usssa.com/event/spring-slam-kc/", "credits the real public event page")
    l = by.get("Liberty Classic", {})
    check(l.get("start") == "2027-04-16" and l.get("zip") == "64068" and l.get("ages") == "10U - HS",
          "page without structured data parsed from description + table")
    check(r["new"] == 2, "first run reports 2 new")

    # 2. unchanged
    time.sleep(1.1)
    r = run()
    check(r["not_modified"] >= 2 and r["new"] == 0 and r["changed"] == 0 and r["removed"] == 0,
          f"second run: pages unchanged (304), no updates (not_modified={r['not_modified']})")

    # 3. one fee changes, one event drops off the list
    time.sleep(1.1)
    p = site / "ksfastpitch.usssa.com/event/spring-slam-kc/index.html"
    p.write_text(p.read_text().replace("$200 - $450", "$225 - $475"))
    lst = site / "ksfastpitch.usssa.com/events/index.html"
    lst.write_text(lst.read_text().replace('<a href="/event/liberty-classic/">Liberty Classic</a>', ""))
    r = run()
    ch = r["changes"]
    check(r["changed"] == 1 and ch["changed"][0]["fields"].get("fee") == ["$200 - $450", "$225 - $475"], "fee change detected")
    check(r["removed"] == 1 and ch["removed"][0]["name"] == "Liberty Classic", "removed event detected")

    # 4. the build step accepts the scraper's output
    b = subprocess.run([sys.executable, str(repo / "ingest/build_tournaments.py"), "--check", "--today", "2026-11-13"],
                       capture_output=True, text=True)
    check(b.returncode == 0 and "usssa-ksfastpitch.json: 1 kept" in b.stdout, "build_tournaments.py ingests the scraped feed")
    check("usssa-kc-fastpitch.json: skipped (replaced by usssa-ksfastpitch.json)" in b.stdout,
          "hand-entered USSSA KC feed is replaced by the scraped one")

    srv.shutdown()
    shutil.rmtree(tmp)
    print("\nALL PASSED" if not fails else f"\n{len(fails)} FAILED")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
