# Seattle Ferry Tracker

Real-time WSDOT Seattle ↔ Bainbridge Island ferry tracker. Single self-contained HTML file — no build step, no dependencies to install.

**Live app:** https://demetrearges206.github.io/seattle-ferry-tracker/ferry.html

## What it does

- **Current Sailing card** — shows the active or next departure with live vessel status (At Dock / Sailing / Arriving), ETA countdown pill, animated progress track with ferry icon that moves in real time, and return departure time
- **Direction toggle** — switch between Seattle → Bainbridge and Bainbridge → Seattle
- **Upcoming sailings** — next 3 departures with scheduled arrival times
- **Full schedule toggle** — expand to see the complete day's timetable
- **Live Vessels map** — interactive Leaflet map with per-vessel color-coded markers that rotate by heading; updates every 60 seconds
- **Alerts** — active WSDOT service bulletins

## Data sources

All data from the [Washington State Ferries Traveler API](https://www.wsdot.wa.gov/ferries/api/vessels/documentation/).

The API key is a **query parameter** (`?apiaccesscode={key}`), not a path segment.

| Endpoint | Used for |
|----------|----------|
| `vessellocations?apiaccesscode={key}` | Live vessel positions, heading, speed, ETA, at-dock status |
| `scheduletoday/{dep_id}/{arr_id}/false?apiaccesscode={key}` | Today's departure/arrival timetable |
| `schedulebulletins?apiaccesscode={key}` | Service alerts and bulletins |
| `terminalwaittimes?apiaccesscode={key}` | Drive-up and reservation wait times |

Terminal IDs: Seattle = `7`, Bainbridge Island = `3`.

## Local dev

Open `ferry.html` in a browser. All assets are inlined (Leaflet 1.9.4, CSS, JS) — no install needed.

Live API data requires `http://` (not `file://`) to avoid CORS on some browsers:

```bash
npx serve .
# or
python3 -m http.server 8080
```

Then open `http://localhost:8080/ferry.html`.

## Deploy to GitHub Pages

1. Push `ferry.html` to the `main` branch
2. Go to **Settings → Pages → Deploy from branch → main → / (root)**
3. Save — Pages builds in ~30s
4. Live at `https://demetrearges206.github.io/seattle-ferry-tracker/ferry.html`

The deploy workflow (`.github/workflows/pages.yml`) automatically inlines the Inter font as base64 at build time.

## Build history

| Build | Changes |
|-------|---------|
| r31 | Inlined Leaflet 1.9.4; progressive cache-first boot; improved map contrast |
| r32 | Fixed "Stale · just now" on load; featured card redesign; `partial` status state |
| r33 | Vessel/badge above eyebrow; Terminal Wait Times moved below Live Vessels |
| r34 | Removed broken mini-map; fixed upcoming arrival times contaminated by live ETA |
| r35 | Map above Upcoming section; countdown pill "to arrival" sublabel; return dep in footer |
| r36–r43 | Various stability fixes; direction toggle; alerts section |
| r44–r50 | Custom ferry SVG map markers; per-vessel stable color palette; vessel strip redesign |
| r51 | Card redesign from Figma: progress track at bottom, SEA/BI terminal labels, ferry icon on track |
| r52 | Ferry icon moves along track based on live ETA; `computeBarPct()` driven by `cdTarget` |
| r53 | Fixed `lvApproaching` — vessel on return leg now shows sailing/arriving, not at-dock |
| r54 | Fixed swapped column labels for `lvApproaching` on SEA→BI tab |
| r55 | Fixed ferry icon rotation direction (XOR tab direction with `lvApproaching`) |
| r56 | Fixed upcoming section starting index (`slice(0,3)` not `slice(1,4)`); removed top gradient |
| r57 | Fixed at-dock track fill (0% not barPct%); fixed all-amber docked vessels (always use palette color) |
