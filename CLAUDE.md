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
- Progress track at bottom of featured card — SEA always left, BI always right; ferry icon moves along it
- `lvApproaching` state: vessel on return leg toward our departure terminal shows sailing/arriving (not at-dock)

## File map

- `ferry.html` — entire app (~225 KB, all CSS/JS/Leaflet inlined)
- `.github/workflows/pages.yml` — GitHub Pages deploy; inlines Inter font as base64
- `.github/workflows/figma-sync-auto.yml` — auto-triggers on push when `figma-specs/request.txt` changes; fetches Figma API and commits JSON + PNG back to `main`
- `.github/workflows/figma-sync.yml` — manual workflow_dispatch version of the same
- `.github/scripts/figma_sync.py` — Python script that calls Figma REST API, writes `figma-specs/`
- `figma-specs/request.txt` — one Figma node URL per line; committing here triggers auto-sync
- `figma-specs/*.json` / `figma-specs/*.png` / `figma-specs/*-summary.md` — output from sync
- `.github/workflows/wsdot-snapshot.yml` — auto-triggers on push when `api-snapshots/request.txt` changes; fetches live WSDOT API data and commits JSON + markdown back to `main`
- `.github/scripts/wsdot_snapshot.py` — Python script that fetches vessellocations, vesselbasics, and schedule; writes `api-snapshots/`
- `api-snapshots/request.txt` — keywords (`vessels`, `schedule`, `all`); committing here triggers auto-snapshot
- `api-snapshots/*.json` / `api-snapshots/*-summary.md` — live API snapshots committed by bot
- `design/Boat Icon/ferry-deck.svg` — source SVG for vessel map marker icon
- `wsdot-attributes.md` — design reference: vessel list, API fields, card states, countdown pill states
- `CLAUDE.md` — this file

---

## Cloud session notes (code.claude.com)

**Branch issue:** Every code.claude.com session automatically assigns a feature branch (e.g. `claude/bold-volta-8GEoB`). The session environment instructs Claude to develop on that branch and open a PR. This conflicts with the project preference of always pushing directly to `main`.

**Workaround:** Push directly to `main` using the GitHub MCP tool (`mcp__github__create_or_update_file`) rather than local `git push`. This bypasses the branch entirely. Use this for all changes so they go live immediately.

**How to start a new cloud session:**
1. Go to [code.claude.com](https://code.claude.com) and create a new session for the `demetrearges206/seattle-ferry-tracker` repo
2. Set environment variables if needed:
   - `FIGMA_ACCESS_TOKEN` — only needed if you want to test direct Figma MCP (currently blocked by network policy; use the git-trigger workflow instead)
   - `WSDOT_API_KEY` — already set as a GitHub secret; not needed as an env var in the session
3. The session will clone `main` and have full git access

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

## WSDOT API snapshot workflow

The WSDOT API (`www.wsdot.wa.gov`) is also blocked from cloud sessions. Use the same git-trigger pattern:

### Step-by-step when you need live API data

1. Write keyword(s) to `api-snapshots/request.txt`: `vessels`, `schedule`, or `all`
2. Commit + push to `main` — `wsdot-snapshot.yml` fires automatically
3. Wait for the bot commit (watch via `git pull` or GitHub MCP `list_commits`)
4. Read `api-snapshots/vessel-summary.md` (vessel list + status) or `api-snapshots/schedule-summary-YYYY-MM-DD.md`

**Available keywords:**
- `vessels` — fetches `vessellocations` (live positions/status) + `vesselbasics` (static fleet info)
- `schedule` — fetches today's SEA-BI and BI-SEA schedules
- `all` — fetches everything

**Output files committed by the bot:**
- `api-snapshots/vessel-locations.json` — raw vessellocations response
- `api-snapshots/vessel-basics.json` — raw vesselbasics response
- `api-snapshots/vessel-summary.md` — readable table: vessel name, InService, AtDock, From/To, ETA, speed
- `api-snapshots/schedule-SEA-BI-YYYY-MM-DD.json` — raw schedule
- `api-snapshots/schedule-summary-YYYY-MM-DD.md` — readable sailings table

**Do not attempt to call `www.wsdot.wa.gov` directly from a cloud session — it will always fail.**

**Troubleshooting if the bot doesn't commit back:**
- Check the Actions tab at `github.com/demetrearges206/seattle-ferry-tracker/actions`
- Ensure Actions are enabled: Settings → Actions → General → Allow all actions
- Ensure the workflow has write permission: Settings → Actions → General → Workflow permissions → Read and write

---

## WSDOT API endpoints

**IMPORTANT: The API key is a QUERY PARAMETER, not a path segment.**

```js
apiUrl(base, path) → `${base}/${path}?apiaccesscode=${API_KEY}`
```

| Base | Path | Purpose |
|------|------|---------|
| `https://www.wsdot.wa.gov/ferries/api/vessels/rest` | `vessellocations` | Live vessel positions, headings, ETAs, docked status |
| `https://www.wsdot.wa.gov/ferries/api/vessels/rest` | `vesselbasics` | Static fleet info (class, capacity) |
| `https://www.wsdot.wa.gov/ferries/api/schedule/rest` | `scheduletoday/{dep_id}/{arr_id}/false` | Today's sailings between two terminals |
| `https://www.wsdot.wa.gov/ferries/api/schedule/rest` | `schedulebulletins` | Service alerts |
| `https://www.wsdot.wa.gov/ferries/api/terminals/rest` | `terminalwaittimes` | Terminal wait/reservation times |

**API key:** Stored in `ferry.html` as `const API_KEY` and in the GitHub secret `WSDOT_API_KEY`. Demo fallback: `7d7a5056-0f82-4547-a870-6db3db67b9d7`.

**Terminal IDs:**
```js
const TERMINALS = {
  SEA: { id: 7,  name: 'Seattle',          abbrev: 'SEA' },
  BI:  { id: 3,  name: 'Bainbridge Island', abbrev: 'BI'  },
};
```

**Date format:** All WSDOT dates are `/Date(milliseconds-offset)/` strings — use `parseWSDot(str)`.

**Key vessel API fields:**

| Field | Type | Meaning |
|-------|------|---------|
| `VesselName` | string | e.g. `"Tacoma"` |
| `Lat`, `Lon` | float | GPS position |
| `Heading` | int | Degrees 0–359 |
| `AtDock` | bool | True when tied up at terminal |
| `LeftDock` | `/Date(ms)/` | When vessel last departed |
| `Eta` | `/Date(ms)/` | Live ETA at next terminal (current trip only) |
| `DepartingTerminalID` | int | Terminal sailing FROM |
| `ArrivingTerminalID` | int | Terminal sailing TO |
| `InService` | bool | False = maintenance |
| `Speed` | float | Knots |

---

## WSF vessel fleet

21 vessels total as of 2026-05-29. Full list with classes and attributes in `wsdot-attributes.md`.

**Seattle–Bainbridge primary vessels:** Wenatchee, Tacoma (Jumbo Mark II class)

**Derived vessel statuses:**

| `InService` | `AtDock` | App state | Badge |
|-------------|----------|-----------|-------|
| `false` | any | Filtered out | — |
| `true` | `true` | `at-dock` | **At Dock** |
| `true` | `false`, ETA > 5 min | `sailing` | **Sailing** |
| `true` | `false`, ETA ≤ 5 min | `arriving` | **Arriving** |

**Countdown pill text (`countdownInfo()`):**

| `minsTo(cdTarget)` | Text | Color |
|--------------------|------|-------|
| ≥ 60 | `"Xh Xm"` | neutral |
| 10–59 | `"Xm"` | neutral |
| 0–9 | `"Xm"` | red |
| −5 to 0 | `"Leaving"` | red |
| < −5 | `"Departed"` | muted |

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
| `refresh(fullRefresh)` | Main fetch loop — `Promise.allSettled` over all APIs, updates state, re-renders |
| `renderSchedule()` | Featured card → `#schedFeatured`; upcoming + full schedule → `#schedContent` |
| `renderVessels()` | Updates Leaflet map markers + vessel strip |
| `renderWaitTimes()` | Terminal wait table (`#waitContent`) |
| `getDepartures()` | Today's departures for current `direction` from `scheduleData` |
| `getReturnDeparture(afterTime)` | Temporarily swaps `direction`; gets next opposite-direction departure |
| `getLiveVessel(name)` | Live vessel object from `vesselList` |
| `routeVessels()` | `vesselList` filtered to SEA↔BI route vessels |
| `countdownInfo(date)` | `{text, cls}` for countdown pill |
| `setStatus(state)` | Header dot + text (`loading`/`live`/`partial`/`stale`) |
| `fmtTime(date)` | Date → `"h:mm AM/PM"` |
| `parseWSDot(str)` | `/Date(ms-offset)/` → JS Date |
| `minsTo(date)` | Minutes from now to a Date (negative = past) |
| `vesselMarkerIcon(heading, atDock, name)` | `L.divIcon` with ferry SVG for map |
| `getVesselColor(name)` | Per-vessel stable color from `VESSEL_PALETTE` |
| `updateProgress()` | Repositions `#ncPin` and `#ncTrackFill` every 10s |

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

## Featured card — detailed

### `lvApproaching` logic

```js
const dirDep = direction === 'SEA-BI' ? TERMINALS.SEA.id : TERMINALS.BI.id;
const dirArr = direction === 'SEA-BI' ? TERMINALS.BI.id  : TERMINALS.SEA.id;

const lvOnRoute     = lv && !lv.AtDock &&
  lv.DepartingTerminalID === dirDep && lv.ArrivingTerminalID === dirArr;

const lvApproaching = lv && !lv.AtDock && !lvOnRoute &&
  lv.DepartingTerminalID === dirArr && lv.ArrivingTerminalID === dirDep;
```

When `lvApproaching`, the vessel is on its return leg heading toward our departure terminal. Show it as sailing/arriving rather than at-dock.

### Card states

| State | Condition | Pin position |
|-------|-----------|-------------|
| `fallback` | No live vessel | Hidden |
| `at-dock` | `lv.AtDock` or no route match | 3% (SEA side) or 97% (BI side) |
| `sailing` | Underway, ETA > 5 min | Along track |
| `arriving` | Underway, ETA ≤ 5 min | Near arrival end |

### Progress track

- SEA always left (0%), BI always right (100%)
- `nc-track-fill` width = 0% when at-dock; = pin% when sailing
- Ferry icon rotation: `((direction === 'SEA-BI') !== lvApproaching) ? 90 : -90`
- `updateProgress()` fires every 10s via `cdTimer`; uses `cdTarget` (no dependency on `LeftDock`)

### Column labels

**SEA→BI tab:**

| State | SEA col (left) | BI col (right) |
|-------|----------------|----------------|
| `at-dock` | DEPARTS SEA + `next.depart` (primary) | ARRIVES BI + `next.arrive` |
| `lvApproaching` | ARRIVES SEA + `approachEta` (primary) | DEPARTED BI + `actualDepart` |
| `sailing`/`arriving` | DEPARTED SEA + `actualDepart` | ARRIVES BI + `arriveTime` (primary) |

**BI→SEA tab:**

| State | SEA col (left) | BI col (right) |
|-------|----------------|----------------|
| `at-dock` | ARRIVES SEA + `next.arrive` | DEPARTS BI + `next.depart` (primary) |
| `lvApproaching` | DEPARTED SEA + `actualDepart` | ARRIVES BI + `approachEta` (primary) |
| `sailing`/`arriving` | ARRIVES SEA + `arriveTime` (primary) | DEPARTED BI + `actualDepart` |

---

## CSS variables

```css
--bg:     #0d1117   /* page background */
--card:   #161b22   /* card surface */
--border: #30363d   /* borders */
--text:   #e6edf3   /* primary text */
--mid:    #8b949e   /* secondary/muted text */
--green:  #3fb950   /* live / on-time */
--amber:  #d29922   /* warning / partial */
--red:    #f85149   /* alert / departed */
--teal:   #58a6ff   /* accent / links */
```

**Vessel color palette** (`VESSEL_PALETTE`, indexed by stable hash of vessel name):
`#00c9a7`, `#ffc947`, `#f472b6`, `#60a5fa`, `#fb923c`, `#a3e635`, `#c084fc`, `#f87171`

Always use palette color for vessel markers — docked state shown by dimmer glow only, not a different color.

---

## Refresh cadence

```
DOMContentLoaded
  → render cached schedule immediately (wsf_sched_v1) if present
  → refresh(!bootCache)

setInterval(refresh(false), 60s)      ← vessels + wait times only
setInterval(refresh(true),  10min)    ← full refresh including schedule
setInterval(updateStaleLabel, 60s)    ← "Updated Xm ago" label
cdTimer = setInterval(updateProgress + updateCountdowns, 10s)
```

---

## localStorage keys

| Key | Contents | TTL |
|-----|----------|-----|
| `wsf_sched_v1` | `{ date: "YYYY-MM-DD", data: <raw schedule> }` | Invalidated when date ≠ today |
| `ferry_tip_v1` | `"1"` | Permanent — home screen tip flag |

---

## Map implementation

- Leaflet 1.9.4 fully inlined in `ferry.html`
- Vessel markers: `L.divIcon` with teardrop ferry SVG, rotated by `Heading`, per-vessel color + glow
- Init: `initMap()` called once on `DOMContentLoaded`; container must be non-zero size
- After hide/show: call `leafMap.invalidateSize({ reset: true })` — wired to vessel section toggle
- Tile layer: OpenStreetMap (no API key required)

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
3. Push directly to `main` — use `mcp__github__create_or_update_file` if in a cloud session with a forced branch, otherwise `git push origin main`
4. GitHub Pages auto-deploys in ~30s
5. User may need hard cache clear on iOS Safari (`?bust=N` appended to URL)

**Always push live immediately — commit → push to `main`. No PRs, no branches, no waiting.**

---

## Anti-regression notes

- **Never use `lv.Eta` for future scheduled trips** — live ETA only valid for the current active trip. Upcoming rows always use `d.arrive` (scheduled).
- **`vesselList` always defaults to `[]`** on API failure — never undefined.
- **`getReturnDeparture()`** temporarily swaps global `direction` — must remain atomic.
- **Leaflet container** must be visible before `L.map()` init.
- **`lvApproaching`**: vessel on return leg → show sailing/arriving, not at-dock. Track position, ferry rotation, and column labels all have separate `lvApproaching` branches.
- **Track fill vs pin**: at-dock → fill = 0%, pin = 3%/97%. Sailing → fill = pin = barPct.
- **`cdTarget`** drives both the pill and `updateProgress()`. It's set in `renderSchedule()` and read by the interval callbacks as a closure variable.
- **Upcoming slice**: `upcoming.slice(0, 3)` — do NOT use `slice(1, 4)`; the featured departure is also the first upcoming row.

---

## Known issues

- **Figma MCP in cloud**: Network blocked. Use the git-trigger workflow — it's fully automatic.
- **Branch forced in cloud sessions**: code.claude.com assigns a feature branch. Workaround: push to `main` directly via `mcp__github__create_or_update_file`.
- **CORS on `file://`**: Live API data won't load from disk. Use `npx serve .` locally.
- **Mobile cache**: iOS Safari aggressively caches. Hard-clear or `?bust=N` after deploy.
