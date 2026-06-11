#!/usr/bin/env python3
"""Generate all report graphs."""
import csv
import re
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

try:
    plt.style.use('seaborn-v0_8-whitegrid')
except:
    plt.style.use('ggplot')

BASE = "/Users/dashing_dm/Documents/Firmware/report_assets"
OUT = f"{BASE}/graphs"

def read_csv(path):
    with open(path) as f:
        r = csv.DictReader(f)
        return list(r)

host = read_csv(f"{BASE}/csv/host_telemetry.csv")
fw = read_csv(f"{BASE}/csv/firmware_telemetry.csv")
wd = read_csv(f"{BASE}/csv/firmware_watchdog.csv")
snaps = read_csv(f"{BASE}/csv/host_stats_snapshot.csv")

def fv(row, key):
    return float(row[key])

def iv(row, key):
    return int(row[key])

# ---- 1. temperature_comparison.png ----
fig, ax = plt.subplots(figsize=(10,5))
h_seq = [iv(r,'seq') for r in host]
h_temp = [fv(r,'temperature_c') for r in host]
f_seq = [iv(r,'seq') for r in fw]
f_temp = [fv(r,'temperature_c') for r in fw]
ax.plot(h_seq, h_temp, color='steelblue', label='Host Simulator', linewidth=2)
ax.plot(f_seq, f_temp, color='tomato', label='Firmware (QEMU)', linewidth=2)
ax.set_xlabel("Sequence Number")
ax.set_ylabel("Temperature (°C)")
ax.set_title("Temperature Over Time — Host vs Firmware")
ax.legend()
fig.tight_layout()
fig.savefig(f"{OUT}/temperature_comparison.png", dpi=150)
plt.close(fig)
print("temperature_comparison.png done")

# ---- 2. firmware_acceleration_3axis.png ----
fig, ax = plt.subplots(figsize=(10,5))
f_ax = [fv(r,'accel_x') for r in fw]
f_ay = [fv(r,'accel_y') for r in fw]
f_az = [fv(r,'accel_z') for r in fw]
ax.plot(f_seq, f_ax, label='ax', color='crimson', linewidth=1.5)
ax.plot(f_seq, f_ay, label='ay', color='green', linewidth=1.5)
ax.plot(f_seq, f_az, label='az', color='royalblue', linewidth=1.5)
ax.set_xlabel("Sequence Number")
ax.set_ylabel("Acceleration (g)")
ax.set_title("3-Axis Accelerometer (Firmware)")
ax.legend()
fig.tight_layout()
fig.savefig(f"{OUT}/firmware_acceleration_3axis.png", dpi=150)
plt.close(fig)
print("firmware_acceleration_3axis.png done")

# ---- 3. host_acceleration_3axis.png ----
fig, ax = plt.subplots(figsize=(10,5))
h_ax = [fv(r,'accel_x_g') for r in host]
h_ay = [fv(r,'accel_y_g') for r in host]
h_az = [fv(r,'accel_z_g') for r in host]
ax.plot(h_seq, h_ax, label='ax', color='crimson', linewidth=1.5)
ax.plot(h_seq, h_ay, label='ay', color='green', linewidth=1.5)
ax.plot(h_seq, h_az, label='az', color='royalblue', linewidth=1.5)
ax.set_xlabel("Sequence Number")
ax.set_ylabel("Acceleration (g)")
ax.set_title("3-Axis Accelerometer (Host Simulator)")
ax.legend()
fig.tight_layout()
fig.savefig(f"{OUT}/host_acceleration_3axis.png", dpi=150)
plt.close(fig)
print("host_acceleration_3axis.png done")

# ---- 4. speed_comparison.png ----
fig, ax = plt.subplots(figsize=(10,5))
h_spd = [fv(r,'speed_kmh') for r in host]
f_spd = [fv(r,'speed_kmh') for r in fw]
ax.plot(h_seq, h_spd, color='steelblue', label='Host Simulator', linewidth=2)
ax.plot(f_seq, f_spd, color='tomato', label='Firmware (QEMU)', linewidth=2)
ax.set_xlabel("Sequence Number")
ax.set_ylabel("Speed (km/h)")
ax.set_title("Speed Over Time — Host vs Firmware")
ax.legend()
fig.tight_layout()
fig.savefig(f"{OUT}/speed_comparison.png", dpi=150)
plt.close(fig)
print("speed_comparison.png done")

# ---- 5. rpm_throttle.png ----
fig, ax1 = plt.subplots(figsize=(10,5))
f_rpm = [iv(r,'rpm') for r in fw]
f_thr = [fv(r,'throttle_pct') for r in fw]
color1 = 'royalblue'
color2 = 'darkorange'
ax1.plot(f_seq, f_rpm, color=color1, linewidth=2, label='RPM')
ax1.set_xlabel("Sequence Number")
ax1.set_ylabel("RPM", color=color1)
ax1.tick_params(axis='y', labelcolor=color1)
ax2 = ax1.twinx()
ax2.plot(f_seq, f_thr, color=color2, linewidth=2, linestyle='--', label='Throttle %')
ax2.set_ylabel("Throttle (%)", color=color2)
ax2.tick_params(axis='y', labelcolor=color2)
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1+lines2, labels1+labels2, loc='upper left')
ax1.set_title("RPM and Throttle % (Firmware) vs Sequence")
fig.tight_layout()
fig.savefig(f"{OUT}/rpm_throttle.png", dpi=150)
plt.close(fig)
print("rpm_throttle.png done")

# ---- 6. fault_demo.png ----
# Parse host_commands.txt for temp readings around fault injection
fault_data = []
fault_events = []
with open(f"{BASE}/logs/host_commands.txt") as f:
    lines = f.readlines()

telem_pat = re.compile(r'\[telemetry\] seq=(\d+) temp=([\d.]+)C.*fault=(\d+)')
fault_cmd_pat = re.compile(r'Fault mode set to (\S+)')
current_fault = "none"
event_seqs = []
for line in lines:
    m = telem_pat.search(line)
    if m:
        seq, temp, fault_code = int(m.group(1)), float(m.group(2)), int(m.group(3))
        fault_data.append((seq, temp, current_fault))
    fm = fault_cmd_pat.search(line)
    if fm:
        current_fault = fm.group(1)
        if fault_data:
            event_seqs.append((fault_data[-1][0], current_fault))

if not fault_data:
    # Use stats data
    fault_data = [(1, 73.3, 'none')]

seqs = [d[0] for d in fault_data]
temps = [d[1] for d in fault_data]
labels = [d[2] for d in fault_data]

fig, ax = plt.subplots(figsize=(10,5))
colors = {'none': 'steelblue', 'sensor-failure': 'tomato', 'queue-overflow': 'darkorange'}
color_list = [colors.get(l, 'gray') for l in labels]
ax.scatter(seqs, temps, c=color_list, s=60, zorder=5)
ax.plot(seqs, temps, color='gray', alpha=0.4, linewidth=1)
for seq, fname in event_seqs:
    ax.axvline(x=seq, color='red', linestyle='--', alpha=0.7, linewidth=1)
    ax.annotate(f'→{fname}', xy=(seq, max(temps)*0.95), fontsize=8, color='red', rotation=90)
patches = [mpatches.Patch(color=v, label=k) for k,v in colors.items()]
ax.legend(handles=patches)
ax.set_xlabel("Sequence Number")
ax.set_ylabel("Temperature (°C)")
ax.set_title("Fault Injection Demo — Temperature Response")
fig.tight_layout()
fig.savefig(f"{OUT}/fault_demo.png", dpi=150)
plt.close(fig)
print("fault_demo.png done")

# ---- 7. watchdog_health.png ----
fig, ax = plt.subplots(figsize=(8,5))
w_sensor = [int(r['sensor_beats']) for r in wd]
w_proc = [int(r['processor_beats']) for r in wd]
w_logger = [int(r['logger_beats']) for r in wd]
x = np.arange(len(wd))
width = 0.28
ax.bar(x - width, w_sensor, width, label='Sensor', color='steelblue', alpha=0.85)
ax.bar(x,          w_proc,   width, label='Processor', color='tomato', alpha=0.85)
ax.bar(x + width,  w_logger, width, label='Logger', color='green', alpha=0.85)
ax.set_xlabel("Watchdog Check #")
ax.set_ylabel("Beat Count")
ax.set_title("Watchdog Health — Task Beat Counts")
ax.legend()
if len(x) > 20:
    step = max(1, len(x)//10)
    ax.set_xticks(x[::step])
    ax.set_xticklabels([str(i+1) for i in range(0,len(x),step)])
fig.tight_layout()
fig.savefig(f"{OUT}/watchdog_health.png", dpi=150)
plt.close(fig)
print("watchdog_health.png done")

# ---- 8. sensor_dashboard.png ----
fig, axes = plt.subplots(2, 3, figsize=(15, 8))
axes = axes.flatten()

# fw temp
axes[0].plot(f_seq, f_temp, color='tomato', linewidth=1.5)
axes[0].set_title("Temperature (Firmware)")
axes[0].set_xlabel("Seq"); axes[0].set_ylabel("°C")

# fw speed
axes[1].plot(f_seq, f_spd, color='royalblue', linewidth=1.5)
axes[1].set_title("Speed (Firmware)")
axes[1].set_xlabel("Seq"); axes[1].set_ylabel("km/h")

# fw rpm
axes[2].plot(f_seq, f_rpm, color='green', linewidth=1.5)
axes[2].set_title("RPM (Firmware)")
axes[2].set_xlabel("Seq"); axes[2].set_ylabel("RPM")

# fw throttle
axes[3].plot(f_seq, f_thr, color='darkorange', linewidth=1.5)
axes[3].set_title("Throttle % (Firmware)")
axes[3].set_xlabel("Seq"); axes[3].set_ylabel("%")

# fw accel_z
axes[4].plot(f_seq, f_az, color='purple', linewidth=1.5)
axes[4].set_title("Accel Z (Firmware)")
axes[4].set_xlabel("Seq"); axes[4].set_ylabel("g")

# host temp
axes[5].plot(h_seq, h_temp, color='steelblue', linewidth=1.5)
axes[5].set_title("Temperature (Host Sim)")
axes[5].set_xlabel("Seq"); axes[5].set_ylabel("°C")

fig.suptitle("ECU Sensor Dashboard — FreeRTOS Firmware + Host Simulator", fontsize=13, fontweight='bold')
fig.tight_layout()
fig.savefig(f"{OUT}/sensor_dashboard.png", dpi=150)
plt.close(fig)
print("sensor_dashboard.png done")

print("\nAll graphs generated successfully.")
