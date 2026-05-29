# WSDOT Ferry Attributes — Design Reference

Source: WSDOT Traveler Information API · Live snapshot 2026-05-29

---

## Vessel Fleet (21 vessels)

| Vessel | Class | In Service | Notes |
|--------|-------|-----------|-------|
| Cathlamet | Issaquah 130 | ✓ | Active |
| Chelan | Issaquah 130 | ✓ | Active |
| Chetzemoka | Kwa-di Tabil | ✓ | Active |
| Chimacum | Olympic | ✓ | Active |
| Issaquah | Issaquah 130 | ✗ | Out of service |
| Kaleetan | Super | ✗ | Out of service |
| Kennewick | Kwa-di Tabil | ✓ | Active |
| Kitsap | Issaquah 130 | ✓ | Active |
| Kittitas | Issaquah 130 | ✓ | Active |
| Puyallup | Jumbo Mark II | ✓ | Active |
| Salish | Kwa-di Tabil | ✓ | Active |
| Samish | Olympic | ✓ | Active |
| Sealth | Issaquah | ✓ | Active |
| Spokane | Jumbo | ✓ | Active |
| Suquamish | Olympic | ✓ | Active |
| Tacoma | Jumbo Mark II | ✓ | SEA–BI primary |
| Tillikum | Evergreen State | ✓ | Active |
| Tokitae | Olympic | ✓ | Active |
| Walla Walla | Jumbo | ✓ | Active |
| Wenatchee | Jumbo Mark II | ✓ | SEA–BI primary |
| Yakima | Super | ✗ | Out of service |

### Vessel classes

| Class | Typical car capacity | Notes |
|-------|---------------------|-------|
| Jumbo Mark II | ~202 | Largest in fleet |
| Jumbo | ~188 | |
| Olympic | ~144 | Mid-size |
| Issaquah 130 | ~124 | |
| Issaquah | ~124 | |
| Kwa-di Tabil | ~64 | Smaller routes |
| Super | ~100 | |
| Evergreen State | ~87 | Older heritage vessel |

---

## API Fields — `vessellocations` endpoint

`GET https://www.wsdot.wa.gov/ferries/api/vessels/rest/vessellocations?apiaccesscode={key}`

| Field | Type | Description |
|-------|------|-------------|
| `VesselName` | string | Vessel name, e.g. `"Tacoma"` |
| `Lat` | float | Current GPS latitude |
| `Lon` | float | Current GPS longitude |
| `Heading` | int | Compass heading, 0–359° |
| `Speed` | float | Speed in knots |
| `AtDock` | bool | `true` when tied up at a terminal |
| `InService` | bool | `false` = maintenance / out of rotation |
| `LeftDock` | `/Date(ms-0700)/` | Timestamp of last terminal departure |
| `Eta` | `/Date(ms-0700)/` | Live ETA at next terminal (valid only for active trip) |
| `DepartingTerminalID` | int | Terminal ID the vessel is sailing FROM |
| `DepartingTerminalName` | string | e.g. `"Seattle"` |
| `ArrivingTerminalID` | int | Terminal ID the vessel is sailing TO |
| `ArrivingTerminalName` | string | e.g. `"Bainbridge Island"` |
| `VesselID` | int | Unique vessel identifier |
| `OpRouteAbbrev` | string[] | Abbreviations for assigned routes |

**Date format:** all timestamps are `/Date(milliseconds-0700)/` strings — parse with `parseInt(str.match(/\d+/)[0])`.

**Terminal IDs used in app:**

| Terminal | ID |
|----------|----|
| Seattle | 7 |
| Bainbridge Island | 3 |

---

## App-Derived Card States

The featured card derives one of four states from live vessel data:

| State | Condition | Badge label |
|-------|-----------|-------------|
| `fallback` | No live vessel data available | *(hidden)* |
| `at-dock` | `lv.AtDock === true` OR vessel not on this route | **At Dock** |
| `sailing` | Vessel underway, ETA > 5 min | **Sailing** |
| `arriving` | Vessel underway, ETA ≤ 5 min | **Arriving** |

### `lvApproaching` sub-state

When the vessel is on the **return leg** heading back toward the current tab's departure terminal (e.g., sailing BI→SEA while viewing the SEA→BI tab), the app treats it as `sailing` or `arriving` — not `at-dock`. Column labels and track position flip accordingly.

---

## Countdown Pill States

The countdown pill appears below the ferry icon on the progress track (and in the card header).

| Condition | Display text | Style |
|-----------|-------------|-------|
| ≥ 60 min to event | `Xh Xm` | Neutral (white/muted) |
| 10–59 min to event | `Xm` | Neutral |
| 1–9 min to event | `Xm` | Red / urgent |
| 0 to −5 min | `Leaving` | Red |
| < −5 min (departed) | `Departed` | Muted grey |

The pill target (`cdTarget`) is:
- **At dock** → next scheduled departure time
- **Sailing / arriving** → live ETA at destination (or scheduled arrive time if ETA unavailable)

---

## Track / Progress Bar

SEA is always **left (0%)**, BI is always **right (100%)**, regardless of which direction tab is active.

| Card state | Track fill | Pin position |
|------------|-----------|-------------|
| `at-dock` (SEA→BI) | 0% | 3% (parked at SEA) |
| `at-dock` (BI→SEA) | 0% | 97% (parked at BI) |
| `sailing` / `arriving` | = pin % | `(1 − remaining/tripDuration) × 100`, clamped 3–97% |

Pin is repositioned every 10 seconds by `updateProgress()`.

---

## Vessel Color Palette

Each vessel gets a stable color derived from a hash of its name. Colors are always used — docked state is indicated only by a dimmer glow, not a color override.

| Index | Hex | |
|-------|-----|-|
| 0 | `#00c9a7` | teal |
| 1 | `#ffc947` | amber |
| 2 | `#f472b6` | pink |
| 3 | `#60a5fa` | blue |
| 4 | `#fb923c` | orange |
| 5 | `#a3e635` | lime |
| 6 | `#c084fc` | purple |
| 7 | `#f87171` | red |
