#include "processing_task.h"
#include "ipc.h"
#include "health_monitor_task.h"
#include "fault_injection.h"
#include "FreeRTOS.h"
#include "task.h"
#include "event_groups.h"
#include <stdint.h>

/* Simple integer sqrt using Newton's method */
static uint32_t isqrt32(uint32_t n)
{
    if (n == 0) return 0;
    uint32_t x = n;
    uint32_t y = (x + 1) / 2;
    while (y < x) {
        x = y;
        y = (x + n / x) / 2;
    }
    return x;
}

/* Fixed-point speed accumulator (x10, i.e. tenths of km/h) */
static int32_t speed_kmh_x10 = 0;

void processing_task(void *pvParameters)
{
    (void)pvParameters;

    for (;;) {
        if (xSemaphoreTake(xDataReadySem, portMAX_DELAY) != pdTRUE)
            continue;

        SensorData_t sensor;
        if (xQueueReceive(xSensorQueue, &sensor, 0) != pdTRUE) {
            xEventGroupSetBits(xHeartbeatEvents, EVT_PROCESSOR);
            continue;
        }

        /* Compute accel magnitude squared in fixed-point (x100)^2 = x10000 */
        int32_t ax = sensor.accel_x_x100;
        int32_t ay = sensor.accel_y_x100;
        int32_t az = sensor.accel_z_x100;
        /* mag_sq in units of (0.01 m/s^2)^2 */
        uint32_t mag_sq = (uint32_t)(ax * ax + ay * ay + az * az);
        /* mag in units of 0.01 m/s^2 */
        uint32_t mag_x100 = isqrt32(mag_sq);

        /* speed update: delta = (mag - 9.8 m/s^2) * 0.1
         * mag_x100 units: 0.01 m/s^2, gravity = 980
         * delta_x10 = (mag_x100 - 980) / 10  (tenths of km/h, very rough) */
        int32_t delta = ((int32_t)mag_x100 - 980) / 10;
        speed_kmh_x10 += delta;
        if (speed_kmh_x10 < 0)     speed_kmh_x10 = 0;
        if (speed_kmh_x10 > 2000)  speed_kmh_x10 = 2000; /* 200.0 km/h */

        /* Compute rpm and throttle from fixed-point temperature and accel
         * rpm = 700 + temp_c * 17.5 + mag_m/s^2 * 125
         * temp_c = temperature_c_x10 / 10
         * mag = mag_x100 / 100
         * rpm = 700 + (temp_c_x10 * 175) / 100 + (mag_x100 * 125) / 100 */
        uint32_t rpm = 700u
            + (uint32_t)((int32_t)sensor.temperature_c_x10 * 175 / 1000)
            + (uint32_t)(mag_x100 * 125 / 10000);

        /* throttle_pct_x10 = clamp(120 + mag_x100*140/10000 + temp_c_x10*10/60, 0, 1000) */
        int32_t throttle_x10 = 120
            + (int32_t)(mag_x100 * 140 / 10000)
            + (int32_t)sensor.temperature_c_x10 * 10 / 60;
        if (throttle_x10 < 0)    throttle_x10 = 0;
        if (throttle_x10 > 1000) throttle_x10 = 1000;

        TelemetryData_t telem;
        telem.sensor         = sensor;
        telem.speed_kmh_x10  = (uint16_t)speed_kmh_x10;
        telem.rpm            = (uint16_t)rpm;
        telem.throttle_pct_x10 = (uint16_t)throttle_x10;
        telem.timestamp_ms   = sensor.timestamp_ms;

        if (sensor.temperature_c_x10 > 750 ||  /* > 75.0 C */
            g_active_fault == FAULT_SENSOR_FAILURE) {
            telem.fault_code = 0x01;
            telem.valid      = false;
            xEventGroupSetBits(xSystemEventGroup, EVT_FAULT_DETECTED);
        } else {
            telem.fault_code = 0x00;
            telem.valid      = true;
        }

        xQueueSend(xTelemetryQueue, &telem, 0);

        /* Heartbeat for event-group watchdog */
        xEventGroupSetBits(xHeartbeatEvents, EVT_PROCESSOR);
    }
}
