# Builds assets/zip/<first digit>.json from the MIT-licensed `zipcodes` package data
# (pip download "zipcodes==1.2.0" --no-binary :all:; data last updated Oct 2021).
# Usage: python3 _build/zip_shards.py path/to/zips.json.bz2
import bz2, json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
out = ROOT / "assets" / "zip"
out.mkdir(parents=True, exist_ok=True)
rows = json.loads(bz2.open(sys.argv[1]).read())
shards = {str(i): {} for i in range(10)}
for r in rows:
    if not r.get("active") or not r.get("lat"):
        continue
    z = r["zip_code"]
    shards[z[0]][z] = [round(float(r["lat"]), 3), round(float(r["long"]), 3), r["city"], r["state"]]
for k, v in shards.items():
    (out / f"{k}.json").write_text(json.dumps(v, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    print(k, len(v))
