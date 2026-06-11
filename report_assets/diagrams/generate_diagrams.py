#!/usr/bin/env python3
"""Generate architecture diagrams."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

OUT = "/Users/dashing_dm/Documents/Firmware/report_assets/diagrams"

plt.rcParams.update({
    'font.size': 12,
    'axes.titlesize': 15,
    'axes.labelsize': 13,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'legend.fontsize': 11,
})

# ---- system_architecture.png ----
fig, ax = plt.subplots(figsize=(16, 9))
ax.set_xlim(0, 16)
ax.set_ylim(0, 9)
ax.axis('off')
ax.set_facecolor('#f8f9fa')
fig.patch.set_facecolor('#f8f9fa')

def fbox(ax, x, y, w, h, color, label, fontsize=11, text_color='white', style="round,pad=0.1"):
    box = FancyBboxPatch((x, y), w, h, boxstyle=style, facecolor=color, edgecolor='white', linewidth=1.5)
    ax.add_patch(box)
    ax.text(x+w/2, y+h/2, label, ha='center', va='center', fontsize=fontsize,
            color=text_color, fontweight='bold', wrap=True)

def outline(ax, x, y, w, h, color, label, fontsize=13):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15",
                         facecolor='none', edgecolor=color, linewidth=2.5)
    ax.add_patch(box)
    ax.text(x+w/2, y+h-0.3, label, ha='center', va='top', fontsize=fontsize,
            color=color, fontweight='bold')

# Center label
ax.text(8, 8.5, "ECU Simulator — Dual Platform Architecture", ha='center', va='center',
        fontsize=16, fontweight='bold', color='#2c3e50')

# Left: macOS Host
outline(ax, 0.3, 0.5, 6.5, 7.5, '#2980b9', "macOS Host Simulator")
fbox(ax, 0.7, 5.8, 2.5, 0.8, '#2980b9', "sensor pthread\n(POSIX timer)")
fbox(ax, 0.7, 4.7, 2.5, 0.8, '#27ae60', "processor pthread")
fbox(ax, 0.7, 3.6, 2.5, 0.8, '#8e44ad', "logger pthread")
fbox(ax, 0.7, 2.5, 2.5, 0.8, '#e74c3c', "watchdog pthread")
fbox(ax, 3.5, 5.3, 2.9, 1.3, '#1a5276', "POSIX Queues\n(sensor_q)\n(telemetry_q)", fontsize=10)
fbox(ax, 3.5, 3.6, 2.9, 1.4, '#117a65', "CLI Interface\n(stdin/stdout)\nstatus|tasks|heap", fontsize=10)
fbox(ax, 0.7, 1.2, 5.7, 0.9, '#566573', "POSIX stdio  /  Terminal I/O", fontsize=11)

# Right: STM32/QEMU
outline(ax, 9.2, 0.5, 6.5, 7.5, '#c0392b', "STM32VL / QEMU Firmware")
colors_fw = ['#e74c3c','#2980b9','#8e44ad','#27ae60','#d35400']
tasks = ["SensorTask (p3)\n100ms kick", "ProcessorTask (p2)\nfixed-pt math", "LoggerTask (p1)\nsemihosting", "WatchdogTask (p2)\nevent group", "DiagnosticsTask (p1)\nUART/console"]
for i, (t, c) in enumerate(zip(tasks, colors_fw)):
    fbox(ax, 9.6, 5.8 - i*1.1, 2.8, 0.85, c, t, fontsize=10)
fbox(ax, 12.7, 4.5, 2.6, 2.1, '#1a5276', "FreeRTOS\nQueues\nxSensorQueue\nxTelemetryQueue", fontsize=10)
fbox(ax, 12.7, 3.0, 2.6, 1.2, '#117a65', "Event Group\nxHeartbeatEvents", fontsize=10)
fbox(ax, 9.6, 1.2, 5.7, 0.9, '#566573', "ARM Semihosting  /  QEMU Console", fontsize=11)

# Center concept arrows
ax.annotate('', xy=(9.1, 5.0), xytext=(6.8, 5.0),
            arrowprops=dict(arrowstyle='<->', color='#7f8c8d', lw=2))
ax.text(7.95, 5.15, "Shared\nConcepts", ha='center', va='bottom', fontsize=11, color='#7f8c8d')

fig.tight_layout()
fig.savefig(f"{OUT}/system_architecture.png", dpi=150)
plt.close(fig)
print("system_architecture.png done")

# ---- task_priority_chart.png ----
fig, ax = plt.subplots(figsize=(10, 6))
tasks_data = [
    ("timer_svc",      4, "FreeRTOS System", '#e74c3c',  192),
    ("SensorTask",     3, "High Priority",   '#e67e22',  192),
    ("ProcessorTask",  2, "Med Priority",    '#2980b9',  192),
    ("WatchdogTask",   2, "Med Priority",    '#2980b9',  192),
    ("LoggerTask",     1, "Low Priority",    '#27ae60',  192),
    ("DiagnosticsTask",1, "Low Priority",    '#27ae60',  192),
    ("idle",           0, "Idle",            '#95a5a6',  128),
]
tasks_data.sort(key=lambda x: x[1])
names = [t[0] for t in tasks_data]
prios = [t[1] for t in tasks_data]
colors = [t[3] for t in tasks_data]
stacks = [t[4] for t in tasks_data]

y = np.arange(len(names))
bars = ax.barh(y, prios, color=colors, alpha=0.85, height=0.6, edgecolor='white', linewidth=1.5)
for i, (bar, t) in enumerate(zip(bars, tasks_data)):
    ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2,
            f"Stack: {t[4]} words", va='center', fontsize=12)
ax.set_yticks(y)
ax.set_yticklabels(names, fontsize=12)
ax.set_xlabel("FreeRTOS Priority Level", fontsize=13)
ax.set_title("FreeRTOS Task Priority Chart", fontsize=15, fontweight='bold')
ax.set_xlim(0, 6)
ax.axvline(x=0, color='gray', lw=0.5)

legend_patches = [
    mpatches.Patch(color='#e74c3c', label='FreeRTOS System'),
    mpatches.Patch(color='#e67e22', label='High Priority'),
    mpatches.Patch(color='#2980b9', label='Medium Priority'),
    mpatches.Patch(color='#27ae60', label='Low Priority'),
    mpatches.Patch(color='#95a5a6', label='Idle'),
]
ax.legend(handles=legend_patches, loc='lower right', fontsize=12)
fig.tight_layout()
fig.savefig(f"{OUT}/task_priority_chart.png", dpi=150)
plt.close(fig)
print("task_priority_chart.png done")

# ---- ipc_diagram.png ----
fig, ax = plt.subplots(figsize=(13, 8))
ax.set_xlim(0, 13)
ax.set_ylim(0, 8)
ax.axis('off')
ax.set_facecolor('#fafafa')
fig.patch.set_facecolor('#fafafa')
ax.set_title("FreeRTOS IPC — Inter-Task Communication", fontsize=15, fontweight='bold', pad=15)

def task_box(ax, x, y, label, color):
    box = FancyBboxPatch((x-1, y-0.4), 2, 0.8, boxstyle="round,pad=0.1",
                         facecolor=color, edgecolor='white', linewidth=1.5)
    ax.add_patch(box)
    ax.text(x, y, label, ha='center', va='center', fontsize=11, color='white', fontweight='bold')

def queue_box(ax, x, y, label, color='#1a5276'):
    box = FancyBboxPatch((x-1.2, y-0.35), 2.4, 0.7, boxstyle="round,pad=0.1",
                         facecolor=color, edgecolor='#aaa', linewidth=1.5)
    ax.add_patch(box)
    ax.text(x, y, label, ha='center', va='center', fontsize=10, color='white')

def arrow(ax, x1, y1, x2, y2, label, color='#2c3e50', dashed=False):
    style = 'dashed' if dashed else 'solid'
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=1.8,
                                linestyle=style))
    mx, my = (x1+x2)/2, (y1+y2)/2
    ax.text(mx, my+0.15, label, ha='center', va='bottom', fontsize=10, color=color)

# Task boxes
task_box(ax, 2, 7, "SensorTask", '#e67e22')
task_box(ax, 6.5, 7, "ProcessorTask", '#2980b9')
task_box(ax, 11, 7, "LoggerTask", '#8e44ad')
task_box(ax, 6.5, 2, "WatchdogTask", '#e74c3c')
task_box(ax, 2, 4.5, "TimerISR\n(100ms)", '#566573')
task_box(ax, 11, 4.5, "DiagnosticsTask", '#27ae60')

# Queues
queue_box(ax, 4.25, 5.5, "xSensorQueue")
queue_box(ax, 8.75, 5.5, "xTelemetryQueue")

# Event group
box = FancyBboxPatch((5, 3.3), 3, 0.8, boxstyle="round,pad=0.1",
                     facecolor='#117a65', edgecolor='white', linewidth=1.5)
ax.add_patch(box)
ax.text(6.5, 3.7, "xHeartbeatEvents\n(EVT_S | EVT_P | EVT_L)", ha='center', va='center', fontsize=10, color='white')

# Mutex
box2 = FancyBboxPatch((9.5, 3.3), 3, 0.8, boxstyle="round,pad=0.1",
                      facecolor='#7d3c98', edgecolor='white', linewidth=1.5)
ax.add_patch(box2)
ax.text(11, 3.7, "xConsoleMutex", ha='center', va='center', fontsize=11, color='white')

# xSensorKickSem
box3 = FancyBboxPatch((0.5, 5.3), 2.3, 0.6, boxstyle="round,pad=0.1",
                      facecolor='#1f618d', edgecolor='white', linewidth=1.5)
ax.add_patch(box3)
ax.text(1.65, 5.6, "xSensorKickSem", ha='center', va='center', fontsize=10, color='white')

# Arrows
arrow(ax, 2, 6.6, 3.05, 5.85, "SensorSample\n(fixed-pt)")
arrow(ax, 5.45, 5.5, 6.5, 6.6, "read sample")
arrow(ax, 6.5, 6.6, 7.55, 5.85, "TelemetryFrame\n(fixed-pt)")
arrow(ax, 9.95, 5.5, 11, 6.6, "read frame")
arrow(ax, 2, 4.1, 2, 3.0, "", color='#566573', dashed=True)
ax.text(1.7, 3.6, "100ms\nkick", ha='right', va='center', fontsize=10, color='#566573')
arrow(ax, 1.65, 5.3, 1.65, 4.9, "", color='#1f618d', dashed=True)
arrow(ax, 2, 4.1, 5.5, 3.9, "EVT_SENSOR")
arrow(ax, 6.5, 6.6, 6.5, 4.1, "EVT_PROCESSOR", color='#2980b9')
arrow(ax, 11, 6.6, 7.5, 4.0, "EVT_LOGGER", color='#8e44ad')
arrow(ax, 11, 4.1, 11, 4.1, "", color='#27ae60')
ax.annotate('', xy=(10, 3.7), xytext=(11, 4.1),
            arrowprops=dict(arrowstyle='->', color='#27ae60', lw=1.8))
ax.text(10.6, 4.0, "protects\nUART", ha='left', fontsize=10, color='#27ae60')

fig.tight_layout()
fig.savefig(f"{OUT}/ipc_diagram.png", dpi=150)
plt.close(fig)
print("ipc_diagram.png done")

# ---- memory_map.png ----
fig, axes = plt.subplots(1, 2, figsize=(12, 6))
fig.suptitle("STM32F100RB Memory Map", fontsize=15, fontweight='bold')

# Flash (128 KB)
ax = axes[0]
total_flash = 128
used_flash = 20.8
free_flash = total_flash - used_flash
ax.barh(['Flash'], [used_flash], color='#e74c3c', label='.text used (20.8 KB)')
ax.barh(['Flash'], [free_flash], left=[used_flash], color='#bdc3c7', label='Free (107.2 KB)')
ax.set_xlabel("Size (KB)")
ax.set_title("Flash Memory (128 KB total)")
ax.set_xlim(0, total_flash * 1.1)
ax.legend(loc='upper right', fontsize=11)
ax.text(used_flash/2, 0, '20.8 KB\n.text', ha='center', va='center', fontsize=11, color='white', fontweight='bold')
ax.text(used_flash + free_flash/2, 0, f'{free_flash:.1f} KB free', ha='center', va='center', fontsize=11, color='#555')

# RAM (8 KB)
ax = axes[1]
total_ram = 8
bss_total = 7.0
items = [
    ("5x TaskSlot", 2.5, '#e74c3c'),
    ("AppObjects", 2.0, '#e67e22'),
    ("AppStats", 1.5, '#2980b9'),
    ("Other .bss", 1.0, '#8e44ad'),
]
free_ram = total_ram - bss_total
left = 0
for label, size, color in items:
    ax.barh(['RAM'], [size], left=[left], color=color, label=f'{label} ({size:.1f} KB)')
    ax.text(left + size/2, 0, f'{size:.1f}', ha='center', va='center', fontsize=11, color='white', fontweight='bold')
    left += size
ax.barh(['RAM'], [free_ram], left=[left], color='#bdc3c7', label=f'Free ({free_ram:.1f} KB)')
ax.text(left + free_ram/2, 0, f'{free_ram:.1f} KB', ha='center', va='center', fontsize=11, color='#555')
ax.set_xlabel("Size (KB)")
ax.set_title("SRAM (8 KB total)")
ax.set_xlim(0, total_ram * 1.1)
ax.legend(loc='upper right', fontsize=11)

fig.tight_layout()
fig.savefig(f"{OUT}/memory_map.png", dpi=150)
plt.close(fig)
print("memory_map.png done")

print("\nAll diagrams generated successfully.")
