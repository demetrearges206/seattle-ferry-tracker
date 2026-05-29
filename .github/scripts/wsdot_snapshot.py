#!/usr/bin/env python3
"""
Fetch WSDOT Traveler API snapshots and write them to api-snapshots/.

Triggered by .github/workflows/wsdot-snapshot.yml when api-snapshots/request.txt changes.
Reads request.txt for keywords: vessels, schedule, all.
Writes pretty-printed JSON + a human-readable summary markdown.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

API_KEY  = os.environ.get("WSDOT_API_KEY", "7d7a5056-0f82-4547-a870-6db3db67b9d7")
BASE_URL = "https://www.wsdot.wa.gov/ferries/api"
OUT_DIR  = "api-snapshots"
TODAY    = datetime.now(timezone.utc).strftime("%Y-%m-%d")

ROUTES = [
    ("Seattle-Bainbridge",   "SEA-BI"),
    ("Bainbridge-Seattle",   "BI-SEA"),
]

TERMINAL_IDS = {7: "Seattle", 3: "Bainbridge Island"}


def fetch(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def save(filename, data):
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  wrote {path} ({len(json.dumps(data))} bytes)")
    return path


def fetch_vessels():
    print("Fetching vessel locations…")
    locs  = fetch(f"{BASE_URL}/vessels/rest/vessellocations/{API_KEY}")
    save("vessel-locations.json", locs)

    print("Fetching vessel basics…")
    basics = fetch(f"{BASE_URL}/vessels/rest/vesselbasics/{API_KEY}")
    save("vessel-basics.json", basics)

    # Write human-readable summary
    lines = [
        f"# WSDOT Vessel Snapshot — {TODAY}\n",
        f"Total vessels returned: {len(locs)}\n",
        "",
        "| Vessel | InService | AtDock | From | To | ETA | Speed |",
        "|--------|-----------|--------|------|----|-----|-------|",
    ]
    for v in sorted(locs, key=lambda x: x.get("VesselName", "")):
        name    = v.get("VesselName", "?")
        insvc   = "✓" if v.get("InService") else "✗"
        docked  = "✓" if v.get("AtDock")    else "—"
        dep     = v.get("DepartingTerminalName", "—") or "—"
        arr     = v.get("ArrivingTerminalName",  "—") or "—"
        eta_raw = v.get("Eta") or ""
        speed   = v.get("Speed", 0)
        lines.append(f"| {name} | {insvc} | {docked} | {dep} | {arr} | {eta_raw} | {speed} kts |")

    lines += [
        "",
        "## Vessel basics (class / capacity)",
        "",
        "| Vessel | Class | Car Capacity | Passenger Capacity |",
        "|--------|-------|--------------|--------------------|",
    ]
    for v in sorted(basics, key=lambda x: x.get("VesselName", "")):
        name  = v.get("VesselName", "?")
        cls   = v.get("VesselSubjectID", "?")
        cars  = v.get("CarCapacity", "?")
        pax   = v.get("PassengerCapacity", "?")
        lines.append(f"| {name} | {cls} | {cars} | {pax} |")

    with open(os.path.join(OUT_DIR, "vessel-summary.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  wrote {OUT_DIR}/vessel-summary.md")


def fetch_schedule():
    print("Fetching schedules…")
    all_routes = {}
    for route_name, abbrev in ROUTES:
        url = f"{BASE_URL}/schedule/rest/schedule/GetSchedule/{API_KEY}/{TODAY}/{route_name}"
        data = fetch(url)
        all_routes[abbrev] = data
        save(f"schedule-{abbrev}-{TODAY}.json", data)

    # Human-readable summary
    lines = [f"# WSDOT Schedule Snapshot — {TODAY}\n"]
    for abbrev, data in all_routes.items():
        lines.append(f"\n## {abbrev}\n")
        sailings = []
        try:
            for t in data.get("TerminalCombos", []):
                for s in t.get("Times", []):
                    depart = s.get("DepartingTime", "")
                    arrive = s.get("ArrivingTime", "")
                    vessel = s.get("VesselName", "?")
                    sailings.append((depart, arrive, vessel))
        except Exception as e:
            lines.append(f"Parse error: {e}\n")
            continue

        lines.append("| Departs | Arrives | Vessel |")
        lines.append("|---------|---------|--------|")
        for dep, arr, ves in sailings:
            lines.append(f"| {dep} | {arr} | {ves} |")

    with open(os.path.join(OUT_DIR, f"schedule-summary-{TODAY}.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  wrote {OUT_DIR}/schedule-summary-{TODAY}.md")


def main():
    request_file = os.path.join(OUT_DIR, "request.txt")
    if not os.path.exists(request_file):
        print("No request.txt found — nothing to do.")
        return

    with open(request_file) as f:
        keywords = {line.strip().lower() for line in f if line.strip()}

    print(f"Keywords: {keywords}")
    want_all      = "all"      in keywords
    want_vessels  = "vessels"  in keywords or want_all
    want_schedule = "schedule" in keywords or want_all

    if want_vessels:
        fetch_vessels()
    if want_schedule:
        fetch_schedule()

    if not want_vessels and not want_schedule:
        print("No recognised keywords (vessels / schedule / all). Nothing fetched.")


if __name__ == "__main__":
    main()
