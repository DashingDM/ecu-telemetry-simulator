# ECU Telemetry Simulator

A real-time vehicle telemetry ECU simulator built as a graduate embedded systems project. The system runs on two platforms: an STM32F100RB microcontroller emulated in QEMU (`stm32vldiscovery`) running FreeRTOS, and a native macOS POSIX host simulator using pthreads. Both platforms implement identical sensor pipelines, fault injection, and telemetry logging.

## Architecture

The system is structured around five concurrent tasks:

| Task | Priority | Role |
|---|---|---|
| Sensor | 3 | Reads RPM, throttle, temperature, acceleration (fixed-point) |
| Processor | 2 | Validates frames, applies fault logic |
| Telemetry | 2 | Logs outbound telemetry frames |
| Watchdog | 1 | Monitors task heartbeats via event group |
| Diagnostics | 1 | CLI console — status, fault injection, reset |

Inter-task communication uses FreeRTOS static queues on firmware and a custom POSIX ring-buffer with condition variables on the host.

## Features

- **Static allocation only** — no heap usage at runtime (`configSUPPORT_DYNAMIC_ALLOCATION 0`)
- **Software timer** — periodic sensor sampling via `xTimerCreate`
- **Event group watchdog** — detects task stalls within a configurable window
- **Fault injection** — sensor dropout, stack overflow simulation, task stall
- **Fixed-point arithmetic** — temperature × 10, acceleration × 100, no floating point
- **ARM semihosting** — firmware I/O over QEMU debug interface

## Build

**Host simulator (macOS):**
```bash
mkdir build_host && cd build_host
cmake .. && make
./ecu_sim
```

**Firmware (QEMU):**
```bash
./run_qemu.sh
```
Requires `arm-none-eabi-gcc` and `qemu-system-arm` with `stm32vldiscovery` support.

## CLI Commands

```
status         — current sensor readings and fault mode
tasks          — per-task stack watermark
heap           — static memory footprint
stats          — telemetry frame counters
fault sensor   — inject sensor dropout
fault overflow — inject stack overflow
fault stall    — inject task stall
fault none     — clear fault
reset          — reset statistics
help           — list commands
```

## Memory Footprint (STM32F100RB)

| Region | Size |
|---|---|
| Flash (text) | 20,912 bytes / 128 KB |
| RAM (bss) | 7,016 bytes / 8 KB |

## Report

Full technical write-up including design decisions, IPC analysis, test results, and captured telemetry: [REPORT.md](REPORT.md)
