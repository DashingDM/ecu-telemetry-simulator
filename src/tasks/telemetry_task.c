#include "telemetry_task.h"
#include "ipc.h"
#include "health_monitor_task.h"
#include "uart.h"
#include "compat.h"
#include "FreeRTOS.h"
#include "task.h"
#include "event_groups.h"

void telemetry_task(void *pvParameters)
{
    (void)pvParameters;

    for (;;) {
        TelemetryData_t telem;
        if (xQueueReceive(xTelemetryQueue, &telem, portMAX_DELAY) == pdTRUE) {
            char buf[200];
            /* Print fixed-point values in human-readable form */
            mini_snprintf(buf, sizeof(buf),
                "[TELEM] ts=%lu temp=%d.%dC "
                "ax=%d.%02d ay=%d.%02d az=%d.%02d "
                "spd=%u.%ukm/h rpm=%u thr=%u.%u%% "
                "fault=0x%02X valid=%d\r\n",
                (unsigned long)telem.timestamp_ms,
                (int)(telem.sensor.temperature_c_x10 / 10),
                (int)(telem.sensor.temperature_c_x10 < 0
                    ? -(telem.sensor.temperature_c_x10 % 10)
                    :   telem.sensor.temperature_c_x10 % 10),
                (int)(telem.sensor.accel_x_x100 / 100),
                (int)(telem.sensor.accel_x_x100 < 0
                    ? -(telem.sensor.accel_x_x100 % 100)
                    :   telem.sensor.accel_x_x100 % 100),
                (int)(telem.sensor.accel_y_x100 / 100),
                (int)(telem.sensor.accel_y_x100 < 0
                    ? -(telem.sensor.accel_y_x100 % 100)
                    :   telem.sensor.accel_y_x100 % 100),
                (int)(telem.sensor.accel_z_x100 / 100),
                (int)(telem.sensor.accel_z_x100 < 0
                    ? -(telem.sensor.accel_z_x100 % 100)
                    :   telem.sensor.accel_z_x100 % 100),
                (unsigned int)(telem.speed_kmh_x10 / 10),
                (unsigned int)(telem.speed_kmh_x10 % 10),
                (unsigned int)telem.rpm,
                (unsigned int)(telem.throttle_pct_x10 / 10),
                (unsigned int)(telem.throttle_pct_x10 % 10),
                (unsigned int)telem.fault_code,
                (int)telem.valid);

            xSemaphoreTake(xUartMutex, portMAX_DELAY);
            uart_puts(buf);
            xSemaphoreGive(xUartMutex);

            /* Heartbeat for event-group watchdog */
            xEventGroupSetBits(xHeartbeatEvents, EVT_TELEMETRY);
        }
    }
}
