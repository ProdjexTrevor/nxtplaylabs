# nxtplaylabs.com

Company site for NXT Play Labs. Six static pages, no build step:

| Page | File |
| --- | --- |
| Home | `index.html` |
| The Grind Pass | `grind-pass.html` |
| Tournament finder | `tournaments.html` |
| About | `about.html` |
| Support | `support.html` |
| Contact | `contact.html` |

Shared styles are in `styles.css`; `site.js` fills the footer year and runs the Copy button on Contact. Product screenshots live in `assets/shots/`.

## Tournament finder

Listings live in `tournaments.json`, which is generated: don't edit it by hand. Add events to a feed in `ingest/feeds/` (JSON, or CSV like `submissions.csv`), then run `python3 ingest/build_tournaments.py`. It validates, cleans up dates/ages/fees, fills city and state from ZIP, merges the same event listed by two organizations, and drops past events. Sports, sanctioning bodies and the sample flag are set in `ingest/config.json`. Each tournament has its own page at `/tournaments/<id>` (one template, `tournament.html`, via the rewrite in `vercel.json`). `docs/tournament-sourcing-plan.md` covers where listings will come from.

 `tournaments.js` renders the finder on `/tournaments` and the "On deck" board on the home page. Each event needs a 5-digit `zip` for the distance search. To add a sport or sanctioning body, add it to `ingest/config.json`; the filter buttons update themselves.

ZIP search uses `assets/zip/0.json`–`9.json` (ZIP → lat/lng, city, state), split by first digit so a search only loads one ~55 KB gzipped file. They're built by `_build/zip_shards.py` from the MIT-licensed `zipcodes` package data (last updated Oct 2021); rerun it with a newer data file to refresh. The state filter lists all 50 states plus DC. Past events hide themselves. Filters are kept in the URL (`/tournaments?sport=softball&state=TX`) so a filtered list can be shared. While `"sample": true` (in `ingest/config.json`) the sample feed is included and the page shows a sample-listings notice; set it to `false` once the listings are real. The finder fetches the JSON, so preview it through a local server (`python3 -m http.server`), not by opening the file directly. A plain local server doesn't do the `/tournaments/<id>` rewrite, so preview a detail page at `/tournament.html?id=<id>`.

## Deploy (Vercel)

1. New Vercel project from this repo. Framework preset: **Other**. No build command, output directory `.`.
2. Add the domain **nxtplaylabs.com**.
3. Keep **www.nxtplaylabs.com** on the app project for now — the TestFlight build already on phones still calls the app at www. Move www here (redirect to the bare domain) once that build is retired.

`vercel.json` turns on clean URLs, so `/about` serves `about.html`.

## Editing

The pages share a header and footer. `_build/build.py` regenerates all six from one template:

```
python3 _build/build.py
```

Edit page copy in that script, or edit the HTML directly if you stop using the script.

App links (sign in, privacy, terms, delete account) point at `https://app.nxtplaylabs.com`.
