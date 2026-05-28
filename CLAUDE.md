# Seattle Ferry Tracker — project notes

## Project goal

Real-time WSDOT Seattle ↔ Bainbridge Island ferry tracker. Single deliverable: `ferry.html` — a fully self-contained HTML file with all CSS, JS, and Leaflet 1.9.4 inlined. No build step. Deployed to GitHub Pages at `https://demetrearges206.github.io/seattle-ferry-tracker/ferry.html`.

## Current state (r50)

- `const BUILD = 'r50'` in ferry.html
- Inter font is inlined as base64 at deploy time via `.github/workflows/pages.yml` (not via CDN)
- Featured card (`#schedFeatured`) renders above the Vessels map section
- 4 card states: `at-dock`, `sailing`, `arriving`, `fallback` — driven by live vessel data
- Progress bar at **top** of card (6px, gradient left→right, width = `--bar-w`)
- For sailing/arriving: arrival time (large/white) on RIGHT, departed time (muted) on LEFT
- Upcoming rows: 2-column flex — vessel name + dep time left, "ETA" label + arr time right
- "Alerts" section replaces "Terminal Wait Times" — uses WSDOT `schedulebulletins` API
- `partial` status state (amber dot): schedule works but vessels API offline
- Direction toggle: `SEA-BI` (Seattle → Bainbridge) or `BI-SEA` (Bainbridge → Seattle)
- Vessel map markers: top-down ferry SVG icon (teardrop hull), rotates by heading, per-vessel palette color + glow

## Pending / next up

- **Map redesign** — user wants to discuss map changes (new vessel designs coming)
- Figma specs in `figma-specs/` — nodes 1076-120/146/173/229 (card states), 1074-967 (full mobile), 1074-1035 (upcoming row), 1074-1096 (refresh icon)

## File map

- `ferry.html` — entire app. All CSS, JS, and Leaflet 1.9.4 inlined. ~225KB.
- `.github/workflows/pages.yml` — deploys to GitHub Pages; inlines Inter font as base64 at build time.
- `README.md` — project overview and deploy instructions.
- `CLAUDE.md` — this file.

## Architecture

### Key global state

```js
let vesselList = [];        // [{VesselName, Lat, Lon, InService, AtDock, Eta, ...}]
let scheduleData = null;    // raw WSDOT schedule response
let waitData = [];          // terminal wait times
let direction = 'SEA-BI';  // or 'BI-SEA'
let lastUpdate = null;      // Date of last successful refresh
```

### Key functions

| Function | Purpose |
|----------|---------|
| `refresh()` | Main data fetch loop — calls all 3 WSDOT APIs via Promise.allSettled, updates global state, re-renders |
| `renderSchedule()` | Renders featured card → `#schedFeatured`, upcoming+full schedule → `#schedContent` |
| `renderVessels()` | Renders vessel icon strip (`#vesselStrip`) and updates map markers |
| `renderWaitTimes()` | Renders terminal wait table (`#waitContent`) |
| `getDepartures()` | Returns today's departures for current `direction` from `scheduleData` |
| `getReturnDeparture(afterTime)` | Temporarily swaps `direction` to get next opposite-direction departure |
| `getLiveVessel(name)` | Returns live vessel object from `vesselList` for a given vessel name |
| `routeVessels()` | Filters `vesselList` to vessels on the current route |
| `vesselStatus(lv)` | Returns `{text, cls}` badge for a live vessel (At Dock / Arriving / Sailing) |
| `countdownInfo(date)` | Returns `{text, cls}` for the countdown pill (Departed / Leaving / Xm / Xh Xm) |
| `setStatus(state)` | Updates the header status dot + text (loading / live / partial / stale) |
| `fmtTime(date)` | Formats a Date to "h:mm" |
| `parseWSDot(str)` | Parses WSDOT's `/Date(ms-offset)/` epoch strings |
| `minsTo(date)` | Minutes from now to a Date (negative = past) |

### Render targets (HTML structure)

```html
<div id="schedFeatured">   ← featured "Current Sailing" card only
<button id="vesselLabel">  ← Live Vessels toggle
<div id="vesselStrip">     ← vessel icon pills
<div class="map-section">  ← Leaflet map (#ferry-map)
<div id="schedContent">    ← upcoming rows + full schedule toggle
<div id="waitContent">     ← terminal wait times table
```

### Status states

| State | Dot | Text |
|-------|-----|------|
| `loading` | grey, off | "Refreshing…" |
| `live` | green, pulsing | "Updated Xm ago" or "Updated just now" |
| `partial` | amber, static | "Schedule · vessels offline" |
| `stale` | red, static | "Stale · Xm ago" or "Offline" |

### Badge labels (featured card)

| Condition | Text | Class |
|-----------|------|-------|
| `lv.AtDock` | "At Dock" | `badge-dock` |
| ETA ≤ 5 min | "Arriving" | `badge-underway` |
| Otherwise | "Sailing" | `badge-underway` |

### Countdown pill labels

| `minsTo` | Text | Class |
|----------|------|-------|
| < -5 | "Departed" | `gone` |
| -5 to 0 | "Leaving" | `now` |
| 0 to 10 | "Xm" | `now` (red) |
| 10 to 30 | "Xm" | `soon` (amber) |
| ≥ 30 | "Xh Xm" or "Xm" | "" (neutral) |

Pill updates every 10s via `cdTimer`. When `isUnderway`, shows a "TO ARRIVAL" sublabel.

## WSDOT API endpoints

Base URL: `https://www.wsdot.wa.gov/ferries/api/`

```
vessels/rest/vessellocations/{apikey}
schedule/rest/schedule/GetSchedule/{apikey}/{date}/{route}
terminals/rest/terminalwaittimes/{apikey}
```

Default demo API key: `7d7a5056-0f82-4547-a870-6db3db67b9d7`
Route codes: `SEA-BI` = Seattle-Bainbridge, `BI-SEA` = Bainbridge-Seattle

## CSS variables

```css
--bg: #0d1117        /* dark background */
--card: #161b22      /* card surface */
--border: #30363d    /* borders */
--text: #e6edf3      /* primary text */
--mid: #8b949e       /* secondary text */
--green: #3fb950     /* live/on-time */
--amber: #d29922     /* warning/partial */
--red: #f85149       /* alert/departed */
--teal: #58a6ff      /* accent/links */
```

## Refresh cadence

```
DOMContentLoaded
  → render cached schedule immediately (wsf_sched_v1) if present
  → refresh(!bootCache)         ← full refresh; skips schedule fetch if cache hit

setInterval(refresh(false), 60s)      ← vessels + wait times only
setInterval(refresh(true),  10min)    ← full refresh including schedule
setInterval(updateStaleLabel, 60s)    ← re-renders "Updated Xm ago" without fetching
cdTimer = setInterval(updateCountdowns, 10s)  ← countdown pills only
```

`refresh(fullRefresh)` uses `Promise.allSettled` so a single API failure doesn't block the rest. Each endpoint's result is checked individually; missing data falls back to last known good state or safe default (`[]` / `null`).

## localStorage keys

| Key | Contents | TTL |
|-----|----------|-----|
| `wsf_sched_v1` | `{ date: "YYYY-MM-DD", data: <raw schedule> }` | Invalidated when `date` ≠ today |
| `ferry_tip_v1` | `"1"` | Permanent — marks "Add to Home Screen" tip as shown |

## Map implementation

- **Instance vars:** `leafMap` (main Leaflet map, `#ferry-map`), `miniMap` (overview inset)
- **Init:** called once on `DOMContentLoaded` via `initMap()`. The container must be non-zero size before init — the main map is always visible at load so this is fine. The mini-map uses a 30ms timeout after its container becomes visible before calling `miniMap.invalidateSize()`.
- **Vessel markers:** circle markers placed at `[Lat, Lon]` from `vesselList`. Marker color: green (underway), amber (docked), grey (out of service).
- **Rule:** whenever the map container is hidden then re-shown, call `leafMap.invalidateSize({ reset: true })`. This is already wired to the vessel section toggle (`#vesselLabel` button). Don't skip it — Leaflet's tile grid goes blank on resize without it.
- **Tile layer:** OpenStreetMap tiles (`https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`). No API key required.

## How to start a new cloud session (code.claude.com)

1. Go to [code.claude.com](https://code.claude.com) and create a new session for the `demetrearges206/seattle-ferry-tracker` repo.
2. No special environment variables needed — Figma access works via GitHub Actions (see below).

## Figma integration (cloud sessions)

Direct Figma MCP does **not** work in cloud/web sessions — `api.figma.com` is blocked by the network egress policy. `FIGMA_ACCESS_TOKEN` being set has no effect.

**The working architecture:**
```
Figma API
  ↓  (GitHub Actions fetches — unrestricted network)
figma-specs/  in repo  (JSON + PNG images, committed by bot)
  ↓  (GitHub MCP reads)
Claude Code cloud session
```

**To sync a new Figma node:**
1. Paste the Figma node URL(s) here in chat
2. I commit them to `figma-specs/request.txt` and push to `main`
3. `figma-sync-auto.yml` triggers automatically, fetches data, commits specs back
4. I pull and read the specs, then implement

No manual GitHub Actions trigger needed — the whole chain is hands-free once the URL is pasted.

## Known issues / open threads

- **Figma MCP in cloud**: Does not work directly (network policy). Use the git-trigger workflow above.
- **CORS on `file://`**: Live API data won't load when opening ferry.html directly from disk in some browsers. Use `npx serve .` for local dev.
- **Mobile cache**: After deploy, iOS Safari aggressively caches. Hard-clear or append `?bust=N` to URL to force reload.
- **API key**: The default WSDOT demo key is public and shared. May occasionally rate-limit during high traffic. If needed, register for a key at wsdot.wa.gov.

## Workflow

1. Edit `ferry.html` here in Claude Code
2. Bump `const BUILD` (r35 → r36, etc.) to confirm new deploy loaded
3. Commit and push to `main`
4. GitHub Pages auto-deploys in ~30s
5. Remind user to hard-clear mobile cache if needed

## User preferences

- **Always push live immediately.** After every change: commit → push → open PR (never draft) → squash-merge right away. Do not wait for the user to trigger any of these steps. Close any superseded PRs from previous sessions.

## Anti-regression notes

- **Never use `lv.Eta` for future scheduled trips** — the live ETA is only valid for the vessel's current active trip. Upcoming rows always use `d.arrive` (scheduled time).
- **`vesselList` always defaults to `[]`** on API failure — never leave it `undefined`. All consumers guard with `Array.isArray(vesselList)`.
- **`getReturnDeparture()`** temporarily swaps the global `direction` variable and restores it. Don't refactor this without ensuring the swap/restore is atomic.
- **Leaflet map container** must be visible (non-zero dimensions) before `L.map()` initializes, or tiles/SVG pane won't have positioning rules. The map is initialized once on load; if the container is hidden/shown, call `map.invalidateSize()`.
