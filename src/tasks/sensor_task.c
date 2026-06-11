#include "sensor_task.h"
#include "ipc.h"
#include "health_monitor_task.h"
#include "fault_injection.h"
#include "FreeRTOS.h"
#include "task.h"
#include "semphr.h"
#include "event_groups.h"
#include <stdint.h>

/* LCG PRNG for fixed-point noise */
static uint32_t lcg_rand(uint32_t *state)
{
    *state = *state * 1664525u + 1013904223u;
    return *state;
}

void sensor_task(void *pvParameters)
{
    (void)pvParameters;
    uint32_t rng = 0xDEADBEEFu;

    for (;;) {
        /* Block until the 100 ms software timer fires */
        xSemaphoreTake(xSensorKickSem, portMAX_DELAY);

        if (g_active_fault == FAULT_TASK_DELAY) {
            vTaskDelay(pdMS_TO_TICKS(3000));
        }

        SensorData_t data;
        uint32_t now_ms = (uint32_t)(xTaskGetTickCount() * portTICK_PERIOD_MS);
        data.timestamp_ms = now_ms;

        if (g_active_fault == FAULT_SENSOR_FAILURE) {
            /* Error sentinel values in fixed-point */
            data.temperature_c_x10 = 1550;   /* 155.0 C */
            data.accel_x_x100      = 420;    /* 4.20 — out-of-range flag */
            data.accel_y_x100      = 420;
            data.accel_z_x100      = 420;
        } else {
            /* Sine wave temperature 20-80 C, period ~6.28 s
             * Fixed-point: value * 10 */
            /* Simple approach: temperature oscillates between 200..800 (20.0-80.0 C)
             * using modular counter as phase */
            uint32_t phase = (now_ms / 100) % 63u; /* 0..62 */
            /* Approximate: half-period up, half-period down */
            int32_t temp_x10;
            if (phase < 32) {
                temp_x10 = 200 + (int32_t)phase * (600 / 31);
            } else {
                temp_x10 = 800 - (int32_t)(phase - 32) * (600 / 31);
            }
            data.temperature_c_x10 = (int16_t)temp_x10;

            /* Accelerometer noise: accel_x/y in [-100, 100] = [-1.00, 1.00] g
             *                      accel_z around 980 = 9.80 m/s^2 */
            lcg_rand(&rng);
            data.accel_x_x100 = (int16_t)((int32_t)(rng & 0xFFFFu) * 200 / 65535 - 100);
            lcg_rand(&rng);
            data.accel_y_x100 = (int16_t)((int32_t)(rng & 0xFFFFu) * 200 / 65535 - 100);
            lcg_rand(&rng);
            data.accel_z_x100 = (int16_t)(980 + (int32_t)(rng & 0xFFFFu) * 40 / 65535 - 20);
        }

        xQueueSend(xSensorQueue, &data, 0);
        xEventGroupSetBits(xSystemEventGroup, EVT_SENSOR_READY);
        xSemaphoreGive(xDataReadySem);

        /* Heartbeat for event-group watchdog */
        xEventGroupSetBits(xHeartbeatEvents, EVT_SENSOR);
    }
}
