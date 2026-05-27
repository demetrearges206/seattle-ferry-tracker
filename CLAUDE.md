# Seattle Ferry Tracker — project notes

## Project goal

Real-time WSDOT Seattle ↔ Bainbridge Island ferry tracker. Single deliverable: `ferry.html` — a fully self-contained HTML file with all CSS, JS, and Leaflet 1.9.4 inlined. No build step. Deployed to GitHub Pages at `https://demetrearges206.github.io/seattle-ferry-tracker/ferry.html`.

## Current state (r35)

- `const BUILD = 'r35'` in ferry.html
- Featured card (`#schedFeatured`) renders above the Live Vessels map section
- Live Vessels map renders between featured card and Upcoming list
- Upcoming rows always use scheduled arrival (no live ETA contamination)
- `partial` status state (amber dot): schedule works but vessels API offline
- Direction toggle: `SEA-BI` (Seattle → Bainbridge) or `BI-SEA` (Bainbridge → Seattle)

## File map

- `ferry.html` — entire app. All CSS, JS, and Leaflet 1.9.4 inlined. ~215KB.
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

## Known issues / open threads

- **Figma MCP**: To be configured once user has their Figma API token. Add to `.claude/settings.json`:
  ```json
  {
    "mcpServers": {
      "figma": {
        "command": "npx",
        "args": ["-y", "@figma/mcp"],
        "env": { "FIGMA_ACCESS_TOKEN": "<your-token>" }
      }
    }
  }
  ```
- **CORS on `file://`**: Live API data won't load when opening ferry.html directly from disk in some browsers. Use `npx serve .` for local dev.
- **Mobile cache**: After deploy, iOS Safari aggressively caches. Hard-clear or append `?bust=N` to URL to force reload.
- **API key**: The default WSDOT demo key is public and shared. May occasionally rate-limit during high traffic. If needed, register for a key at wsdot.wa.gov.

## Workflow

1. Edit `ferry.html` here in Claude Code
2. Bump `const BUILD` (r35 → r36, etc.) to confirm new deploy loaded
3. Commit and push to `main`
4. GitHub Pages auto-deploys in ~30s
5. Remind user to hard-clear mobile cache if needed

## Anti-regression notes

- **Never use `lv.Eta` for future scheduled trips** — the live ETA is only valid for the vessel's current active trip. Upcoming rows always use `d.arrive` (scheduled time).
- **`vesselList` always defaults to `[]`** on API failure — never leave it `undefined`. All consumers guard with `Array.isArray(vesselList)`.
- **`getReturnDeparture()`** temporarily swaps the global `direction` variable and restores it. Don't refactor this without ensuring the swap/restore is atomic.
- **Leaflet map container** must be visible (non-zero dimensions) before `L.map()` initializes, or tiles/SVG pane won't have positioning rules. The map is initialized once on load; if the container is hidden/shown, call `map.invalidateSize()`.
