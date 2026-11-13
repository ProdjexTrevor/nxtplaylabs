# Tournament Sourcing Plan

How nxtplaylabs.com can pull baseball and softball tournaments from USSSA, PBR, USA Softball, Top Gun, Perfect Game and others into one finder.

*Researched November 13, 2026. Not legal advice: have a lawyer review the approach before any automated collection goes live.*

## Summary

There is no shared feed of tournaments. Each organization publishes events its own way, and most say nothing explicit about reuse, so **the plan is permission-first**:

1. **Get organizers to send us events.** That means a proper "Submit a tournament" form and a spreadsheet (CSV) import, plus direct outreach to the big organizations asking for a data feed or permission to list their events. This is the only route that's clearly allowed for every source, and it's how the existing directories (BaseballConnected, SoftballConnected) grow.
2. **Automate only where we have permission or a published feed.** USSSA's event pages are the most structured and the biggest prize. USA Softball's national calendar already offers a calendar (.ics) export.
3. **Never copy Perfect Game.** Their site says plainly that their information can't be posted elsewhere without written consent. We can link to their schedule, nothing more, unless they agree in writing.

For every listing we show only the facts (name, dates, location, cost, age groups, sanctioning body), credit the source, and send people to the organizer's own page to register.

The ingestion pipeline (`ingest/` in this repo) is already built to merge any number of sources into the site's `tournaments.json`. Each new source is just a file of tournament records in the shared format.

## Source by source

| Source | Sport | How events are published | Structure | Reuse terms | Approach |
|---|---|---|---|---|---|
| **USSSA** | Baseball + fastpitch | A site per state and sport (e.g. `txbaseball.usssa.com`, `iafastpitch.usssa.com`), each with an `/events/` list and `/event/<slug>` detail pages. A central event search takes ZIP + radius. | High: dates, entry fee (often a range), "stature" (e.g. State Qualifier), age groups, divisions table, ballpark names + street addresses, director contact. | Terms of use cover participation and waivers. They don't address copying or automated access, but the footer says "All Rights Reserved." Couldn't check robots.txt (blocked from here). | **Ask USSSA national for a feed or permission** (baseball and fastpitch each have a national VP). Until then, list USSSA events by hand or by organizer submission, linking to the official page. |
| **PBR (Prep Baseball)** | Baseball | Tournaments live at `tournaments.prepbaseballreport.com/events/<slug>`. Run with Bullpen Tournaments on the Playbook365 platform (`pbt.playbook365.com`). | Medium: age group, division, game guarantee, price, bat type, city. | Not reviewed; assume all rights reserved. | **Email PBR Tournaments** (pbrtournaments@prepbaseballreport.com) for a feed. Playbook365 may be able to export one on PBR's behalf. |
| **USA Softball** | Softball | The national calendar (`usasoftball.com/events`) offers **.ics calendar export**, but it covers national championships and national-office events only. Most youth tournaments run through state/metro associations, with a national listing on TournamentUSA. | Calendar: name, dates, city/venue. Association sites vary. | Not reviewed. | **Use the .ics export for nationals.** Then contact state/metro associations one at a time, starting with our launch region. |
| **Top Gun** (2 different groups, confirm which you mean) | Fastpitch | **Top Gun Events** (Kansas City) lists tournaments on `topgunevents.com` and runs registration on tagup (`app.tagup.com/topgun/...`). **Top Gun-USA** (Carolinas) runs events co-sanctioned with USSSA, so those already show up on USSSA's state sites. | Top Gun Events: name, dates, city, age groups, "Application Only". | Not reviewed. | **Partner with Top Gun Events.** One person, Jeremy McDowell, is listed as Top Gun Events' CEO and also, in a USSSA staff directory, as a USSSA VP of Fast Pitch. If that's still current, it's a warm intro to both. |
| **Perfect Game** | Baseball + softball | Schedule pages on `perfectgame.org` (e.g. `Schedule/GroupedEvents.aspx?gid=…`). | High: entry fee, game guarantee, age eligibility, bat rules, gate fees. | **Explicitly prohibited.** The FAQ says their information is copyrighted and can't be posted on other sites. The footer bars reproducing it without written consent. | **Link only**, or request written permission. Do not scrape. |
| **BaseballConnected / SoftballConnected** | Both | Free directory where organizers list their own events. SoftballConnected covers IL, IN, KY, MO, OH and TN. | Name, dates, ages, price, link to organizer. | Their compilation is theirs. | **Competitor, not a source.** Shows organizers will self-list if it's free. A data partnership is possible. |
| **The Alliance Fastpitch** | Softball | A national schedule across many sanctioning bodies, with AthletesGoLive event IDs. | Name, dates, city/state, ages, organizer, event type. | Not reviewed. | Possible partner. Their AGL IDs could help match duplicate events. |

Other names to add in later rounds: Triple Crown Sports, Prospect Wire, NSA, Game 7, JP Sports and Five Tool. Many of these are tournament *companies* that also hold a sanction (USSSA, PBR) for their events, which is why the same event often shows up on two sites.

## Legal and terms of use

*This is a summary of risk, not legal advice.*

- **Facts vs. expression.** Basic facts like a tournament's name, dates, location and fee are generally not protected by copyright, but descriptions, photos, logos and the way a site arranges its listings can be. Show facts only, in our own layout, and never copy descriptions or logos.
- **Site terms can still forbid it.** Even when content isn't copyrighted, a site's terms of use can prohibit copying or automated access. Perfect Game's terms do; USSSA's don't say either way. Permission removes the question.
- **Rules for any automated collection (once permitted):** honor robots.txt, identify our crawler with a contact email, rate-limit to a few requests a minute, and only fetch public event pages, never logged-in areas or player data.
- **Credit and take-down.** Every listing names its source and links to the official page ("Listing from USSSA"; the detail page already supports this). Add a "Report a problem / remove this listing" link and honor removals within a day.
- **Minors.** Collect events only, never rosters, player names or stats. The Grind Pass's safety promises extend to this.

## Data model

Every source is converted into one record format before it reaches the site. These fields extend today's `tournaments.json`:

| Field | Type | Notes |
|---|---|---|
| `id` | string | URL-safe and unique; becomes `/tournaments/<id>`. Built from name + city + start date when the source has no ID. |
| `name` | string | |
| `sport` | `baseball` \| `softball` | Fastpitch maps to softball. |
| `sanction` | string | Main sanctioning body id (`usssa`, `pbr`, `usa-softball`, `perfect-game`, `top-gun-events`…). |
| `sanctions` | string[] | Optional. All bodies, for co-sanctioned events (e.g. USSSA + Top Gun-USA). |
| `start`, `end` | `YYYY-MM-DD` | |
| `venue`, `address`, `city`, `state`, `zip` | string | `zip` drives the distance search. |
| `lat`, `lng` | number | Optional; the site looks them up from the ZIP when they're missing. |
| `ages` | string[] | Normalized to `8U`…`18U`; "HS" maps to `18U`. |
| `fee`, `feeMax` | number | Entry fee per team; `feeMax` when the source gives a range. |
| `format` | string | e.g. "4-game guarantee". |
| `organizer` | string | Tournament director or company. |
| `url` | string | Registration / official page. |
| `source` | object | `{ name, url, externalId, fetchedAt }`: where the record came from. |

**Duplicates:** the same event often appears on two sites. Records are matched on sport + start date + ZIP (or city/state) + a cleaned-up name. When two match, they become one listing: the first source keeps its name, page URL and values, the second only fills in blanks, and the age groups and sanctioning bodies are combined.

## Pipeline

```
 sources                     adapters (one per source)          ingest/feeds/*.json|csv
 ─────────                   ─────────────────────────          ───────────────────────
 Organizer form / CSV  ───►  csv import                    ───►  submissions.csv
 USA Softball .ics     ───►  ics adapter                   ───►  usa-softball.json
 USSSA (w/ permission) ───►  usssa adapter                 ───►  usssa.json
 Partner feeds (PBR,…) ───►  feed adapter                  ───►  pbr.json
                                                                    │
                                     ingest/build_tournaments.py ◄──┘
                                     validate → normalize → geocode (ZIP) → dedupe → drop past
                                                                    │
                                                                    ▼
                                                  tournaments.json  →  git push  →  Vercel deploy
```

- **Where it runs:** a nightly GitHub Actions job runs the adapters and the build step, then commits `tournaments.json` if it changed. Vercel redeploys on push. No server needed.
- **What's built now:** `ingest/build_tournaments.py` (validate, normalize, geocode, dedupe, merge) plus the CSV import, tested with a sample file. Source adapters come next, one per source as permission comes in.
- **When to move to a database:** the site loads `tournaments.json` in one go. Past roughly 2,000 upcoming events it gets heavy. At that point, move listings into Supabase (already used by The Grind Pass) and have the finder query by state or radius, or split the JSON by state.
- **SEO later:** detail pages are filled in by the browser today. Once listings are real, generate a static page per tournament at build time so search engines index them fully.

## Phased rollout

**Phase 1: launch with real listings (next 2 weeks)**
- Pick a launch region (suggestion: the states where Grind Pass teams play).
- Replace the "Submit a tournament" email link with a real form that writes to the CSV/Supabase.
- Hand-enter 50–100 upcoming events for the region from USSSA state sites and organizer pages: facts only, each linking to the official page. Set `"sample": false`.
- Send the outreach emails below.

**Phase 2: permissions and feeds (weeks 2–6)**
- USSSA national (baseball + fastpitch): ask for a feed, an API key or written permission to index public event pages.
- PBR Tournaments, Top Gun Events, and USA Softball state associations in the launch region: same ask.
- Perfect Game: ask for written permission or a partner feed; otherwise link to their schedule.
- Pitch to organizers: free listings, a link straight to their registration, and exposure to Grind Pass teams.

**Phase 3: automate (weeks 4–8)**
- Build an adapter per approved source; nightly job; alert when a source's page layout changes.
- Show "Updated <date>" and source credit on each listing; add the "Report a problem" link.

**Phase 4: scale (when listings pass ~2,000)**
- Move to Supabase, add static per-event pages and nationwide coverage, and track events that disappear or move.

### Outreach list

| Organization | Contact found | Ask |
|---|---|---|
| USSSA Baseball / Fastpitch | National program directors (usssa.com) | Feed or permission to index public event pages |
| PBR Tournaments | pbrtournaments@prepbaseballreport.com | Event feed (Playbook365 export) |
| Top Gun Events | info@topgunevents.com | Event feed from tagup; partnership |
| USA Softball | State/metro association commissioners | Tournament lists; TournamentUSA access |
| Perfect Game | perfectgame.org | Written permission or link-only |

## Open questions for you

1. **Top Gun:** Top Gun Events (Kansas City fastpitch) or Top Gun-USA (Carolinas, co-sanctioned with USSSA)?
2. **Launch region:** which states first?
3. **Grind Pass tie-in:** should the finder stay public-only, or should teams also see tournaments in the app?

## Sources

- [USSSA Texas Baseball event page (example of event detail fields)](https://txbaseball.usssa.com/event/beaumont-battle-for-the-belts-nit-belts-rings/)
- [USSSA North Carolina Baseball events list](https://ncbaseball.usssa.com/events/)
- [USSSA Iowa Fastpitch](https://iafastpitch.usssa.com/)
- [USSSA event search](https://ufe.usssa.com/)
- [USSSA terms of use](https://usssa.com/terms-of-use)
- [USSSA national program directors](https://v10.usssa.com/soccer/NationalProgramDirectors/)
- [PBR Tournaments: Why PBR Tournaments](https://pbt.playbook365.com/page/why-pbr-tournaments)
- [PBR partnership with Bullpen Tournaments](https://www.prepbaseball.com/news/PBR/PBR-Partners-with-Bullpen-Tournaments-1320569874)
- [USA Softball events calendar](https://www.usasoftball.com/events/list)
- [USA Softball FAQ (TournamentUSA, local associations)](https://archive.teamusa.com/usa-softball/_/linka30b.html)
- [Top Gun Events FAQ (tagup)](https://topgunevents.com/?p=1482)
- [Top Gun Events tournaments](https://topgunevents.com/?p=9908)
- [Top Gun Events leadership](https://topgunevents.com/author/tgestaff)
- [Perfect Game FAQ](https://www.perfectgame.org/faq.aspx)
- [BaseballConnected FAQ](https://baseballconnected.com/faq)
- [The Alliance Fastpitch national schedule](https://thealliancefastpitch.com/2021-events)
