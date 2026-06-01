# Seattle Ferry Tracker — project notes

## Project goal

Real-time WSDOT Seattle ↔ Bainbridge Island ferry tracker. Single deliverable: `ferry.html` — a fully self-contained HTML file with all CSS, JS, and Leaflet 1.9.4 inlined. No build step. Deployed to GitHub Pages at `https://demetrearges206.github.io/seattle-ferry-tracker/ferry.html`.

## Current state (r73)

- `const BUILD = 'r73'` in ferry.html — bump on every change
- Inter font inlined as base64 at deploy time via `.github/workflows/pages.yml` (not CDN)
- Direction toggle: `SEA-BBI` (Seattle → Bainbridge) or `BBI-SEA` (Bainbridge → Seattle)
- Featured card (`#schedFeatured`) renders above the Vessels/map section
- Upcoming section (`#schedContent`) shows `upcoming.slice(1, 4)` — skips the active sailing (already in featured card), shows next 3
- Vessel map markers: teardrop SVG icon in inline SVG map, per-vessel palette color; Leaflet miniMap in vessel popup
- Progress track at bottom of featured card — SEA always left, BBI always right; ferry icon moves along it
- `lvApproaching` state: vessel on return leg toward departure terminal shows sailing/arriving (not at-dock)
- `lvAtOther` state: vessel docked at the wrong terminal (arrival side) — card shows "AT BBI" or "AT SEA" with next scheduled departure

## File map

- `ferry.html` — entire app (~225 KB, all CSS/JS/Leaflet inlined)
- `.github/workflows/pages.yml` — GitHub Pages deploy; inlines Inter font as base64 (the only workflow; not a workaround — this publishes the site)
- `scripts/wsdot.py` — local dev tool: fetches live WSDOT vessel/schedule data and writes readable snapshots to `api-snapshots/`. Run `python3 scripts/wsdot.py [vessels|schedule|all]`
- `api-snapshots/` — local scratch output from `scripts/wsdot.py` (gitignored, not committed)
- `design/Boat Icon/ferry-deck.svg` — source SVG for vessel map marker icon
- `wsdot-attributes.md` — design reference: vessel list, API fields, card states, countdown pill states
- `CLAUDE.md` — this file

---

## Working environment (GitHub Codespaces terminal)

Development happens in a **Codespaces terminal** with full network and git access. This replaced the earlier code.claude.com web sessions, which had two limitations that no longer apply:

- **No forced feature branch.** Work directly on `main` and push with plain `git push origin main`. (The old `git push origin HEAD:main` workaround is no longer needed.)
- **No network egress block.** `www.wsdot.wa.gov` and `api.figma.com` are both reachable directly. The old git-trigger snapshot/sync workflows existed only to dodge that block and have been removed.

### Getting live WSDOT data

Just call the API directly — `curl` or the helper script:

```bash
python3 scripts/wsdot.py all        # vessels + schedule → api-snapshots/ (gitignored)
python3 scripts/wsdot.py vessels    # live positions + fleet basics only
```

The script uses `$WSDOT_API_KEY` if set, otherwise the working key baked into `ferry.html`.

### Figma

Figma is connected via the **framelink** MCP server (`figma-developer-mcp`), registered at **project scope** in `.mcp.json`. `api.figma.com` is reachable from Codespaces, so it works directly without the old git-trigger workflow.

**Setup (already done):**

```bash
claude mcp add figma --scope project -- npx -y figma-developer-mcp '--figma-api-key=${FIGMA_API_KEY}' --stdio
```

This writes `.mcp.json` with a `${FIGMA_API_KEY}` reference (no secret in the file — safe to commit).

- **`mcpServers` in `.claude/settings.json` is NOT read** by this Claude Code version — use project `.mcp.json` (via `claude mcp add --scope project`). That is the only working location.
- **Token:** the Figma personal access token must be in the env as `FIGMA_API_KEY`. Store it as a **Codespaces secret** (repo → Settings → Secrets and variables → **Codespaces**, not Actions — Actions secrets are invisible to the Codespace), then rebuild the container. The existing `FIGMA_API_KEY` Actions secret does nothing for the MCP.
- **First launch:** a project `.mcp.json` server requires one-time manual approval — run `claude`, approve **figma** when prompted, then `/mcp` should show ✓ Connected.
- **Tools:** `get_figma_data` (layout/styles/text for a file or node) and `download_figma_images` (export assets).

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

**API key:** Stored in `ferry.html` as `const API_KEY` (currently `ff39cd9c-…`, verified working) and in the GitHub secret `WSDOT_API_KEY`. `scripts/wsdot.py` reads `$WSDOT_API_KEY` or falls back to that same key. (The old public demo key `7d7a5056-…` now returns HTTP 400 — don't use it.)

**Terminal IDs:**
```js
const TERMINALS = {
  SEA: { id: 7, name: 'Seattle',           abbrev: 'SEA', lat: 47.60328, lng: -122.33787 },
  BI:  { id: 3, name: 'Bainbridge Island', abbrev: 'BBI', lat: 47.62375, lng: -122.51044 },
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

### `lvApproaching` / `lvAtOther` logic

```js
const dirDep = direction === 'SEA-BI' ? TERMINALS.SEA.id : TERMINALS.BI.id;
const dirArr = direction === 'SEA-BI' ? TERMINALS.BI.id  : TERMINALS.SEA.id;

const lvOnRoute = lv && !lv.AtDock &&
  lv.DepartingTerminalID === dirDep && lv.ArrivingTerminalID === dirArr;

// Vessel on return leg heading toward our departure terminal
const lvApproaching = lv && !lv.AtDock && !lvOnRoute &&
  lv.DepartingTerminalID === dirArr && lv.ArrivingTerminalID === dirDep;

// Vessel is docked at the ARRIVAL terminal (wrong side) — needs to cross first
const lvAtOther = lv && lv.AtDock && lv.DepartingTerminalID === dirArr;
```

`lvApproaching` shows sailing/arriving toward the departure terminal (e.g. Wenatchee returning to SEA before the 7:55 AM SEA→BBI sailing).  
`lvAtOther` shows "AT BBI" or "AT SEA" — vessel is parked at the wrong end and must cross first.

### Card states

| State | Condition | Pin position |
|-------|-----------|-------------|
| `fallback` | No live vessel | Hidden |
| `at-dock` | `lv.AtDock` or no route match | 3% (SEA side) or 97% (BBI side) |
| `sailing` | Underway, ETA > 5 min | Along track |
| `arriving` | Underway, ETA ≤ 5 min | Near arrival end |
| `delayed` | Underway, ETA > 5 min late | Along track |
| `oos` | `!lv.InService` | Hidden (shows scheduled times) |

### Progress track

- SEA always left (0%), BI always right (100%)
- `nc-track-fill` width = 0% when at-dock; = pin% when sailing
- Ferry icon rotation: `((direction === 'SEA-BI') !== lvApproaching) ? 90 : -90`
- `updateProgress()` fires every 10s via `cdTimer`; uses `cdTarget` (no dependency on `LeftDock`)

### Column labels

SEA is always left, BBI always right regardless of direction tab.

**SEA→BBI tab:**

| State | SEA col (left) | BBI col (right) |
|-------|----------------|-----------------|
| `at-dock` (vessel at SEA) | DEPARTS SEA + `next.depart` (primary) | ARRIVES BBI + `next.arrive` |
| `at-dock` (`lvAtOther` — vessel at BBI) | DEPARTS SEA + `next.depart` (primary) | AT BBI |
| `lvApproaching` | ARRIVES SEA + `approachEta` (primary) | DEPARTED BBI + `actualDepart` |
| `sailing`/`arriving` | DEPARTED SEA + `actualDepart` | ARRIVES BBI + `arriveTime` (primary) |

**BBI→SEA tab:**

| State | SEA col (left) | BBI col (right) |
|-------|----------------|-----------------|
| `at-dock` (vessel at BBI) | ARRIVES SEA + `next.arrive` | DEPARTS BBI + `next.depart` (primary) |
| `at-dock` (`lvAtOther` — vessel at SEA) | AT SEA | DEPARTS BBI + `next.depart` (primary) |
| `lvApproaching` | DEPARTED SEA + `actualDepart` | ARRIVES BBI + `approachEta` (primary) |
| `sailing`/`arriving` | ARRIVES SEA + `arriveTime` (primary) | DEPARTED BBI + `actualDepart` |

---

## CSS variables

```css
--navy:       #060f1f   /* page background */
--navy-mid:   #0b1a30   /* mid-depth surface */
--navy-card:  #0e2040   /* card surface */
--navy-light: #162d52   /* hover/active surface */
--teal:       #00c9a7   /* primary accent */
--blue:       #2196f3   /* secondary accent */
--amber:      #ffc947   /* warning */
--red:        #ff5449   /* alert / departed */
--white:      #eef3ff   /* primary text */
--mid:        #8099c0   /* secondary text */
--dim:        #3a5070   /* muted / labels */
--border:     rgba(255,255,255,0.07)

/* Card state badge colors */
--st-sailing:   #58d8ae
--st-arriving:  #eec05b
--st-atdock:    #71bfff
--st-delayed:   #f08f47
--st-departed:  #8294a7
--st-oos:       #6c7680
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

Two separate maps coexist:

**1. Inline SVG route map** (`#ferry-map-svg`) — main vessel section
- Static SVG with hand-crafted Puget Sound landmass paths, dashed bezier route, terminal label `<g>` elements
- Vessel markers injected into `<g id="vessel-markers">` as teardrop SVG paths via `innerHTML`, rotated by `Heading`
- Terminal labels (`term-bi`, `term-sea`) dynamically resize via `updateTermLabel()` to show animated dock dots
- Pan/zoom via `initMapInteraction()` — touch pinch + drag, double-tap to reset
- Vessel tap → `initMapPopup()` → card slides up with vessel detail (speed, ETA, dep time)

**2. Leaflet miniMap** (`#miniMapEl`) — inside vessel detail popup
- Leaflet 1.9.4 fully inlined; OSM tile layer, no API key
- Created fresh on popup open (`openMiniMap()`), destroyed on close
- Shows vessel GPS position + heading on interactive map

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
2. Bump `const BUILD` (r73 → r74, etc.)
3. Push directly to `main` — `git push origin main` (working on `main` directly in Codespaces)
4. GitHub Pages auto-deploys in ~30s
5. User may need hard cache clear on iOS Safari (`?bust=N` appended to URL)

**Always push live immediately — commit → push to `main`. No PRs, no branches, no waiting.**

**Commit & push EVERY change, not just `ferry.html`.** The user keeps a clean working tree — never leave files uncommitted. After any edit (app code, config like `.mcp.json`, notes like this file, anything), commit and push to `main` without being asked, even when the change doesn't affect the live site. The only pause is to check that no file being pushed contains a secret/token.

---

## Anti-regression notes

- **Never use `lv.Eta` for future scheduled trips** — live ETA only valid for the current active trip. Upcoming rows always use `d.arrive` (scheduled).
- **`vesselList` always defaults to `[]`** on API failure — never undefined.
- **`getReturnDeparture()`** temporarily swaps global `direction` — must remain atomic.
- **Leaflet miniMap** must only be created after its container is visible (`openMiniMap` uses a 50ms timeout).
- **`lvApproaching`**: vessel on return leg → show sailing/arriving, not at-dock. Track position, ferry rotation, and column labels all have separate `lvApproaching` branches.
- **`lvAtOther`**: vessel docked at arrival terminal → card shows "AT BBI" / "AT SEA". Both this and `lvApproaching` affect endpoint dot classes.
- **`approachEta` null guard**: `cardState = (approachEta && minsTo(approachEta) <= 5) ? 'arriving' : 'sailing'` — `minsTo(null)` returns a large negative (null coerces to 0) which would wrongly pass the `<= 5` check without the guard.
- **`cdTarget` fallback**: `atDock ? next.depart : (arriveTime || next.depart)` — never leave cdTarget null while sailing; null produces "Departed" in the pill.
- **Track fill vs pin**: at-dock → fill = 0%, pin = 3%/97%. Sailing → fill = pin = barPct.
- **`cdTarget`** drives both the pill and `updateProgress()`. It's set in `renderSchedule()` and read by the interval callbacks as a closure variable.
- **Upcoming slice**: `upcoming.slice(1, 4)` — skip index 0 (the active sailing already shown in the featured card); show the next 3.
- **`DepartingTerminalID` when `AtDock=true`** = the terminal the vessel IS currently at (not where it's departing to). This is how `lvAtOther` works.
- **Vessel color palette** (`VESSEL_PALETTE`, indexed by stable hash of vessel name): `#00c9a7`, `#ffc947`, `#f472b6`, `#60a5fa`, `#fb923c`, `#a3e635`, `#c084fc`, `#f87171`. Docked state shown by dimmer glow only — never a different color.

---

## Known issues

- **CORS on `file://`**: Live API data won't load from disk. Use `npx serve .` locally.
- **Mobile cache**: iOS Safari aggressively caches. Hard-clear or `?bust=N` after deploy.
- **Transient two-vessel glitch**: Very briefly after one vessel docks, both vessels may appear heading the same direction as the API reports stale position data. Clears on next poll. Not worth fixing — it's a WSDOT data artifact.
