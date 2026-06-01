# Seattle Ferry Tracker — project notes

## Project goal

Real-time WSDOT Seattle ↔ Bainbridge Island ferry tracker. Single deliverable: `ferry.html` — a fully self-contained HTML file with all CSS and JS inlined (no map library, no Leaflet — the map is a hand-built inline SVG). No build step. Deployed to GitHub Pages at `https://demetrearges206.github.io/seattle-ferry-tracker/ferry.html`.

## Current state (r77)

- `const BUILD = 'r77'` in ferry.html — bump on every change
- **r77:** removed Leaflet and the vessel-popup mini-map entirely (r75 had added them; they provided no value over the existing SVG map). The vessel-tap popup is text-only. See [Map implementation](#map-implementation).
- Inter font inlined as base64 at deploy time via `.github/workflows/pages.yml` (not CDN)
- Direction toggle: `SEA-BBI` (Seattle → Bainbridge) or `BBI-SEA` (Bainbridge → Seattle). Tab labels read **"To Bainbridge" / "To Seattle"**. Default direction is smart: remembered choice (`ferry_dir_v1`) → geolocation → time-of-day (before noon → `BI-SEA`).
- Featured card (`#schedFeatured`) renders above the Vessels/map section
- Upcoming section (`#schedContent`) shows `upcoming.slice(1, 4)` — skips the active sailing (already in featured card), shows next 3
- Vessel map markers: teardrop SVG icon in inline SVG map, per-vessel palette color (underway vessels only — docked boats show as terminal dots). Vessel tap → text popup. Featured vessel is drawn **last** (paints on top); a `#mapLegend` overlay lists the two route boats + ETAs
- Progress track at bottom of featured card — **BBI always left (0%), SEA always right (100%)** to match the map; ferry icon moves along it via `visPct = 100 - barPct`
- **r74 redesign — color = two independent axes:** **vessel color = identity** (`--vc`, set inline on `.next-card`; drives eyebrow strip, vessel name, lead metric, route track), **status color = state** (the badge only). New status palette avoids the vessel gold/green band. Card gained an **eyebrow ribbon** (`::before` in `--vc`), an **"as of HH:MM"** freshness stamp, and a big **lead metric** ("Departs in / Arrives in" + number) as the hero. Build tag hidden — long-press the route name to reveal.
- **`getDirectionVessel()` + `featuredVessel` global:** the card features the vessel actually positioned for the selected direction (from live positions), not the schedule's planned hull
- `lvApproaching` state: vessel on return leg toward departure terminal shows sailing/arriving (not at-dock)
- `lvAtOther` state: vessel docked at the wrong terminal (arrival side) — card shows "AT BBI" or "AT SEA" with next scheduled departure

## File map

- `ferry.html` — entire app (~123 KB; grows after the deploy step inlines Inter as base64)
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
let direction = 'SEA-BI';  // or 'BI-SEA' (default chosen by pickDefaultDirection())
let featuredVessel = null;  // name of vessel in the featured card — drawn on top in updateMap()
let lastUpdate = null;      // Date of last successful refresh
let cdTimer = null;         // interval handle for 10s countdown ticks
```

### Key functions

| Function | Purpose |
|----------|---------|
| `refresh(fullRefresh)` | Main fetch loop — `Promise.allSettled` over all APIs, updates state, re-renders |
| `renderSchedule()` | Featured card → `#schedFeatured`; upcoming + full schedule → `#schedContent` |
| `renderVessels()` | Updates inline-SVG map markers + vessel strip |
| `renderWaitTimes()` | Terminal wait table (`#waitContent`) |
| `getDepartures()` | Today's departures for current `direction` from `scheduleData` |
| `getReturnDeparture(afterTime)` | Temporarily swaps `direction`; gets next opposite-direction departure |
| `getLiveVessel(name)` | Live vessel object from `vesselList` |
| `getDirectionVessel(depId, arrId)` | Live route vessel positioned to serve `depId→arrId`: underway in-direction → docked at dep → approaching dep to turn around. Drives `featuredVessel` |
| `renderMapLegend()` | `#mapLegend` overlay — the two route boats + ETAs |
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
<div class="map-section">  ← inline SVG route map (#ferry-map-svg)
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

### Progress track (r74)

- **BBI always left (0%), SEA always right (100%)** — matches the map orientation. Coordinate runs BBI=0 … SEA=100; `visPct = 100 - barPct` converts trip-progress to visual position.
- Endpoint dots **flank the line** (`gap:12px`, no SEA/BBI labels — the times row labels the terminals). Dot states use `var(--vc)`: `--docked` (solid+glow), `--destination` (ring+pulse), `--hollow` (outline).
- `.nc-track-fill` (in `--vc`) = traveled segment from origin terminal to the vessel; width = 0% when at-dock.
- `.nc-vessel-pin` = 40px ferry SVG in `--vc`, centered on the line, `display:none` at-dock/oos.
- Ferry icon rotation: `((direction === 'SEA-BI') !== lvApproaching) ? -90 : 90` (signs flipped vs r73 because of the BBI-left coordinate flip).
- `updateProgress()` fires every 10s via `cdTimer`; uses `cdTarget` (no dependency on `LeftDock`). Early-return guard skips `fallback`, `at-dock`, **and `oos`**.

### Lead metric (r74)

The hero of the card. Uppercase label + big number + unit, all in `var(--vc)`:
- at-dock / `lvApproaching` → "Departs in" + `minsTo(next.depart)`; else → "Arrives in" + `minsTo(arriveTime || next.depart)`.
- `< 0` → "Now"; `< 60` → `N min`; else → `Xh Ym` (no unit).
- `oos` → "Out of service" (26px, neutral `--mid`), label "Status".

### Column labels (r74)

**BBI is always on the LEFT, SEA always on the RIGHT** (mirrors the map) — flipped from r73. The card no longer shows a countdown pill in the header (the lead metric replaces it); labels are shorter ("FROM"/"TO").

**SEA→BBI tab:**

| State | BBI col (left) | SEA col (right) |
|-------|----------------|-----------------|
| `at-dock` (vessel at SEA) | TO BBI + `next.arrive` | FROM SEA + `next.depart` (primary) |
| `at-dock` (`lvAtOther` — vessel at BBI) | AT BBI | FROM SEA + `next.depart` (primary) |
| `lvApproaching` | DEPARTED BBI + `actualDepart` | ARRIVES SEA + `approachEta` (primary) |
| `sailing`/`arriving` | ARRIVES BBI + `arriveTime` (primary) | DEPARTED SEA + `actualDepart` |

**BBI→SEA tab:**

| State | BBI col (left) | SEA col (right) |
|-------|----------------|-----------------|
| `at-dock` (vessel at BBI) | FROM BBI + `next.depart` (primary) | TO SEA + `next.arrive` |
| `at-dock` (`lvAtOther` — vessel at SEA) | FROM BBI + `next.depart` (primary) | AT SEA |
| `lvApproaching` | ARRIVES BBI + `approachEta` (primary) | DEPARTED SEA + `actualDepart` |
| `sailing`/`arriving` | DEPARTED BBI + `actualDepart` | ARRIVES SEA + `arriveTime` (primary) |

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

/* Status badge colors (r74 — re-chosen to avoid the vessel gold/green band).
   Used ONLY by the status badge. Rendered color: var(--st-*) on a
   color-mix(in oklab, var(--st-*) 16%, transparent) background. */
--st-atdock:    #71bfff   /* blue   */
--st-sailing:   #2bc5e0   /* cyan   */
--st-arriving:  #a78bfa   /* violet */
--st-delayed:   #f0883e   /* orange */
--st-departed:  #8294a7   /* slate  */
--st-oos:       #6c7680   /* gray   */
--st-cancelled: #e9504d   /* red    */
```

**Vessel colors** (`VESSEL_COLORS`, r74 — named per-vessel map, no longer a hash-indexed palette):
`Tacoma #e2b93a` (gold), `Wenatchee #73e087` (green), plus a 12-hue ramp for the other 19 hulls. `getVesselColor(name)` looks up the map. The chosen vessel's hue is the card's `--vc` AND its map-marker color, so card and map reinforce each other. Docked state shown by dimmer glow only — never a different color.

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
| `ferry_dir_v1` | `"SEA-BI"` \| `"BI-SEA"` | Permanent — remembered direction; set when user taps a tab, read first by `pickDefaultDirection()` |

---

## Map implementation

**One map only: the inline SVG route map** (`#ferry-map-svg`) — main vessel section. **No Leaflet, no OSM, no real-world map tiles** anywhere in the app (see history below).
- Static SVG with hand-crafted Puget Sound landmass paths, dashed bezier route, terminal label `<g>` elements
- Vessel markers injected into `<g id="vessel-markers">` as teardrop SVG paths via `innerHTML`, rotated by `Heading`. **Only vessels that are underway get a tappable marker** — docked vessels `return` early in `updateMap()` and are shown as dots on the terminal labels instead
- Terminal labels (`term-bi`, `term-sea`) dynamically resize via `updateTermLabel()` to show animated dock dots
- Pan/zoom via `initMapInteraction()` — touch pinch + drag, double-tap to reset (this is the app's own SVG interaction, not a map library)
- Vessel tap → `initMapPopup()` → text popup with vessel detail (route, dep time, ETA, speed). **Text only — no embedded map.**

**History — why there's no Leaflet:** `ferry.html` long carried orphaned `openMiniMap`/`closeMiniMap` functions (Leaflet API calls to a library that was never loaded) plus a false "Leaflet 1.9.4 inlined" claim here. r75 briefly inlined Leaflet + an OSM-tile mini-map in the vessel popup, but it added no value (the main SVG map is the real UI and already pans/zooms), so **r77 removed Leaflet and the mini-map entirely** — the dead code, the inlined library, and the popup map container. Don't re-add it without a concrete reason.

---

## Status states

| State | Dot | Text |
|-------|-----|------|
| `loading` | grey, off | "Refreshing…" |
| `live` | green, pulsing | "Updated Xm ago" / "Updated just now" |
| `partial` | amber, static | "Schedule · vessels offline" |
| `stale` | red, static | "Stale · Xm ago" / "Offline" |

`setStatus()` also drives `#dataBanner` (above the featured card): `partial` → "Live vessel positions are temporarily unavailable…"; `stale` → "Data may be out of date…"; otherwise empty.

---

## Workflow

1. Edit `ferry.html`
2. Bump `const BUILD` (r77 → r78, etc.)
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
- **No map library.** The map is a hand-built inline SVG (`#ferry-map-svg`); pan/zoom is the app's own `initMapInteraction()`. Leaflet/OSM were removed in r77 — don't reintroduce a map dependency without a concrete need.
- **`lvApproaching`**: vessel on return leg → show sailing/arriving, not at-dock. Track position, ferry rotation, and column labels all have separate `lvApproaching` branches.
- **`lvAtOther`**: vessel docked at arrival terminal → card shows "AT BBI" / "AT SEA". Both this and `lvApproaching` affect endpoint dot classes.
- **`approachEta` null guard**: `cardState = (approachEta && minsTo(approachEta) <= 5) ? 'arriving' : 'sailing'` — `minsTo(null)` returns a large negative (null coerces to 0) which would wrongly pass the `<= 5` check without the guard.
- **`cdTarget` fallback**: `atDock ? next.depart : (arriveTime || next.depart)` — never leave cdTarget null while sailing; null produces "Departed" in the pill.
- **BBI-left / SEA-right coordinate flip (r74)**: the track runs BBI=0% (left) … SEA=100% (right). All pin/fill math goes through `visPct = 100 - barPct`. `updateProgress()` recomputes `visPct` independently — if you touch one, touch both. Ferry rotation signs are flipped from r73 (`-90`/`90`) for the same reason.
- **`getDirectionVessel()` (r74)**: drives `featuredVessel`, which `updateMap()` reads to sort the featured boat **last** (on top). The card's `lv` is `getDirectionVessel(...) || getLiveVessel(next.vessel)` — live position wins over the schedule's planned hull. `featVessel`/`featuredVessel` (not `next.vessel`) feed the card color, name, and `lvAny` OOS check.
- **`--vc` is set inline on `.next-card`** (`style="--vc:${vesselClr}"`) — the eyebrow `::before`, lead metric, name, and track all inherit it. Don't move it to a child or those break.
- **Track fill vs pin**: at-dock → fill = 0%, pin hidden. Sailing → pin at `visPct`, fill spans origin→pin (side depends on direction).
- **`cdTarget`** drives both the pill and `updateProgress()`. It's set in `renderSchedule()` and read by the interval callbacks as a closure variable.
- **Upcoming slice**: `upcoming.slice(1, 4)` — skip index 0 (the active sailing already shown in the featured card); show the next 3.
- **`DepartingTerminalID` when `AtDock=true`** = the terminal the vessel IS currently at (not where it's departing to). This is how `lvAtOther` works.
- **Vessel color palette** (`VESSEL_PALETTE`, indexed by stable hash of vessel name): `#00c9a7`, `#ffc947`, `#f472b6`, `#60a5fa`, `#fb923c`, `#a3e635`, `#c084fc`, `#f87171`. Docked state shown by dimmer glow only — never a different color.

---

## Known issues

- **CORS on `file://`**: Live API data won't load from disk. Use `npx serve .` locally.
- **Mobile cache**: iOS Safari aggressively caches. Hard-clear or `?bust=N` after deploy.
- **Transient two-vessel glitch**: Very briefly after one vessel docks, both vessels may appear heading the same direction as the API reports stale position data. Clears on next poll. Not worth fixing — it's a WSDOT data artifact.
