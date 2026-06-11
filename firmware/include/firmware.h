#ifndef FIRMWARE_H
#define FIRMWARE_H

#include "FreeRTOS.h"
#include "event_groups.h"
#include "queue.h"
#include "semphr.h"
#include "task.h"
#include "timers.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef enum
{
    FAULT_NONE = 0,
    FAULT_OVERFLOW,
    FAULT_SENSOR,
    FAULT_STALL
} FaultMode;

typedef struct
{
    uint32_t sequence;
    int16_t temperature_c_x10;
    int16_t accel_x_x100;
    int16_t accel_y_x100;
    int16_t accel_z_x100;
    bool valid;
    TickType_t tick;
} SensorSample;

typedef struct
{
    uint32_t sequence;
    int16_t temperature_c_x10;
    int16_t accel_x_x100;
    int16_t accel_y_x100;
    int16_t accel_z_x100;
    uint16_t rpm;
    uint16_t throttle_pct_x10;
    uint16_t speed_kmh_x10;
    bool valid;
    TickType_t tick;
} TelemetryFrame;

typedef struct
{
    uint32_t sensor_samples;
    uint32_t telemetry_frames;
    uint32_t sensor_drops;
    uint32_t telemetry_drops;
    uint32_t sensor_faults;
    uint32_t watchdog_warnings;
    uint32_t task_sensor_beats;
    uint32_t task_processor_beats;
    uint32_t task_logger_beats;
    FaultMode fault_mode;
    SensorSample last_sample;
    TelemetryFrame last_frame;
} AppStats;

void console_init( void );
void console_writef( const char * fmt, ... );
void console_writeln( const char * text );
bool console_readline( char * buffer, size_t buffer_size );

#endif
