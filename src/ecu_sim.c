#define _POSIX_C_SOURCE 200809L

#include "ecu_sim.h"

#include <math.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef enum {
    TASK_SENSOR    = 0,
    TASK_PROCESSOR = 1,
    TASK_LOGGER    = 2,
    TASK_WATCHDOG  = 3,
    TASK_COUNT     = 4
} TaskId;

struct EcuSim {
    pthread_t      threads[TASK_COUNT];
    atomic_bool    stop_requested;
    atomic_bool    running;
    pthread_mutex_t state_mutex;
    pthread_mutex_t log_mutex;
    pthread_mutex_t beat_mutex;
    struct timespec last_beat[TASK_COUNT];
    bool            beat_initialized[TASK_COUNT];
    MsgQueue       *sensor_queue;
    MsgQueue       *telemetry_queue;
    EcuSnapshot     snapshot;
    FaultMode       fault_mode;
    uint64_t        sensor_sequence;
    double          speed_kmh;
    bool            started;
};

/* ------------------------------------------------------------------ helpers */

static long prvDiffMs(const struct timespec *a, const struct timespec *b)
{
    long sec  = (long)(a->tv_sec  - b->tv_sec);
    long nsec = (long)(a->tv_nsec - b->tv_nsec);
    return sec * 1000L + nsec / 1000000L;
}

static struct timespec prvNowTs(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return ts;
}

static void prvSleepMs(int ms)
{
    struct timespec req;
    req.tv_sec  = ms / 1000;
    req.tv_nsec = (long)(ms % 1000) * 1000000L;
    nanosleep(&req, NULL);
}

static void prvLog(EcuSim *sim, const char *fmt, ...)
{
    va_list ap;
    pthread_mutex_lock(&sim->log_mutex);
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
    printf("\n");
    fflush(stdout);
    pthread_mutex_unlock(&sim->log_mutex);
}

/* ------------------------------------------------------------------ beats */

static void prvBeat(EcuSim *sim, TaskId task)
{
    struct timespec ts = prvNowTs();
    pthread_mutex_lock(&sim->beat_mutex);
    sim->last_beat[task]         = ts;
    sim->beat_initialized[task]  = true;
    switch (task) {
        case TASK_SENSOR:    sim->snapshot.task_sensor_beats++;    break;
        case TASK_PROCESSOR: sim->snapshot.task_processor_beats++; break;
        case TASK_LOGGER:    sim->snapshot.task_logger_beats++;    break;
        case TASK_WATCHDOG:  sim->snapshot.task_watchdog_beats++;  break;
        default: break;
    }
    pthread_mutex_unlock(&sim->beat_mutex);
}

static void prvClearBeats(EcuSim *sim)
{
    pthread_mutex_lock(&sim->beat_mutex);
    memset(sim->beat_initialized, 0, sizeof(sim->beat_initialized));
    memset(sim->last_beat,        0, sizeof(sim->last_beat));
    pthread_mutex_unlock(&sim->beat_mutex);
}

/* ------------------------------------------------------------------ sample generation */

static SensorSample prvMakeSensorSample(EcuSim *sim, uint64_t seq)
{
    double phase = (double)seq / 6.0;
    SensorSample s = {
        .sequence      = seq,
        .temperature_c = 72.0 + 8.0  * sin(phase),
        .accel_x       =  0.3 + 0.2  * sin(phase * 1.3),
        .accel_y       = -0.1 + 0.15 * sin(phase * 0.9),
        .accel_z       =  9.8 + 0.2  * sin(phase * 1.7),
        .speed_kmh     = 60.0 + 20.0 * sin(phase * 0.5),
        .fault_code    = 0,
        .timestamp     = prvNowTs()
    };

    FaultMode mode = ecu_get_fault(sim);
    if (mode == FAULT_SENSOR_FAILURE) {
        s.temperature_c = 155.0;
        s.accel_x       = 4.2;
        s.accel_y       = 4.2;
        s.accel_z       = 4.2;
        s.fault_code    = 1;
    }

    return s;
}

static TelemetryFrame prvProcessSample(const SensorSample *s)
{
    double accel_mag = sqrt(s->accel_x * s->accel_x +
                            s->accel_y * s->accel_y +
                            s->accel_z * s->accel_z);

    TelemetryFrame f = {
        .sequence     = s->sequence,
        .temperature_c = s->temperature_c,
        .accel_x      = s->accel_x,
        .accel_y      = s->accel_y,
        .accel_z      = s->accel_z,
        .speed_kmh    = s->speed_kmh,
        .rpm          = 700.0 + s->temperature_c * 17.5 + accel_mag * 125.0,
        .throttle_pct = fmax(0.0, fmin(100.0,
                            12.0 + accel_mag * 14.0 + s->temperature_c / 6.0)),
        .fault_code   = s->fault_code,
        .timestamp    = prvNowTs()
    };
    return f;
}

/* ------------------------------------------------------------------ snapshot helpers */

static void prvUpdateFromSample(EcuSim *sim, const SensorSample *s)
{
    pthread_mutex_lock(&sim->state_mutex);
    sim->snapshot.sensor_samples++;
    sim->snapshot.last_temperature_c = s->temperature_c;
    sim->snapshot.last_accel_x       = s->accel_x;
    sim->snapshot.last_accel_y       = s->accel_y;
    sim->snapshot.last_accel_z       = s->accel_z;
    sim->snapshot.last_speed_kmh     = s->speed_kmh;
    sim->snapshot.sensor_queue_depth =
        queue_count(sim->sensor_queue);
    sim->snapshot.telemetry_queue_depth =
        queue_count(sim->telemetry_queue);
    pthread_mutex_unlock(&sim->state_mutex);
}

static void prvUpdateFromFrame(EcuSim *sim, const TelemetryFrame *f)
{
    pthread_mutex_lock(&sim->state_mutex);
    sim->snapshot.telemetry_frames++;
    sim->snapshot.last_temperature_c    = f->temperature_c;
    sim->snapshot.last_accel_x          = f->accel_x;
    sim->snapshot.last_accel_y          = f->accel_y;
    sim->snapshot.last_accel_z          = f->accel_z;
    sim->snapshot.last_speed_kmh        = f->speed_kmh;
    sim->snapshot.last_rpm              = f->rpm;
    sim->snapshot.last_throttle_pct     = f->throttle_pct;
    sim->snapshot.sensor_queue_depth    = queue_count(sim->sensor_queue);
    sim->snapshot.telemetry_queue_depth = queue_count(sim->telemetry_queue);
    pthread_mutex_unlock(&sim->state_mutex);
}

static void prvIncrementDrop(EcuSim *sim, bool sensor_q)
{
    pthread_mutex_lock(&sim->state_mutex);
    if (sensor_q) sim->snapshot.sensor_drops++;
    else          sim->snapshot.telemetry_drops++;
    pthread_mutex_unlock(&sim->state_mutex);
}

/* ------------------------------------------------------------------ threads */

static void *prvSensorThread(void *arg)
{
    EcuSim *sim = arg;
    prvBeat(sim, TASK_SENSOR);

    while (!atomic_load(&sim->stop_requested)) {
        FaultMode mode = ecu_get_fault(sim);

        if (mode == FAULT_QUEUE_OVERFLOW) {
            for (int i = 0; i < 4 && !atomic_load(&sim->stop_requested); i++) {
                SensorSample s = prvMakeSensorSample(sim, ++sim->sensor_sequence);
                if (!queue_push(sim->sensor_queue, &s))
                    prvIncrementDrop(sim, true);
                else
                    prvUpdateFromSample(sim, &s);
            }
            prvBeat(sim, TASK_SENSOR);
            prvSleepMs(25);
            continue;
        }

        if (mode == FAULT_SENSOR_FAILURE && (sim->sensor_sequence % 10) == 0) {
            prvLog(sim, "[sensor] injected invalid reading");
        }

        SensorSample s = prvMakeSensorSample(sim, ++sim->sensor_sequence);
        if (!queue_push(sim->sensor_queue, &s))
            prvIncrementDrop(sim, true);
        else
            prvUpdateFromSample(sim, &s);

        prvBeat(sim, TASK_SENSOR);
        prvSleepMs(mode == FAULT_PROCESS_STALL ? 90 : 180);
    }
    return NULL;
}

static void *prvProcessorThread(void *arg)
{
    EcuSim *sim = arg;
    prvBeat(sim, TASK_PROCESSOR);

    while (!atomic_load(&sim->stop_requested)) {
        SensorSample s;
        if (!queue_pop(sim->sensor_queue, &s, 250)) {
            prvBeat(sim, TASK_PROCESSOR);
            continue;
        }

        if (ecu_get_fault(sim) == FAULT_PROCESS_STALL && (s.sequence % 8 == 0)) {
            prvLog(sim, "[processor] deliberate stall on sample %llu",
                    (unsigned long long)s.sequence);
            prvSleepMs(750);
        }

        TelemetryFrame f = prvProcessSample(&s);
        if (!queue_push(sim->telemetry_queue, &f))
            prvIncrementDrop(sim, false);
        else
            prvUpdateFromFrame(sim, &f);

        prvBeat(sim, TASK_PROCESSOR);
    }
    return NULL;
}

static void *prvLoggerThread(void *arg)
{
    EcuSim *sim = arg;
    prvBeat(sim, TASK_LOGGER);

    while (!atomic_load(&sim->stop_requested)) {
        TelemetryFrame f;
        if (!queue_pop(sim->telemetry_queue, &f, 300)) {
            prvBeat(sim, TASK_LOGGER);
            continue;
        }

        pthread_mutex_lock(&sim->log_mutex);
        printf("[telemetry] seq=%llu temp=%.1fC ax=%.2fg ay=%.2fg az=%.2fg "
               "spd=%.1fkm/h rpm=%.0f throttle=%.1f%% fault=%d\n",
               (unsigned long long)f.sequence,
               f.temperature_c,
               f.accel_x, f.accel_y, f.accel_z,
               f.speed_kmh,
               f.rpm,
               f.throttle_pct,
               f.fault_code);
        fflush(stdout);
        pthread_mutex_unlock(&sim->log_mutex);

        prvBeat(sim, TASK_LOGGER);
    }
    return NULL;
}

static void prvWarnIfOverdue(EcuSim *sim, TaskId task, const char *name, long deadline_ms)
{
    pthread_mutex_lock(&sim->beat_mutex);
    if (!sim->beat_initialized[task]) {
        pthread_mutex_unlock(&sim->beat_mutex);
        return;
    }
    struct timespec last = sim->last_beat[task];
    pthread_mutex_unlock(&sim->beat_mutex);

    struct timespec now = prvNowTs();
    long age = prvDiffMs(&now, &last);
    if (age > deadline_ms) {
        pthread_mutex_lock(&sim->state_mutex);
        sim->snapshot.watchdog_warnings++;
        pthread_mutex_unlock(&sim->state_mutex);
        prvLog(sim, "[watchdog] %s heartbeat overdue by %ldms", name, age - deadline_ms);
    }
}

static void *prvWatchdogThread(void *arg)
{
    EcuSim *sim = arg;
    prvBeat(sim, TASK_WATCHDOG);

    while (!atomic_load(&sim->stop_requested)) {
        prvWarnIfOverdue(sim, TASK_SENSOR,    "sensor",    900);
        prvWarnIfOverdue(sim, TASK_PROCESSOR, "processor", 900);
        prvWarnIfOverdue(sim, TASK_LOGGER,    "logger",   1200);
        prvBeat(sim, TASK_WATCHDOG);
        prvSleepMs(500);
    }
    return NULL;
}

/* ------------------------------------------------------------------ public API */

static void prvInitSnapshot(EcuSim *sim)
{
    memset(&sim->snapshot, 0, sizeof(sim->snapshot));
    sim->snapshot.fault_mode            = sim->fault_mode;
    sim->snapshot.sensor_queue_depth    = queue_count(sim->sensor_queue);
    sim->snapshot.telemetry_queue_depth = queue_count(sim->telemetry_queue);
}

EcuSim *ecu_create(void)
{
    EcuSim *sim = calloc(1, sizeof(*sim));
    if (!sim)
        return NULL;

    if (pthread_mutex_init(&sim->state_mutex, NULL) != 0 ||
        pthread_mutex_init(&sim->log_mutex,   NULL) != 0 ||
        pthread_mutex_init(&sim->beat_mutex,  NULL) != 0) {
        ecu_destroy(sim);
        return NULL;
    }

    sim->sensor_queue    = queue_create("sensor",    sizeof(SensorSample),   24);
    sim->telemetry_queue = queue_create("telemetry", sizeof(TelemetryFrame), 24);
    if (!sim->sensor_queue || !sim->telemetry_queue) {
        ecu_destroy(sim);
        return NULL;
    }

    sim->fault_mode = FAULT_NONE;
    prvInitSnapshot(sim);
    return sim;
}

void ecu_destroy(EcuSim *sim)
{
    if (!sim)
        return;
    ecu_stop(sim);
    queue_destroy(sim->sensor_queue);
    queue_destroy(sim->telemetry_queue);
    pthread_mutex_destroy(&sim->state_mutex);
    pthread_mutex_destroy(&sim->log_mutex);
    pthread_mutex_destroy(&sim->beat_mutex);
    free(sim);
}

void ecu_start(EcuSim *sim)
{
    if (!sim || sim->started)
        return;
    atomic_store(&sim->stop_requested, false);
    atomic_store(&sim->running,        true);
    sim->started = true;
    pthread_create(&sim->threads[TASK_SENSOR],    NULL, prvSensorThread,    sim);
    pthread_create(&sim->threads[TASK_PROCESSOR], NULL, prvProcessorThread, sim);
    pthread_create(&sim->threads[TASK_LOGGER],    NULL, prvLoggerThread,    sim);
    pthread_create(&sim->threads[TASK_WATCHDOG],  NULL, prvWatchdogThread,  sim);
}

void ecu_stop(EcuSim *sim)
{
    if (!sim || !sim->started)
        return;
    atomic_store(&sim->stop_requested, true);
    /* unblock queue waiters */
    if (sim->sensor_queue)    queue_clear(sim->sensor_queue);
    if (sim->telemetry_queue) queue_clear(sim->telemetry_queue);
    for (size_t i = 0; i < TASK_COUNT; i++)
        pthread_join(sim->threads[i], NULL);
    sim->started = false;
    atomic_store(&sim->running, false);
}

void ecu_reset(EcuSim *sim)
{
    if (!sim)
        return;
    pthread_mutex_lock(&sim->state_mutex);
    prvInitSnapshot(sim);
    sim->sensor_sequence = 0;
    sim->speed_kmh       = 0.0;
    pthread_mutex_unlock(&sim->state_mutex);
    queue_clear(sim->sensor_queue);
    queue_clear(sim->telemetry_queue);
    prvClearBeats(sim);
}

void ecu_set_fault(EcuSim *sim, FaultMode mode)
{
    if (!sim)
        return;
    pthread_mutex_lock(&sim->state_mutex);
    sim->fault_mode          = mode;
    sim->snapshot.fault_mode = mode;
    pthread_mutex_unlock(&sim->state_mutex);
}

FaultMode ecu_get_fault(EcuSim *sim)
{
    if (!sim)
        return FAULT_NONE;
    pthread_mutex_lock(&sim->state_mutex);
    FaultMode mode = sim->fault_mode;
    pthread_mutex_unlock(&sim->state_mutex);
    return mode;
}

void ecu_snapshot(EcuSim *sim, EcuSnapshot *out)
{
    if (!sim || !out)
        return;
    pthread_mutex_lock(&sim->state_mutex);
    *out = sim->snapshot;
    out->sensor_queue_depth    = queue_count(sim->sensor_queue);
    out->telemetry_queue_depth = queue_count(sim->telemetry_queue);
    pthread_mutex_unlock(&sim->state_mutex);
}

bool ecu_is_running(EcuSim *sim)
{
    return sim ? atomic_load(&sim->running) : false;
}

const char *fault_mode_name(FaultMode mode)
{
    switch (mode) {
        case FAULT_QUEUE_OVERFLOW: return "queue-overflow";
        case FAULT_SENSOR_FAILURE: return "sensor-failure";
        case FAULT_PROCESS_STALL:  return "process-stall";
        default:                   return "none";
    }
}
