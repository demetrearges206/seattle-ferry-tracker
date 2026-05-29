#!/usr/bin/env python3
"""
Fetch WSDOT Traveler API snapshots and write them to api-snapshots/.

Triggered by .github/workflows/wsdot-snapshot.yml when api-snapshots/request.txt changes.
Reads request.txt for keywords: vessels, schedule, all.
Writes pretty-printed JSON + a human-readable summary markdown.

API format: key is a QUERY PARAMETER (?apiaccesscode=), NOT a path segment.
  Vessels:  GET https://www.wsdot.wa.gov/ferries/api/vessels/rest/vessellocations?apiaccesscode={key}
  Schedule: GET https://www.wsdot.wa.gov/ferries/api/schedule/rest/scheduletoday/{dep_id}/{arr_id}/false?apiaccesscode={key}
"""

import json
import os
import traceback
import urllib.request
from datetime import datetime, timezone

API_KEY   = os.environ.get("WSDOT_API_KEY", "7d7a5056-0f82-4547-a870-6db3db67b9d7")
VESS_BASE = "https://www.wsdot.wa.gov/ferries/api/vessels/rest"
SCHED_BASE = "https://www.wsdot.wa.gov/ferries/api/schedule/rest"
OUT_DIR   = "api-snapshots"
TODAY     = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# Terminal IDs
SEA_ID = 7
BI_ID  = 3

ROUTES = [
    (SEA_ID, BI_ID, "SEA-BI"),
    (BI_ID, SEA_ID, "BI-SEA"),
]

log_lines = []


def api_url(base, path):
    return f"{base}/{path}?apiaccesscode={API_KEY}"


def fetch(url):
    log_lines.append(f"GET {url}")
    print(f"  GET {url}")
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode()
        log_lines.append(f"  → HTTP {resp.status} ({len(raw):,} bytes)")
        print(f"  → HTTP {resp.status} ({len(raw):,} bytes)")
        return json.loads(raw)


def safe_fetch(url, label):
    try:
        return fetch(url)
    except Exception as e:
        msg = f"  ERROR {label}: {type(e).__name__}: {e}"
        log_lines.append(msg)
        print(msg)
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

    # Write summary
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
    log_lines.append(f"Run at: {datetime.now(timezone.utc).isoformat()}")
    log_lines.append(f"API_KEY prefix: {API_KEY[:8]}...")

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
