#!/usr/bin/env python3
"""
Fetch WSDOT Traveler API snapshots and write them to api-snapshots/.

Triggered by .github/workflows/wsdot-snapshot.yml when api-snapshots/request.txt changes.
Reads request.txt for keywords: vessels, schedule, all.
Writes pretty-printed JSON + a human-readable summary markdown.
"""

import json
import os
import traceback
import urllib.request
from datetime import datetime, timezone

API_KEY  = os.environ.get("WSDOT_API_KEY", "7d7a5056-0f82-4547-a870-6db3db67b9d7")
BASE_URL = "https://www.wsdot.wa.gov/ferries/api"
OUT_DIR  = "api-snapshots"
TODAY    = datetime.now(timezone.utc).strftime("%Y-%m-%d")

ROUTES = [
    ("Seattle-Bainbridge", "SEA-BI"),
    ("Bainbridge-Seattle", "BI-SEA"),
]


def fetch(url):
    print(f"  GET {url}")
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode()
        print(f"  HTTP {resp.status} ({len(raw)} bytes)")
        return json.loads(raw)


def save(filename, data):
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    size = len(json.dumps(data))
    print(f"  saved {path} ({size:,} bytes)")
    return path


def fetch_vessels():
    print("\n=== Vessel Locations ===")
    locs = None
    try:
        locs = fetch(f"{BASE_URL}/vessels/rest/vessellocations/{API_KEY}")
        save("vessel-locations.json", locs)
        print(f"  {len(locs)} vessels returned")
    except Exception:
        print("  ERROR fetching vessellocations:")
        traceback.print_exc()

    print("\n=== Vessel Basics ===")
    basics = None
    try:
        basics = fetch(f"{BASE_URL}/vessels/rest/vesselbasics/{API_KEY}")
        save("vessel-basics.json", basics)
        print(f"  {len(basics)} vessel basics returned")
    except Exception:
        print("  ERROR fetching vesselbasics (endpoint may differ):")
        traceback.print_exc()
        # Try alternate path
        try:
            basics = fetch(f"{BASE_URL}/vessels/rest/vesselverbose/{API_KEY}")
            save("vessel-basics.json", basics)
            print(f"  {len(basics)} vessel verbose records returned (alternate endpoint)")
        except Exception:
            print("  Alternate endpoint also failed.")

    # Write summary
    lines = [
        f"# WSDOT Vessel Snapshot — {TODAY}\n",
        f"Fetched at: {datetime.now(timezone.utc).isoformat()}\n",
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
    lines = [f"# WSDOT Schedule Snapshot — {TODAY}\n",
             f"Fetched at: {datetime.now(timezone.utc).isoformat()}\n"]

    for route_name, abbrev in ROUTES:
        url = f"{BASE_URL}/schedule/rest/schedule/GetSchedule/{API_KEY}/{TODAY}/{route_name}"
        try:
            data = fetch(url)
            save(f"schedule-{abbrev}-{TODAY}.json", data)
        except Exception:
            print(f"  ERROR fetching schedule for {abbrev}:")
            traceback.print_exc()
            lines.append(f"\n## {abbrev}\n*Unavailable*\n")
            continue

        sailings = []
        try:
            # WSDOT schedule structure: ScheduledRoutes > ScheduledTimes
            # Try multiple known structures
            times_found = False
            for top_key in ("ScheduledRoutes", "TerminalCombos"):
                for route_block in data.get(top_key, []):
                    for times_key in ("ScheduledTimes", "Times"):
                        for s in route_block.get(times_key, []):
                            dep    = s.get("DepartingTime") or s.get("DepartTime") or "?"
                            arr    = s.get("ArrivingTime")  or s.get("ArriveTime")  or "?"
                            vessel = s.get("VesselName") or "?"
                            sailings.append((dep, arr, vessel))
                            times_found = True
            if not times_found:
                # Dump the top-level keys so we can learn the structure
                lines.append(f"\n## {abbrev} — raw top-level keys: {list(data.keys())}\n")
                continue
        except Exception:
            traceback.print_exc()

        lines.append(f"\n## {abbrev} — {len(sailings)} sailings\n")
        lines.append("| Departs | Arrives | Vessel |")
        lines.append("|---------|---------|--------|")
        for dep, arr, ves in sailings:
            lines.append(f"| {dep} | {arr} | {ves} |")

    with open(os.path.join(OUT_DIR, f"schedule-summary-{TODAY}.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  saved {OUT_DIR}/schedule-summary-{TODAY}.md")


def main():
    log_lines = [f"Run at: {datetime.now(timezone.utc).isoformat()}",
                 f"API_KEY prefix: {API_KEY[:8]}..."]

    # Monkey-patch fetch to also log to file
    original_fetch = globals()['fetch']
    def logged_fetch(url):
        try:
            result = original_fetch(url)
            log_lines.append(f"OK  {url}")
            return result
        except Exception as e:
            log_lines.append(f"ERR {url} — {type(e).__name__}: {e}")
            raise
    globals()['fetch'] = logged_fetch

    request_file = os.path.join(OUT_DIR, "request.txt")
    if not os.path.exists(request_file):
        print("No request.txt found — nothing to do.")
        return

    with open(request_file) as f:
        keywords = {line.strip().lower() for line in f
                    if line.strip() and not line.strip().startswith("#")}

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

    with open(os.path.join(OUT_DIR, "last-run.log"), "w") as f:
        f.write("\n".join(log_lines) + "\n")
    print("Wrote last-run.log")


if __name__ == "__main__":
    main()
