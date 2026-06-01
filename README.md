# Seattle Ferry Tracker

Real-time WSDOT Seattle ↔ Bainbridge Island ferry tracker. Single self-contained HTML file — no build step, no dependencies to install.

**Live app:** https://demetrearges206.github.io/seattle-ferry-tracker/ferry.html

## What it does

- **Current Sailing card** — shows the active or next departure with live vessel status (At Dock / Sailing / Arriving), ETA countdown pill, animated progress track with ferry icon that moves in real time, and return departure time
- **Direction toggle** — switch between SEA → BBI and BBI → SEA
- **Upcoming sailings** — next 3 departures (after the active sailing) with vessel name, scheduled arrival, and countdown pill
- **Full schedule** — expand to see the complete day's timetable
- **Route map** — inline SVG map of the SEA–BBI corridor with animated vessel markers that rotate by heading; terminal labels expand with pulse dots when a vessel is docked; tap any vessel for a detail popup with speed, ETA, and a Leaflet miniMap
- **Alerts** — active WSDOT service bulletins and terminal wait times

## Vessel card states

| State | Condition |
|-------|-----------|
| **At Dock** | Vessel tied up at departure terminal |
| **Sailing** | Underway, ETA > 5 min |
| **Arriving** | Underway, ETA ≤ 5 min |
| **Delayed** | Underway, running > 5 min late |
| **AT BBI / AT SEA** | Vessel docked at the wrong terminal — must cross first |
| *Approaching* | Vessel on return leg heading back to pick up passengers (shown as Sailing/Arriving on the tab it's serving) |

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
| r51 | Card redesign from Figma: progress track at bottom, SEA/BBI terminal labels, ferry icon on track |
| r52 | Ferry icon moves along track based on live ETA; `computeBarPct()` driven by `cdTarget` |
| r53 | Fixed `lvApproaching` — vessel on return leg now shows sailing/arriving, not at-dock |
| r54 | Fixed swapped column labels for `lvApproaching` on SEA→BBI tab |
| r55 | Fixed ferry icon rotation direction (XOR tab direction with `lvApproaching`) |
| r56 | Fixed upcoming section starting index; removed top gradient |
| r57 | Fixed at-dock track fill (0% not barPct%); fixed palette color always used for docked vessels |
| r58–r64 | Navy color theme; card polish; popup improvements |
| r65–r68 | Replaced Leaflet vessel map with inline SVG route map; terminal dock dots with pulse animation; Leaflet moved to vessel tap popup (miniMap) |
| r69 | Terminal abbrev BI → BBI; ARRIVES label fix; vessel popup tap fix; ferry icon enlarged to 34px |
| r70 | Added `lvAtOther` state: vessel docked at wrong terminal now shows "AT SEA" / "AT BBI" with correct dot positions |
| r71 | Map centering fix; upcoming table redesigned with ETA column + countdown pill; active sailing removed from upcoming list |
| r72 | Terminal label dot pulse clearance padding; ETA stacked layout in upcoming rows |
| r73 | Fixed null-ETA crash: `minsTo(null)` guard on `approachEta` prevents false "Arriving" state when WSDOT omits ETA briefly after departure |
