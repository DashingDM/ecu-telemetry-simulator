#ifndef IPC_H
#define IPC_H

#include "FreeRTOS.h"
#include "queue.h"
#include "semphr.h"
#include "event_groups.h"
#include <stdint.h>
#include <stdbool.h>

/* ---- Event bits for system event group ---- */
#define EVT_SENSOR_READY    ( 1 << 0 )
#define EVT_FAULT_DETECTED  ( 1 << 1 )
#define EVT_WATCHDOG_RESET  ( 1 << 2 )

/* ---- Watchdog heartbeat event bits ---- */
#define EVT_SENSOR      ( 1 << 0 )
#define EVT_PROCESSOR   ( 1 << 1 )
#define EVT_TELEMETRY   ( 1 << 2 )

/* ---- Fixed-point data structures ---- */
/* temperature_c_x10: e.g. 720 = 72.0 C
 * accel_x/y/z_x100: e.g. 980 = 9.80 m/s^2 */
typedef struct {
    int16_t  temperature_c_x10;
    int16_t  accel_x_x100;
    int16_t  accel_y_x100;
    int16_t  accel_z_x100;
    uint32_t timestamp_ms;
} SensorData_t;

typedef struct {
    SensorData_t sensor;
    uint16_t speed_kmh_x10;  /* e.g. 1234 = 123.4 km/h */
    uint16_t rpm;
    uint16_t throttle_pct_x10; /* e.g. 450 = 45.0 % */
    uint8_t  fault_code;
    bool     valid;
    uint32_t timestamp_ms;
} TelemetryData_t;

/* ---- IPC handles ---- */
extern QueueHandle_t       xSensorQueue;
extern QueueHandle_t       xTelemetryQueue;
extern SemaphoreHandle_t   xUartMutex;
extern SemaphoreHandle_t   xDataReadySem;
extern SemaphoreHandle_t   xSensorKickSem;   /* timer -> sensor_task */
extern EventGroupHandle_t  xSystemEventGroup;
extern EventGroupHandle_t  xHeartbeatEvents; /* watchdog event group */

void ipc_init(void);

#endif /* IPC_H */
