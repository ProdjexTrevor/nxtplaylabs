# nxtplaylabs.com

Company site for NXT Play Labs. Five static pages, no build step:

| Page | File |
| --- | --- |
| Home | `index.html` |
| The Grind Pass | `grind-pass.html` |
| About | `about.html` |
| Support | `support.html` |
| Contact | `contact.html` |

Shared styles are in `styles.css`; `site.js` fills the footer year and runs the Copy button on Contact. Product screenshots live in `assets/shots/`.

## Deploy (Vercel)

1. New Vercel project from this repo. Framework preset: **Other**. No build command, output directory `.`.
2. Add the domain **nxtplaylabs.com**.
3. Keep **www.nxtplaylabs.com** on the app project for now — the TestFlight build already on phones still calls the app at www. Move www here (redirect to the bare domain) once that build is retired.

`vercel.json` turns on clean URLs, so `/about` serves `about.html`.

## Editing

The pages share a header and footer. `_build/build.py` regenerates all five from one template:

```
python3 _build/build.py
```

Edit page copy in that script, or edit the HTML directly if you stop using the script.

App links (sign in, privacy, terms, delete account) point at `https://app.nxtplaylabs.com`.
