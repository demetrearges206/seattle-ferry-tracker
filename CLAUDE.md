# Seattle Ferry Tracker — project notes

## Project goal

Real-time WSDOT Seattle ↔ Bainbridge Island ferry tracker. Single deliverable: `ferry.html` — a fully self-contained HTML file with all CSS, JS, and Leaflet 1.9.4 inlined. No build step. Deployed to GitHub Pages at `https://demetrearges206.github.io/seattle-ferry-tracker/ferry.html`.

## Current state (r57)

- `const BUILD = 'r57'` in ferry.html — bump on every change
- Inter font inlined as base64 at deploy time via `.github/workflows/pages.yml` (not CDN)
- Direction toggle: `SEA-BI` (Seattle → Bainbridge) or `BI-SEA` (Bainbridge → Seattle)
- Featured card (`#schedFeatured`) renders above the Vessels/map section
- Upcoming section (`#schedContent`) shows `upcoming.slice(0, 3)` — starts with the current active sailing
- Vessel map markers: teardrop SVG icon, rotates by heading, per-vessel palette color with glow (dimmer when docked)

## File map

- `ferry.html` — entire app (~225 KB, all CSS/JS/Leaflet inlined)
- `.github/workflows/pages.yml` — GitHub Pages deploy; inlines Inter font as base64
- `.github/workflows/figma-sync-auto.yml` — auto-triggers on push when `figma-specs/request.txt` changes; fetches Figma API and commits JSON + PNG back to `main`
- `.github/workflows/figma-sync.yml` — manual workflow_dispatch version of the same
- `.github/scripts/figma_sync.py` — Python script that calls Figma REST API, writes `figma-specs/`
- `figma-specs/request.txt` — one Figma node URL per line; committing here triggers auto-sync
- `figma-specs/*.json` / `figma-specs/*.png` / `figma-specs/*-summary.md` — output from sync
- `design/Boat Icon/ferry-deck.svg` — source SVG for vessel map marker icon
- `CLAUDE.md` — this file

---

## Figma workflow (IMPORTANT — read before implementing any Figma design)

Direct Figma API / Figma MCP **does not work** in Claude Code cloud/web sessions — `api.figma.com` is blocked by network egress policy. `FIGMA_ACCESS_TOKEN` env var is set but irrelevant.

### How it works

```
User pastes Figma node URL in chat
  ↓
Claude commits URL to figma-specs/request.txt and pushes to main
  ↓
.github/workflows/figma-sync-auto.yml triggers automatically (watches request.txt)
  ↓
GitHub Actions (unrestricted network) calls Figma API, fetches node JSON + renders PNG
  ↓
Bot commits figma-specs/<node-id>.png, figma-specs/<file-id>-nodes.json,
  figma-specs/<file-id>-summary.md back to main
  ↓
Claude pulls / reads specs via local git or GitHub MCP, then implements
```

### Step-by-step when user provides a Figma URL

1. Read `figma-specs/request.txt` first (to know current contents)
2. Write the new node URL to `figma-specs/request.txt` (one URL per line)
3. Commit + push to `main` — the auto-sync workflow fires immediately
4. Wait for the bot commit (watch via `git pull` or GitHub MCP `list_commits`)
5. Read `figma-specs/<node-id>.png` (visual reference) and `figma-specs/*-summary.md` (layout tree)
6. Implement, bump BUILD, commit + push to `main`

**Do not attempt to call `api.figma.com` directly — it will always fail.**

---

## WSDOT API endpoints

Base URL: `https://www.wsdot.wa.gov/ferries/api/`

| Endpoint | Purpose |
|----------|---------|
| `vessels/rest/vessellocations/{key}` | Live vessel positions, headings, ETAs, docked status |
| `schedule/rest/schedule/GetSchedule/{key}/{date}/{route}` | Full day schedule for a route |
| `terminals/rest/terminalwaittimes/{key}` | Terminal wait/reservation times |
| `schedule/rest/schedulebulletins/{key}` | Service alerts / bulletins |

**Demo API key** (public, shared): `7d7a5056-0f82-4547-a870-6db3db67b9d7`

**Route codes for schedule endpoint:**
- `SEA-BI` = `Seattle-Bainbridge` (use the full hyphenated name in the URL)
- `BI-SEA` = `Bainbridge-Seattle`

**Date format:** `YYYY-MM-DD`

**Vessel API key fields used in the app:**

| Field | Type | Meaning |
|-------|------|---------|
| `VesselName` | string | e.g. `"Tacoma"`, `"Wenatchee"` |
| `Lat`, `Lon` | float | Current GPS position |
| `Heading` | int | Degrees 0–359 |
| `AtDock` | bool | True when vessel is tied up at a terminal |
| `LeftDock` | `/Date(ms)/` | When vessel last departed a terminal |
| `Eta` | `/Date(ms)/` | Live ETA at next terminal (only valid for current active trip) |
| `DepartingTerminalID` | int | Terminal vessel is sailing FROM |
| `ArrivingTerminalID` | int | Terminal vessel is sailing TO |
| `InService` | bool | False = out of service / maintenance |
| `Speed` | float | Knots |

**Terminal IDs (constants in code):**
```js
const TERMINALS = {
  SEA: { id: 7,  name: 'Seattle',          abbrev: 'SEA' },
  BI:  { id: 3,  name: 'Bainbridge Island', abbrev: 'BI'  },
};
```

**Date parsing:** All WSDOT dates are `/Date(milliseconds-offset)/` strings — use `parseWSDot(str)`.

---

## Architecture

### Key global state

```js
let vesselList = [];        // [{VesselName, Lat, Lon, InService, AtDock, Eta, ...}]
let scheduleData = null;    // raw WSDOT schedule response
let waitData = [];          // terminal wait times
let direction = 'SEA-BI';  // or 'BI-SEA'
let lastUpdate = null;      // Date of last successful refresh
let cdTimer = null;         // interval handle for 10s countdown ticks
```

### Key functions

| Function | Purpose |
|----------|---------|
| `refresh(fullRefresh)` | Main fetch loop — `Promise.allSettled` over all 3 APIs, updates state, re-renders |
| `renderSchedule()` | Featured card → `#schedFeatured`; upcoming + full schedule → `#schedContent` |
| `renderVesselStrip()` | Vessel icon strip (`#vesselStrip`) |
| `renderVessels()` | Updates Leaflet map markers |
| `renderWaitTimes()` | Terminal wait table (`#waitContent`) |
| `getDepartures()` | Today's departures for current `direction` from `scheduleData` |
| `getReturnDeparture(afterTime)` | Temporarily swaps `direction`; gets next opposite-direction departure |
| `getLiveVessel(name)` | Live vessel object from `vesselList` for a given vessel name |
| `routeVessels()` | `vesselList` filtered to vessels on the current SEA↔BI route |
| `countdownInfo(date)` | `{text, cls}` for countdown pill |
| `setStatus(state)` | Header dot + text (`loading`/`live`/`partial`/`stale`) |
| `fmtTime(date)` | Date → `"h:mm AM/PM"` |
| `splitTime(date)` | Date → `{t: "h:mm", ap: "AM"}` for display in card columns |
| `parseWSDot(str)` | `/Date(ms-offset)/` → JS Date |
| `minsTo(date)` | Minutes from now to a Date (negative = past) |
| `vesselMarkerIcon(heading, atDock, name)` | Returns `L.divIcon` with ferry SVG for map |
| `getVesselColor(name)` | Per-vessel stable color from `VESSEL_PALETTE` |

### Render targets (HTML structure)

```html
<div id="schedFeatured">   ← featured card (1 card)
<button id="vesselLabel">  ← Live Vessels toggle
<div id="vesselStrip">     ← vessel icon pills
<div class="map-section">  ← Leaflet map (#ferry-map)
<div id="schedContent">    ← upcoming rows + full schedule toggle
<div id="waitContent">     ← terminal wait times / alerts
```

---

## Featured card (renderSchedule) — detailed

### Live vessel detection

```js
const dirDep = direction === 'SEA-BI' ? TERMINALS.SEA.id : TERMINALS.BI.id;
const dirArr = direction === 'SEA-BI' ? TERMINALS.BI.id  : TERMINALS.SEA.id;

// Vessel traveling in the correct direction for this tab
const lvOnRoute = lv && !lv.AtDock &&
  lv.DepartingTerminalID === dirDep && lv.ArrivingTerminalID === dirArr;

// Vessel traveling the RETURN leg toward our departure terminal
const lvApproaching = lv && !lv.AtDock && !lvOnRoute &&
  lv.DepartingTerminalID === dirArr && lv.ArrivingTerminalID === dirDep;
```

`lvApproaching` is critical: when the vessel is on its return trip (e.g., sailing BI→SEA while we're on the SEA→BI tab), the card shows the approach in progress rather than a static "At Dock" state.

### Card states

| State | Condition | Pin position |
|-------|-----------|-------------|
| `fallback` | No live vessel data | Hidden |
| `at-dock` | `lv.AtDock` OR (`!lvOnRoute && !lvApproaching`) | Parked at departure terminal (3% SEA or 97% BI) |
| `sailing` | `lvApproaching` with >5 min to arrival, OR `lvOnRoute` with >5 min ETA | Moving along track |
| `arriving` | `lvApproaching` with ≤5 min to arrival, OR `lvOnRoute` with ≤5 min ETA | Near arrival terminal |

### Track / progress bar

- **SEA always left (0%), BI always right (100%)** — fixed regardless of direction tab
- `nc-track-fill` width = 0% when `at-dock`; otherwise = pin position %
- `nc-vessel-pin` left = `barPct` (3–97%, clamped)
- Ferry icon rotated: `((direction === 'SEA-BI') !== lvApproaching) ? 90 : -90` — always points toward the terminal the vessel is heading to
- `updateProgress()` fires every 10s via `cdTimer`; uses `cdTarget` (live ETA-based) and `scheduledTripMs` to reposition pin without needing `LeftDock`

### Column layout (SEA left, BI right)

**SEA→BI tab:**

| State | SEA col (left) | BI col (right) |
|-------|----------------|----------------|
| `at-dock` | DEPARTS SEA + `next.depart` (primary) | ARRIVES BI + `next.arrive` |
| `lvApproaching` (vessel BI→SEA) | ARRIVES SEA + `approachEta` (primary) | DEPARTED BI + `actualDepart` |
| `sailing` / `arriving` | DEPARTED SEA + `actualDepart` | ARRIVES/ARRIVED BI + `arriveTime` (primary) |

**BI→SEA tab:**

| State | SEA col (left) | BI col (right) |
|-------|----------------|----------------|
| `at-dock` | ARRIVES SEA + `next.arrive` | DEPARTS BI + `next.depart` (primary) |
| `lvApproaching` (vessel SEA→BI) | DEPARTED SEA + `actualDepart` | ARRIVES/ARRIVED BI + `approachEta` (primary) |
| `sailing` / `arriving` | ARRIVES/ARRIVED SEA + `arriveTime` (primary) | DEPARTED BI + `actualDepart` |

**Primary column** = large text (42px). Secondary = muted smaller text.

### Countdown pill

- `cdTarget` = `next.depart` when at-dock; `arriveTime` (or `approachEta`) when sailing/arriving
- `countdownInfo(cdTarget)` → pill text: `"Xm"`, `"Leaving"`, `"Departed"`, etc.
- `#ncPinTime` below the ferry icon on the track shows the same text (hidden when at-dock)

### Footer line

- Normal: `"Next: Departs [destination] · [time]"` via `getReturnDeparture()`
- `lvApproaching`: `"Next: Departs [departure terminal] · [next.depart]"`

---

## CSS variables

```css
--bg:     #0d1117   /* page background */
--card:   #161b22   /* generic card surface */
--border: #30363d   /* borders */
--text:   #e6edf3   /* primary text */
--mid:    #8b949e   /* secondary/muted text */
--green:  #3fb950   /* live / on-time */
--amber:  #d29922   /* warning / partial */
--red:    #f85149   /* alert / departed */
--teal:   #58a6ff   /* accent / links */
```

**Featured card uses its own dark palette** (`#0e2040` background, `rgba(255,255,255,0.07)` border) defined directly in `.next-card`.

**Vessel color palette** (`VESSEL_PALETTE` array, indexed by stable hash of vessel name):
`#00c9a7`, `#ffc947`, `#f472b6`, `#60a5fa`, `#fb923c`, `#a3e635`, `#c084fc`, `#f87171`

Vessels always use their palette color (including when docked). Docked state indicated by dimmer glow only.

---

## Refresh cadence

```
DOMContentLoaded
  → render cached schedule immediately (wsf_sched_v1) if present
  → refresh(!bootCache)  ← full refresh; skips schedule fetch if cache hit

setInterval(refresh(false), 60s)      ← vessels + wait times only
setInterval(refresh(true),  10min)    ← full refresh including schedule
setInterval(updateStaleLabel, 60s)    ← re-renders "Updated Xm ago" label
cdTimer = setInterval(updateProgress+updateCountdowns, 10s)  ← pin + pill ticks
```

`refresh()` uses `Promise.allSettled` — single API failure doesn't block others. Missing data falls back to last known good or safe defaults (`[]` / `null`).

---

## localStorage keys

| Key | Contents | TTL |
|-----|----------|-----|
| `wsf_sched_v1` | `{ date: "YYYY-MM-DD", data: <raw schedule> }` | Invalidated when date ≠ today |
| `ferry_tip_v1` | `"1"` | Permanent — home screen tip shown flag |

---

## Map implementation

- **Leaflet 1.9.4** fully inlined in `ferry.html`
- **Instance vars:** `leafMap` (`#ferry-map`), optional `miniMap` (overview inset)
- **Vessel markers:** `L.divIcon` with teardrop ferry SVG, rotated by `Heading`, per-vessel color + glow
- **Init:** `initMap()` called once on `DOMContentLoaded`. Container must be non-zero size.
- **After hide/show:** call `leafMap.invalidateSize({ reset: true })` — already wired to the vessel section toggle. Never skip — tile grid goes blank without it.
- **Tile layer:** OpenStreetMap `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png` (no key needed)

---

## Status states

| State | Dot | Text |
|-------|-----|------|
| `loading` | grey, off | "Refreshing…" |
| `live` | green, pulsing | "Updated Xm ago" / "Updated just now" |
| `partial` | amber, static | "Schedule · vessels offline" |
| `stale` | red, static | "Stale · Xm ago" / "Offline" |

---

## Workflow

1. Edit `ferry.html`
2. Bump `const BUILD` (r57 → r58, etc.)
3. Commit + push to `main`
4. GitHub Pages auto-deploys in ~30s
5. User may need hard cache clear on iOS Safari (`?bust=N` appended to URL)

**Always push live immediately** — commit → push to `main`. No PRs, no waiting.

---

## Anti-regression notes

- **Never use `lv.Eta` for future scheduled trips** — live ETA is only valid for the vessel's current active trip. Upcoming rows always use `d.arrive` (scheduled).
- **`vesselList` always defaults to `[]`** on API failure — never undefined. All consumers guard with `Array.isArray`.
- **`getReturnDeparture()`** temporarily swaps the global `direction` and restores it. Must be atomic — don't refactor without preserving swap/restore.
- **Leaflet container** must be visible before `L.map()` init. Already handled — don't change init order.
- **`lvApproaching` logic**: when vessel is on the return leg heading toward our departure terminal, show it as sailing/arriving (not at-dock). The track position, ferry icon rotation, and column labels all use separate logic for this case. See "Featured card" section above.
- **Track fill vs pin position**: at-dock state → fill = 0%, pin = 3%/97%. Sailing → fill = pin = barPct. Never set fill to barPct when at-dock.
- **`cdTarget`** is `next.depart` when at-dock, `arriveTime` when sailing. `updateProgress()` always reads `cdTarget` — it's a closure variable from `renderSchedule()`.

---

## Known issues

- **Figma MCP in cloud**: Does not work — network blocked. Use the git-trigger workflow above (it's fully automatic).
- **CORS on `file://`**: Live API data won't load opening ferry.html directly from disk. Use `npx serve .` locally.
- **Mobile cache**: iOS Safari aggressively caches. Hard-clear or append `?bust=N` after deploy.
- **WSDOT API key**: Demo key is public/shared; may rate-limit under high traffic. Register at wsdot.wa.gov if needed.
