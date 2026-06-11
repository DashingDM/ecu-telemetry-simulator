#!/usr/bin/env python3
"""Generate flowchart diagrams."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

OUT = "/Users/dashing_dm/Documents/Firmware/report_assets/flowcharts"

import matplotlib
plt.rcParams.update({
    'font.size': 12,
    'axes.titlesize': 14,
})

def draw_box(ax, x, y, w, h, label, color='#2980b9', fontsize=11, shape='rect'):
    if shape == 'diamond':
        # Draw diamond
        cx, cy = x, y
        hw, hh = w/2, h/2
        diamond = plt.Polygon([[cx, cy+hh], [cx+hw, cy], [cx, cy-hh], [cx-hw, cy]],
                               closed=True, facecolor=color, edgecolor='white', linewidth=1.5)
        ax.add_patch(diamond)
        ax.text(x, y, label, ha='center', va='center', fontsize=fontsize, color='white', fontweight='bold')
    elif shape == 'round':
        box = FancyBboxPatch((x-w/2, y-h/2), w, h, boxstyle="round,pad=0.1",
                             facecolor=color, edgecolor='white', linewidth=1.5)
        ax.add_patch(box)
        ax.text(x, y, label, ha='center', va='center', fontsize=fontsize, color='white', fontweight='bold')
    else:
        box = FancyBboxPatch((x-w/2, y-h/2), w, h, boxstyle="square,pad=0.05",
                             facecolor=color, edgecolor='white', linewidth=1.5)
        ax.add_patch(box)
        ax.text(x, y, label, ha='center', va='center', fontsize=fontsize, color='white', fontweight='bold')

def arrow_down(ax, x, y_start, y_end, label='', color='#555'):
    ax.annotate('', xy=(x, y_end), xytext=(x, y_start),
                arrowprops=dict(arrowstyle='->', color=color, lw=1.5))
    if label:
        ax.text(x+0.15, (y_start+y_end)/2, label, fontsize=11, color=color, va='center')

def arrow_to(ax, x1, y1, x2, y2, label='', color='#555', dashed=False):
    ls = 'dashed' if dashed else 'solid'
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=1.5, linestyle=ls))
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx+0.1, my+0.1, label, fontsize=11, color=color)

# ---- main_flow.png ----
fig, ax = plt.subplots(figsize=(6, 12))
ax.set_xlim(0, 6)
ax.set_ylim(0, 12)
ax.axis('off')
ax.set_title("main() Startup Flow", fontsize=14, fontweight='bold')

steps = [
    (3, 11, 2.5, 0.6, "console_init()\nUART / semihosting ready", '#27ae60', 'rect'),
    (3, 9.8, 2.5, 0.6, "Create IPC Objects\nQueues, Semaphore,\nEvent Group, Mutex", '#2980b9', 'rect'),
    (3, 8.5, 2.5, 0.6, "Create 5 FreeRTOS Tasks\nSensor|Processor|Logger\nWatchdog|Diagnostics", '#8e44ad', 'rect'),
    (3, 7.3, 2.5, 0.6, "xTimerCreate()\nxTimerStart()\n100ms sensor kick", '#e67e22', 'rect'),
    (3, 6.1, 2.5, 0.6, "vTaskStartScheduler()", '#e74c3c', 'rect'),
    (3, 4.9, 2.5, 0.6, "[Scheduler Running]\nAll tasks active\nRTOS takes control", '#117a65', 'round'),
    (3, 3.5, 2.5, 0.8, "[Runs Forever]\nTasks execute on\nFreeRTOS scheduler", '#1a5276', 'round'),
]

for x, y, w, h, label, color, shape in steps:
    draw_box(ax, x, y, w, h, label, color=color, shape=shape)

for i in range(len(steps)-1):
    y_start = steps[i][1] - steps[i][3]/2
    y_end = steps[i+1][1] + steps[i+1][3]/2
    arrow_down(ax, 3, y_start, y_end)

# Loop arrow
ax.annotate('', xy=(3, 3.1), xytext=(3, 2.5),
            arrowprops=dict(arrowstyle='->', color='#1a5276', lw=1.5))
ax.annotate('', xy=(4.6, 3.5), xytext=(3, 2.5),
            arrowprops=dict(arrowstyle='->', color='#1a5276', lw=1.5, linestyle='dashed'))
ax.text(5.0, 3.5, "∞ loop", fontsize=12, color='#1a5276', va='center')

fig.tight_layout()
fig.savefig(f"{OUT}/main_flow.png", dpi=150)
plt.close(fig)
print("main_flow.png done")

# ---- sensor_task_flow.png ----
fig, ax = plt.subplots(figsize=(8, 13))
ax.set_xlim(0, 8)
ax.set_ylim(0, 13)
ax.axis('off')
ax.set_title("SensorTask Flow", fontsize=14, fontweight='bold')

draw_box(ax, 4, 12.2, 2.5, 0.5, "START", '#27ae60', shape='round')
draw_box(ax, 4, 11.2, 3.2, 0.6, "xSemaphoreTake(\n  xSensorKickSem, MAX_DELAY)", '#2980b9')
draw_box(ax, 4, 10.1, 3.0, 0.5, "xEventGroupSetBits(\n  EVT_SENSOR)", '#8e44ad')
draw_box(ax, 4, 9.0, 2.8, 0.6, "FAULT_OVERFLOW?", '#e74c3c', shape='diamond')
draw_box(ax, 1.5, 7.8, 2.2, 0.6, "Burst 3 samples\nto queue\n(overflow test)", '#e74c3c')
draw_box(ax, 4, 7.5, 2.8, 0.6, "FAULT_SENSOR?", '#e67e22', shape='diamond')
draw_box(ax, 6.5, 6.3, 2.2, 0.6, "temp = 1550\n(99.9°C sentinel)\nvalid = false", '#e67e22')
draw_box(ax, 4, 6.0, 2.5, 0.6, "Normal Sample\nread_sensor()", '#27ae60')
draw_box(ax, 4, 4.9, 3.2, 0.6, "xQueueSend(\n  xSensorQueue, sample)", '#1a5276')
draw_box(ax, 4, 3.8, 2.0, 0.5, "Loop back", '#566573', shape='round')

arrow_down(ax, 4, 12.0, 11.5)
arrow_down(ax, 4, 10.9, 10.4)
arrow_down(ax, 4, 9.8, 9.3)
# overflow yes branch
arrow_to(ax, 2.6, 9.0, 1.5, 8.1, "Yes", '#e74c3c')
# overflow no branch
arrow_down(ax, 4, 8.7, 7.8, "No")
arrow_down(ax, 4, 7.2, 6.3)
# sensor yes branch
arrow_to(ax, 5.4, 7.5, 6.5, 6.6, "Yes", '#e67e22')
# sensor no branch
arrow_down(ax, 4, 7.2, 6.3, "No")
arrow_down(ax, 4, 5.7, 5.2)
arrow_down(ax, 4, 4.6, 4.1)
# loop back arrow
ax.annotate('', xy=(0.8, 11.2), xytext=(0.8, 3.8),
            arrowprops=dict(arrowstyle='->', color='#555', lw=1.5))
ax.plot([0.8, 4-1.0], [3.8, 3.8], color='#555', lw=1.5)
ax.plot([0.8, 4-1.6], [11.2, 11.2], color='#555', lw=1.5)
ax.text(0.2, 7.5, "loop", fontsize=11, color='#555', va='center', rotation=90)

fig.tight_layout()
fig.savefig(f"{OUT}/sensor_task_flow.png", dpi=150)
plt.close(fig)
print("sensor_task_flow.png done")

# ---- watchdog_flow.png ----
fig, ax = plt.subplots(figsize=(7, 11))
ax.set_xlim(0, 7)
ax.set_ylim(0, 11)
ax.axis('off')
ax.set_title("WatchdogTask Flow", fontsize=14, fontweight='bold')

draw_box(ax, 3.5, 10.3, 2.0, 0.5, "START", '#27ae60', shape='round')
draw_box(ax, 3.5, 9.3, 3.5, 0.6, "xEventGroupWaitBits(\n  EVT_S|EVT_P|EVT_L\n  wait_all=true, 1000ms)", '#2980b9')
draw_box(ax, 3.5, 8.0, 2.8, 0.6, "All bits set\nbefore timeout?", '#e74c3c', shape='diamond')
draw_box(ax, 1.2, 6.7, 2.5, 0.7, "warnings++\nLog missing bits\n(WARN output)", '#e74c3c')
draw_box(ax, 5.8, 6.7, 2.5, 0.7, "Print healthy:\nsensor/proc/logger\nbeat counts", '#27ae60')
draw_box(ax, 3.5, 5.5, 3.0, 0.6, "xEventGroupClearBits(\n  EVT_S|EVT_P|EVT_L)", '#8e44ad')
draw_box(ax, 3.5, 4.4, 2.0, 0.5, "Loop back", '#566573', shape='round')

arrow_down(ax, 3.5, 10.1, 9.6)
arrow_down(ax, 3.5, 9.0, 8.3)
arrow_to(ax, 2.1, 8.0, 1.2, 7.05, "No", '#e74c3c')
arrow_to(ax, 4.9, 8.0, 5.8, 7.05, "Yes", '#27ae60')
arrow_to(ax, 1.2, 6.35, 3.5-1.5, 5.8, "", '#555')
arrow_to(ax, 5.8, 6.35, 3.5+1.5, 5.8, "", '#555')
arrow_down(ax, 3.5, 5.2, 4.65)
# loop
ax.plot([3.5-1.0, 0.5], [4.4, 4.4], color='#555', lw=1.5)
ax.plot([0.5, 0.5], [4.4, 9.3], color='#555', lw=1.5)
ax.annotate('', xy=(3.5-1.75, 9.3), xytext=(0.5, 9.3),
            arrowprops=dict(arrowstyle='->', color='#555', lw=1.5))
ax.text(0.2, 7, "loop", fontsize=11, color='#555', va='center', rotation=90)

fig.tight_layout()
fig.savefig(f"{OUT}/watchdog_flow.png", dpi=150)
plt.close(fig)
print("watchdog_flow.png done")

# ---- fault_injection_flow.png ----
fig, ax = plt.subplots(figsize=(12, 8))
ax.set_xlim(0, 12)
ax.set_ylim(0, 8)
ax.axis('off')
ax.set_title("Fault Injection Flow — DiagnosticsTask", fontsize=14, fontweight='bold')

# Top
draw_box(ax, 6, 7.3, 3.5, 0.5, "UART receives 'fault X'", '#2980b9', shape='rect')
draw_box(ax, 6, 6.4, 3.5, 0.6, "Parse command\n[none | overflow | sensor | stall]", '#8e44ad', shape='diamond')

# 4 branches
draw_box(ax, 1.5, 4.8, 2.2, 0.8, "fault none\n─────\nClear fault mode\nAll tasks normal", '#27ae60')
draw_box(ax, 4.2, 4.8, 2.2, 0.9, "fault overflow\n─────\nSensor bursts\n3 samples/cycle\n(queue stress)", '#e67e22')
draw_box(ax, 7.0, 4.8, 2.2, 0.9, "fault sensor\n─────\ntemp = 1550\n(99.9°C sentinel)\nvalid = false", '#e74c3c')
draw_box(ax, 10.0, 4.8, 2.2, 0.9, "fault stall\n─────\nvTaskDelay(450ms)\nWatchdog will\nlog warnings", '#c0392b')

arrow_down(ax, 6, 7.1, 6.7)
# 4 branch arrows
for bx, label in [(1.5,"none"),(4.2,"overflow"),(7.0,"sensor"),(10.0,"stall")]:
    arrow_to(ax, 6, 6.1, bx, 5.25, label, '#555')

# Effects
draw_box(ax, 1.5, 3.2, 2.2, 0.6, "System resumes\nnormal operation", '#117a65')
draw_box(ax, 4.2, 3.2, 2.2, 0.6, "Queue drops\nincrement\nProcessor load up", '#e67e22')
draw_box(ax, 7.0, 3.2, 2.2, 0.6, "Logger prints\n'invalid' frames\nto console", '#e74c3c')
draw_box(ax, 10.0, 3.2, 2.2, 0.6, "Watchdog prints\nmissing EVT_SENSOR\nwarnings", '#c0392b')

for bx in [1.5, 4.2, 7.0, 10.0]:
    arrow_down(ax, bx, 4.4, 3.5)

# Bottom note
draw_box(ax, 6, 1.8, 8, 0.8, "xTaskNotify / global fault_mode flag protects all state changes\nAll tasks check fault_mode on each iteration", '#1a5276', fontsize=11)
for bx in [1.5, 4.2, 7.0, 10.0]:
    arrow_to(ax, bx, 2.9, 6, 2.2, "", '#aaa')

fig.tight_layout()
fig.savefig(f"{OUT}/fault_injection_flow.png", dpi=150)
plt.close(fig)
print("fault_injection_flow.png done")

print("\nAll flowcharts generated successfully.")
