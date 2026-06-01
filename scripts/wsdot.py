#!/usr/bin/env python3
"""
Fetch live WSDOT Traveler API data and write readable snapshots to api-snapshots/.

Local dev tool — run it directly; the WSDOT API is reachable from Codespaces.
(The old git-trigger GitHub Actions workflow existed only because the web-browser
session couldn't reach the API. That workaround is gone.)

Usage:
    python3 scripts/wsdot.py [vessels|schedule|all]   # default: all

API key resolution: $WSDOT_API_KEY, else the working key baked into ferry.html.
API format: key is a QUERY PARAMETER (?apiaccesscode=), NOT a path segment.
  Vessels:  GET {VESS_BASE}/vessellocations?apiaccesscode={key}
  Schedule: GET {SCHED_BASE}/scheduletoday/{dep_id}/{arr_id}/false?apiaccesscode={key}

Output (api-snapshots/ is gitignored — local scratch, not committed):
  vessel-locations.json / vessel-basics.json / vessel-summary.md
  schedule-{ABBREV}-{date}.json / schedule-summary-{date}.md
"""

import json
import os
import sys
import traceback
import urllib.request
from datetime import datetime, timezone

API_KEY    = os.environ.get("WSDOT_API_KEY", "ff39cd9c-729e-40ac-b740-1cebec6226f9")
VESS_BASE  = "https://www.wsdot.wa.gov/ferries/api/vessels/rest"
SCHED_BASE = "https://www.wsdot.wa.gov/ferries/api/schedule/rest"
OUT_DIR    = "api-snapshots"
TODAY      = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# Terminal IDs
SEA_ID = 7
BI_ID  = 3

ROUTES = [
    (SEA_ID, BI_ID, "SEA-BI"),
    (BI_ID, SEA_ID, "BI-SEA"),
]


def api_url(base, path):
    return f"{base}/{path}?apiaccesscode={API_KEY}"


def fetch(url):
    print(f"  GET {url}")
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode()
        print(f"  → HTTP {resp.status} ({len(raw):,} bytes)")
        return json.loads(raw)


def safe_fetch(url, label):
    try:
        return fetch(url)
    except Exception as e:
        print(f"  ERROR {label}: {type(e).__name__}: {e}")
        traceback.print_exc()
        return None


def save(filename, data):
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  saved {path}")
    return path


def fetch_vessels():
    print("\n=== Vessel Locations ===")
    locs = safe_fetch(api_url(VESS_BASE, "vessellocations"), "vessellocations")
    if locs:
        save("vessel-locations.json", locs)

    print("\n=== Vessel Basics ===")
    basics = safe_fetch(api_url(VESS_BASE, "vesselbasics"), "vesselbasics")
    if basics:
        save("vessel-basics.json", basics)

    lines = [
        f"# WSDOT Vessel Snapshot — {TODAY}",
        f"\nFetched at: {datetime.now(timezone.utc).isoformat()}\n",
    ]

    if locs:
        lines += [
            f"\n## Live Vessel Locations ({len(locs)} total)\n",
            "| Vessel | InService | AtDock | From | To | Speed | ETA |",
            "|--------|-----------|--------|------|----|-------|-----|",
        ]
        for v in sorted(locs, key=lambda x: x.get("VesselName", "")):
            name   = v.get("VesselName", "?")
            insvc  = "✓" if v.get("InService") else "✗"
            docked = "✓" if v.get("AtDock") else "—"
            dep    = v.get("DepartingTerminalName") or "—"
            arr    = v.get("ArrivingTerminalName") or "—"
            speed  = v.get("Speed", 0)
            eta    = v.get("Eta") or "—"
            lines.append(f"| {name} | {insvc} | {docked} | {dep} | {arr} | {speed} kts | {eta} |")
    else:
        lines.append("\n*Vessel locations unavailable*\n")

    if basics:
        lines += [
            f"\n## Vessel Fleet Info ({len(basics)} vessels)\n",
            "| Vessel | Class | Cars | Passengers |",
            "|--------|-------|------|------------|",
        ]
        for v in sorted(basics, key=lambda x: x.get("VesselName", "")):
            name = v.get("VesselName", "?")
            cls  = v.get("Class") or v.get("VesselSubjectID") or "?"
            cars = v.get("CarCapacity") or v.get("RegCarDeckCapacity") or "?"
            pax  = v.get("PassengerCapacity") or v.get("MaxPassengerCount") or "?"
            lines.append(f"| {name} | {cls} | {cars} | {pax} |")
    else:
        lines.append("\n*Vessel basics unavailable*\n")

    with open(os.path.join(OUT_DIR, "vessel-summary.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  saved {OUT_DIR}/vessel-summary.md")


def fetch_schedule():
    print("\n=== Schedules ===")
    lines = [f"# WSDOT Schedule Snapshot — {TODAY}",
             f"\nFetched at: {datetime.now(timezone.utc).isoformat()}\n"]

    for dep_id, arr_id, abbrev in ROUTES:
        url = api_url(SCHED_BASE, f"scheduletoday/{dep_id}/{arr_id}/false")
        data = safe_fetch(url, f"schedule {abbrev}")
        if not data:
            lines.append(f"\n## {abbrev}\n*Unavailable*\n")
            continue

        save(f"schedule-{abbrev}-{TODAY}.json", data)

        sailings = []
        try:
            for t in data.get("TerminalCombos", []):
                for s in t.get("Times", []):
                    dep    = s.get("DepartingTime") or s.get("DepartTime") or "?"
                    arr    = s.get("ArrivingTime")  or s.get("ArriveTime")  or "?"
                    vessel = s.get("VesselName") or "?"
                    sailings.append((dep, arr, vessel))
        except Exception as e:
            lines.append(f"\n## {abbrev}\nParse error: {e}\n")
            lines.append(f"Top-level keys: {list(data.keys())}\n")
            continue

        if not sailings:
            lines.append(f"\n## {abbrev}\nNo sailings parsed. Top-level keys: {list(data.keys())}\n")
        else:
            lines.append(f"\n## {abbrev} — {len(sailings)} sailings\n")
            lines.append("| Departs | Arrives | Vessel |")
            lines.append("|---------|---------|--------|")
            for dep, arr, ves in sailings:
                lines.append(f"| {dep} | {arr} | {ves} |")

    with open(os.path.join(OUT_DIR, f"schedule-summary-{TODAY}.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  saved {OUT_DIR}/schedule-summary-{TODAY}.md")


def main():
    keyword = (sys.argv[1] if len(sys.argv) > 1 else "all").strip().lower()
    if keyword not in ("vessels", "schedule", "all"):
        print(f"Unknown keyword '{keyword}'. Use: vessels | schedule | all")
        sys.exit(1)

    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"WSDOT snapshot · keyword={keyword} · key={API_KEY[:8]}…")

    if keyword in ("vessels", "all"):
        fetch_vessels()
    if keyword in ("schedule", "all"):
        fetch_schedule()


if __name__ == "__main__":
    main()
