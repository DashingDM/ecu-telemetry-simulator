#include "ecu_sim.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void trim_newline(char *s)
{
    if (!s) return;
    size_t len = strlen(s);
    while (len > 0 && (s[len - 1] == '\n' || s[len - 1] == '\r'))
        s[--len] = '\0';
}

static void lowercase(char *s)
{
    for (; s && *s; ++s)
        *s = (char)tolower((unsigned char)*s);
}

static void print_help(void)
{
    puts("Commands:");
    puts("  status           show counters and latest values");
    puts("  tasks            show task heartbeat health");
    puts("  heap             show simulated memory footprint");
    puts("  stats            show queue depths and frame counts");
    puts("  fault none       clear injected faults");
    puts("  fault overflow   stress the sensor queue");
    puts("  fault sensor     inject bad sensor readings");
    puts("  fault process    slow the processing path");
    puts("  reset            clear counters and queues");
    puts("  help             show this help");
    puts("  quit             exit cleanly");
}

static void print_status(EcuSim *sim)
{
    EcuSnapshot snap;
    ecu_snapshot(sim, &snap);
    printf("Fault mode       : %s\n", fault_mode_name(snap.fault_mode));
    printf("Sensor samples   : %llu\n", (unsigned long long)snap.sensor_samples);
    printf("Telemetry frames : %llu\n", (unsigned long long)snap.telemetry_frames);
    printf("Sensor drops     : %llu\n", (unsigned long long)snap.sensor_drops);
    printf("Telemetry drops  : %llu\n", (unsigned long long)snap.telemetry_drops);
    printf("Watchdog warnings: %llu\n", (unsigned long long)snap.watchdog_warnings);
    printf("Latest temp      : %.1f C\n",   snap.last_temperature_c);
    printf("Latest accel     : x=%.2f y=%.2f z=%.2f g\n",
           snap.last_accel_x, snap.last_accel_y, snap.last_accel_z);
    printf("Latest speed     : %.1f km/h\n", snap.last_speed_kmh);
    printf("Latest rpm       : %.0f\n",       snap.last_rpm);
    printf("Latest throttle  : %.1f %%\n",    snap.last_throttle_pct);
}

static void print_tasks(EcuSim *sim)
{
    EcuSnapshot snap;
    ecu_snapshot(sim, &snap);
    printf("sensor beats   : %llu\n", (unsigned long long)snap.task_sensor_beats);
    printf("processor beats: %llu\n", (unsigned long long)snap.task_processor_beats);
    printf("logger beats   : %llu\n", (unsigned long long)snap.task_logger_beats);
    printf("watchdog beats : %llu\n", (unsigned long long)snap.task_watchdog_beats);
    printf("watchdog alerts: %llu\n", (unsigned long long)snap.watchdog_warnings);
}

static void print_heap(EcuSim *sim)
{
    EcuSnapshot snap;
    ecu_snapshot(sim, &snap);
    size_t footprint = sizeof(EcuSnapshot)
                     + 24 * sizeof(SensorSample)
                     + 24 * sizeof(TelemetryFrame);
    printf("Simulated static footprint: about %zu bytes\n", footprint);
    printf("Current queues: sensor=%zu telemetry=%zu\n",
           snap.sensor_queue_depth, snap.telemetry_queue_depth);
    printf("Queue footprint is fixed in this build; no dynamic heap growth.\n");
}

static void print_stats(EcuSim *sim)
{
    EcuSnapshot snap;
    ecu_snapshot(sim, &snap);
    printf("Sensor queue depth   : %zu\n", snap.sensor_queue_depth);
    printf("Telemetry queue depth: %zu\n", snap.telemetry_queue_depth);
    printf("Frames in            : %llu\n", (unsigned long long)snap.sensor_samples);
    printf("Frames out           : %llu\n", (unsigned long long)snap.telemetry_frames);
}

static FaultMode parse_fault(const char *value)
{
    if (strcmp(value, "overflow") == 0) return FAULT_QUEUE_OVERFLOW;
    if (strcmp(value, "sensor")   == 0) return FAULT_SENSOR_FAILURE;
    if (strcmp(value, "process")  == 0) return FAULT_PROCESS_STALL;
    return FAULT_NONE;
}

int main(void)
{
    EcuSim *sim = ecu_create();
    if (!sim) {
        fprintf(stderr, "Failed to create ECU simulator.\n");
        return 1;
    }

    ecu_start(sim);
    puts("Real-Time Vehicle Telemetry ECU Simulator");
    puts("Type 'help' for commands.");

    char line[256];
    while (1) {
        fputs("ecu> ", stdout);
        fflush(stdout);

        if (!fgets(line, sizeof(line), stdin))
            break;

        trim_newline(line);
        lowercase(line);

        if (line[0] == '\0')
            continue;

        if (strcmp(line, "quit") == 0 || strcmp(line, "exit") == 0) {
            break;
        } else if (strcmp(line, "help") == 0) {
            print_help();
        } else if (strcmp(line, "status") == 0) {
            print_status(sim);
        } else if (strcmp(line, "tasks") == 0) {
            print_tasks(sim);
        } else if (strcmp(line, "heap") == 0) {
            print_heap(sim);
        } else if (strcmp(line, "stats") == 0) {
            print_stats(sim);
        } else if (strcmp(line, "reset") == 0) {
            ecu_reset(sim);
            puts("State reset.");
        } else if (strncmp(line, "fault ", 6) == 0) {
            FaultMode mode = parse_fault(line + 6);
            ecu_set_fault(sim, mode);
            printf("Fault mode set to %s.\n", fault_mode_name(mode));
        } else {
            puts("Unknown command. Type 'help' for options.");
        }
    }

    puts("Shutting down...");
    ecu_stop(sim);
    ecu_destroy(sim);
    return 0;
}
