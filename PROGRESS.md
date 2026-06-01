# Seattle Ferry Tracker — Progress Log

## Current build: r73

Live at `https://demetrearges206.github.io/seattle-ferry-tracker/ferry.html`

---

## Recent sprint: Map polish + card logic (r65–r73)

### Map overhaul (r65–r69)

The app switched from a Leaflet tile map in the vessel section to a hand-crafted inline SVG map showing just the SEA–BBI corridor. The Leaflet map was moved to a popup (the "miniMap") that appears when you tap a vessel marker.

Key decisions made:
- **Inline SVG** for the main route map: faster, no tile loading, no attribution clutter, fully controllable styling
- **Terminal abbrev changed from "BI" to "BBI"** to avoid confusion with BI state abbreviation (Rhode Island)
- **Vessel markers** as teardrop SVG paths injected into `<g id="vessel-markers">`, rotated by API `Heading` field
- **Popup** slides up from bottom on vessel tap; shows name, speed, dep time, ETA; miniMap inside it
- **Ferry icon** enlarged to 34px on the progress track card

### Terminal dock dots (r66–r68)

When a vessel is docked, animated pulse dots appear to the left of the terminal label in the SVG map. The label rect expands leftward only — text stays right-anchored.

- Dot pulse: SVG `<animate>` on `r` (3→5→3) and `opacity` (1→0.45→1), 2.2s, staggered per dot
- Padding of 10px inside the label box accommodates the pulse expansion (max r=5)
- `updateTermLabel(termId, vessels, cX, cW, cTX, dotCY)` — single function handles both terminals
- Call sites: `updateTermLabel('term-bi', dockedAtBI, 547, 36, 565, 427)` and `updateTermLabel('term-sea', dockedAtSEA, 861, 38, 880, 471)`

### Card state: lvAtOther (r70)

**Problem:** When Wenatchee was docked at SEA (`DepartingTerminalID=SEA`) while user was on the BBI→SEA tab, the card said "DEPARTS BBI" — but the vessel was at the wrong terminal entirely. Map showed dot at SEA, card implied vessel was at BBI.

**Fix:** Added `lvAtOther = lv && lv.AtDock && lv.DepartingTerminalID === dirArr` — catches the case where the vessel is parked at the arrival terminal. Card now shows "AT SEA" (hollow dot at SEA side) and "DEPARTS BBI 7:55 AM" reflecting the next scheduled departure in the correct direction. Endpoint dot classes also updated to match actual vessel position.

**Key invariant confirmed:** When `AtDock=true`, `DepartingTerminalID` = where the vessel currently IS, not where it's going.

### Upcoming table redesign (r71–r72)

- Removed active sailing from upcoming list: `upcoming.slice(1, 4)` instead of `slice(0, 3)`
- 3-column grid layout: vessel+time | ETA column | countdown pill
- ETA column is stacked: "ETA" label on top, "→ 8:30 AM" below
- Countdown pill shows time until departure ("1h 6m", "44m", "12m", "Leaving", "Departed")

### Null ETA crash fix (r73)

**Problem:** When `lvApproaching=true` and `lv.Eta=null` (WSDOT omits ETA briefly after departure), the card showed the "Arriving" badge with dashes for arrival time and "Departed" in the countdown pill. This was seen live at ~7:11 AM.

**Root cause:** `minsTo(null)` evaluates `(0 - Date.now()) / 60000` — a large negative number — which always passes `<= 5`. The `lvApproaching` cardState branch had no null guard on `approachEta`, unlike the `liveEta` branch at the line below which already had one.

**Fix:**
```js
// Before (buggy):
cardState = minsTo(approachEta) <= 5 ? 'arriving' : 'sailing';

// After:
cardState = (approachEta && minsTo(approachEta) <= 5) ? 'arriving' : 'sailing';
```

Also added `cdTarget = atDock ? next.depart : (arriveTime || next.depart)` — defense-in-depth so a null `arriveTime` never shows "Departed" in the pill while the vessel is actually sailing.

---

## Architecture decisions worth remembering

| Decision | Rationale |
|----------|-----------|
| Single `ferry.html`, no build step | Easy to inspect, version, and hard-cache-bust on iOS |
| SVG route map, Leaflet miniMap in popup | SVG is faster and cleaner for a fixed corridor; full map UX preserved for when you want it |
| `DepartingTerminalID` when `AtDock=true` = current terminal | Confirmed against live API; drives `lvAtOther` detection |
| Plain `git push origin main` from Codespaces | Dev moved from code.claude.com web sessions to a Codespaces terminal — no forced feature branch, full network access. The old `git push origin HEAD:main` workaround and the git-trigger Figma/WSDOT sync workflows are gone (see CLAUDE.md "Working environment"). |
| Bainbridge abbrev = "BBI" | Avoids confusion with RI (Rhode Island) two-letter abbreviation |
| `upcoming.slice(1, 4)` | Index 0 is the active sailing shown in the featured card; showing it twice was redundant |
| `approachEta &&` guard before `minsTo()` | `minsTo(null)` returns a large negative which passes `<= 5`; same pattern used for `liveEta` |

---

## What's working well

- Live vessel state transitions (at-dock → sailing → arriving → at-dock) render correctly
- `lvApproaching` and `lvAtOther` cover all real-world docking scenarios observed in production
- Null ETA from WSDOT no longer causes garbled "Arriving" state
- Map centering, dot animations, and terminal label expansion all verified live this morning (r73, 7:39–7:40 AM)

---

## Next steps / open items

### Possible improvements
- **Pinch-to-zoom snap-back**: The plan file (r67) identified a race condition between two `touchend` listeners — `wasPinching=false` clears before the double-tap guard reads it, causing a zoom reset after pinch. Not yet implemented. Fix: add `pinchEndTime` variable, guard double-tap with 500ms cooldown.
- **Vessel popup speed/departure data**: Plan (r67) called for adding `Speed` and `LeftDock` departure time to the tap-on-vessel popup card. Currently shows name, ETA, route only.
- **Schedule bulletin / service alerts**: `schedulebulletins` API endpoint exists but is not surfaced in the UI.
- **Wait times section**: `renderWaitTimes()` renders terminal wait/reservation data but the section may be sparse when no reservations are active — worth reviewing UX.

### Known transient issues (not worth fixing)
- **Two-vessel same-direction flicker**: Briefly visible when one vessel is transitioning to docked state. API reports stale position for ~1 poll cycle. Clears automatically.
- **WSDOT ETA briefly null after departure**: Now handled gracefully by r73 null guard — falls back to `sailing` state rather than false `arriving`.
