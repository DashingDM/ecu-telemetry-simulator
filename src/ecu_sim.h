#ifndef ECU_SIM_H
#define ECU_SIM_H

#define _POSIX_C_SOURCE 200809L

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <time.h>

/* Fault modes */
typedef enum {
    FAULT_NONE = 0,
    FAULT_QUEUE_OVERFLOW,
    FAULT_SENSOR_FAILURE,
    FAULT_PROCESS_STALL
} FaultMode;

/* Telemetry structures with 3-axis accel + rpm/throttle */
typedef struct {
    uint64_t sequence;
    double temperature_c;
    double accel_x;
    double accel_y;
    double accel_z;
    double speed_kmh;
    int fault_code;
    struct timespec timestamp;
} SensorSample;

typedef struct {
    uint64_t sequence;
    double temperature_c;
    double accel_x;
    double accel_y;
    double accel_z;
    double speed_kmh;
    double rpm;
    double throttle_pct;
    int fault_code;
    struct timespec timestamp;
} TelemetryFrame;

typedef struct {
    uint64_t sensor_samples;
    uint64_t telemetry_frames;
    uint64_t sensor_drops;
    uint64_t telemetry_drops;
    uint64_t watchdog_warnings;
    uint64_t task_sensor_beats;
    uint64_t task_processor_beats;
    uint64_t task_logger_beats;
    uint64_t task_watchdog_beats;
    size_t sensor_queue_depth;
    size_t telemetry_queue_depth;
    double last_temperature_c;
    double last_accel_x;
    double last_accel_y;
    double last_accel_z;
    double last_speed_kmh;
    double last_rpm;
    double last_throttle_pct;
    FaultMode fault_mode;
} EcuSnapshot;

/* Opaque types */
typedef struct MsgQueue MsgQueue;
typedef struct EcuSim EcuSim;

/* Queue API */
MsgQueue *queue_create(const char *name, size_t item_size, size_t capacity);
void      queue_destroy(MsgQueue *queue);
bool      queue_push(MsgQueue *queue, const void *item);
bool      queue_pop(MsgQueue *queue, void *item, int timeout_ms);
size_t    queue_count(const MsgQueue *queue);
size_t    queue_capacity(const MsgQueue *queue);
const char *queue_name(const MsgQueue *queue);
void      queue_clear(MsgQueue *queue);

/* ECU simulator API */
EcuSim   *ecu_create(void);
void      ecu_destroy(EcuSim *sim);
void      ecu_start(EcuSim *sim);
void      ecu_stop(EcuSim *sim);
void      ecu_reset(EcuSim *sim);
void      ecu_set_fault(EcuSim *sim, FaultMode mode);
FaultMode ecu_get_fault(EcuSim *sim);
void      ecu_snapshot(EcuSim *sim, EcuSnapshot *out);
bool      ecu_is_running(EcuSim *sim);
const char *fault_mode_name(FaultMode mode);

#endif /* ECU_SIM_H */
