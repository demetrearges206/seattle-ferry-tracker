# Seattle Ferry Tracker

Real-time WSDOT Seattle ↔ Bainbridge Island ferry tracker. Single self-contained HTML file — no build step, no dependencies to install.

**Live app:** https://demetrearges206.github.io/seattle-ferry-tracker/ferry.html

## What it does

- **Current Sailing** — featured card showing the next (or active) departure with live vessel status, ETA countdown, and return departure time
- **Live Vessels map** — interactive Leaflet map with vessel positions updated from the WSDOT API; custom GeoJSON coastlines (no tile server required)
- **Upcoming sailings** — next several departures with scheduled arrival times
- **Full schedule toggle** — expand to see the complete day's timetable
- **Terminal Wait Times** — drive-up and reservation wait times for both terminals
- Direction toggle: Seattle → Bainbridge or Bainbridge → Seattle

## Data sources

All data from the [Washington State Ferries API](https://www.wsdot.wa.gov/ferries/api/vessels/documentation/):

| Endpoint | Used for |
|----------|----------|
| `Vessellocations/{apikey}` | Live vessel positions, ETA, at-dock status |
| `Schedule/GetSchedule/{apikey}` | Daily departure/arrival timetable |
| `TerminalWaitTimes/{apikey}` | Drive-up and reservation wait times |

API key is public (WSDOT provides a default key for demonstration use).

## Local dev

Just open `ferry.html` in a browser. No server needed — all assets are inlined (Leaflet 1.9.4 CSS+JS, GeoJSON coastlines, custom CSS/JS).

To test live API data, open via `http://` rather than `file://` to avoid CORS restrictions on some browsers. A simple local server works:

```bash
npx serve .
# or
python3 -m http.server 8080
```

Then visit `http://localhost:8080/ferry.html`.

## Deploy to GitHub Pages

1. Push `ferry.html` (and this README) to the `main` branch
2. Go to **Settings → Pages**
3. Set Source to **Deploy from a branch → main → / (root)**
4. Save — Pages will build in ~30s
5. App is live at `https://<your-username>.github.io/seattle-ferry-tracker/ferry.html`

## Build history

| Build | Changes |
|-------|---------|
| r31 | Inlined Leaflet 1.9.4 (CDN was render-blocking); progressive cache-first boot; improved map contrast |
| r32 | Fixed "Stale · just now" on load; featured card redesign (vessel name, arrival label, return dep); `partial` status state |
| r33 | Vessel/badge above eyebrow; Terminal Wait Times moved below Live Vessels |
| r34 | Removed broken mini-map; fixed upcoming arrival times (live ETA was contaminating future trips) |
| r35 | Map moved above Upcoming section; countdown pill "to arrival" sublabel; return dep moved to small footer text |
