#!/usr/bin/env python3
"""Parse log files into CSVs."""
import re
import csv
import os

BASE = "/Users/dashing_dm/Documents/Firmware/report_assets"

# --- host_telemetry.csv ---
host_telem_pat = re.compile(
    r'\[telemetry\] seq=(\d+) temp=([\d.]+)C ax=([-\d.]+)g ay=([-\d.]+)g az=([-\d.]+)g '
    r'spd=([\d.]+)km/h rpm=(\d+) throttle=([\d.]+)% fault=(\d+)'
)
rows = []
with open(f"{BASE}/logs/host_telemetry.txt") as f:
    for line in f:
        m = host_telem_pat.search(line)
        if m:
            rows.append(m.groups())

with open(f"{BASE}/csv/host_telemetry.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["seq","temperature_c","accel_x_g","accel_y_g","accel_z_g","speed_kmh","rpm","throttle_pct","fault_code"])
    w.writerows(rows)
print(f"host_telemetry.csv: {len(rows)} rows")

# --- firmware_telemetry.csv ---
fw_telem_pat = re.compile(
    r'\[telemetry\] seq=(\d+) temp=([\d.]+)C ax=([-\d.]+) ay=([-\d.]+) az=([-\d.]+) '
    r'spd=([\d.]+)km/h rpm=(\d+) thr=([\d.]+)% valid=(\w+) tick=(\d+)'
)
rows = []
with open(f"{BASE}/logs/firmware_telemetry.txt") as f:
    for line in f:
        m = fw_telem_pat.search(line)
        if m:
            rows.append(m.groups())

with open(f"{BASE}/csv/firmware_telemetry.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["seq","temperature_c","accel_x","accel_y","accel_z","speed_kmh","rpm","throttle_pct","valid","tick"])
    w.writerows(rows)
print(f"firmware_telemetry.csv: {len(rows)} rows")

# --- firmware_watchdog.csv ---
wd_pat = re.compile(r'\[watchdog\] healthy: sensor=(\d+) processor=(\d+) logger=(\d+)')
rows = []
line_num = 0
with open(f"{BASE}/logs/firmware_telemetry.txt") as f:
    for i, line in enumerate(f, 1):
        m = wd_pat.search(line)
        if m:
            rows.append((i, *m.groups()))

with open(f"{BASE}/csv/firmware_watchdog.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["line_num","sensor_beats","processor_beats","logger_beats"])
    w.writerows(rows)
print(f"firmware_watchdog.csv: {len(rows)} rows")

# --- host_stats_snapshot.csv ---
# Parse status command outputs from host_commands.txt
status_pat = re.compile(r'fault mode:\s*(\w+)', re.IGNORECASE)
sensor_samples_pat = re.compile(r'sensor samples:\s*(\d+)', re.IGNORECASE)
telemetry_frames_pat = re.compile(r'telemetry frames:\s*(\d+)', re.IGNORECASE)
sensor_drops_pat = re.compile(r'sensor drops:\s*(\d+)', re.IGNORECASE)
telemetry_drops_pat = re.compile(r'telemetry drops:\s*(\d+)', re.IGNORECASE)

snapshots = []
# The host status output uses "Fault mode       : none" format
fault_pat2 = re.compile(r'Fault mode\s*:\s*(\S+)')
sensor_samples_pat2 = re.compile(r'Sensor samples\s*:\s*(\d+)')
telemetry_frames_pat2 = re.compile(r'Telemetry frames\s*:\s*(\d+)')
sensor_drops_pat2 = re.compile(r'Sensor drops\s*:\s*(\d+)')
telemetry_drops_pat2 = re.compile(r'Telemetry drops\s*:\s*(\d+)')

with open(f"{BASE}/logs/host_commands.txt") as f:
    content = f.read()

# Split on "Fault mode" sections (each status block starts with Fault mode line)
blocks = re.split(r'(?=Fault mode\s*:)', content)
snapshot_time = 0
for block in blocks:
    fm = fault_pat2.search(block)
    ss = sensor_samples_pat2.search(block)
    tf = telemetry_frames_pat2.search(block)
    sd = sensor_drops_pat2.search(block)
    td = telemetry_drops_pat2.search(block)
    if fm and ss:
        snapshot_time += 1
        snapshots.append((
            snapshot_time,
            fm.group(1),
            ss.group(1),
            tf.group(1) if tf else 0,
            sd.group(1) if sd else 0,
            td.group(1) if td else 0
        ))

with open(f"{BASE}/csv/host_stats_snapshot.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["snapshot_time","fault_mode","sensor_samples","telemetry_frames","sensor_drops","telemetry_drops"])
    w.writerows(snapshots)
print(f"host_stats_snapshot.csv: {len(snapshots)} rows")

# Show sample of host_commands for debugging
print("\n--- host_commands.txt sample ---")
with open(f"{BASE}/logs/host_commands.txt") as f:
    print(f.read()[:2000])
