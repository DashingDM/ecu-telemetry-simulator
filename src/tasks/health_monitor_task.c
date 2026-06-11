#include "health_monitor_task.h"
#include "ipc.h"
#include "uart.h"
#include "compat.h"
#include "FreeRTOS.h"
#include "task.h"
#include "event_groups.h"

#define ALL_HEARTBEAT_BITS  (EVT_SENSOR | EVT_PROCESSOR | EVT_TELEMETRY)

static volatile uint32_t watchdog_warnings = 0;
static volatile uint32_t beat_count[3]; /* sensor, processor, telemetry */

void health_monitor_task(void *pvParameters)
{
    (void)pvParameters;

    for (;;) {
        /* Wait up to 1000 ms for all three tasks to report in */
        EventBits_t bits = xEventGroupWaitBits(
            xHeartbeatEvents,
            ALL_HEARTBEAT_BITS,
            pdTRUE,          /* clear bits on exit */
            pdTRUE,          /* wait for ALL bits */
            pdMS_TO_TICKS(1000));

        if ((bits & ALL_HEARTBEAT_BITS) == ALL_HEARTBEAT_BITS) {
            /* All tasks healthy */
            beat_count[0]++;
            beat_count[1]++;
            beat_count[2]++;

            char buf[128];
            mini_snprintf(buf, sizeof(buf),
                "[HLTH] OK sensor=%lu proc=%lu telem=%lu heap=%u\r\n",
                (unsigned long)beat_count[0],
                (unsigned long)beat_count[1],
                (unsigned long)beat_count[2],
                (unsigned int)xPortGetFreeHeapSize());
            xSemaphoreTake(xUartMutex, portMAX_DELAY);
            uart_puts(buf);
            xSemaphoreGive(xUartMutex);
        } else {
            /* Timeout — at least one task missed its beat */
            watchdog_warnings++;

            char buf[192];
            mini_snprintf(buf, sizeof(buf),
                "[WDOG] TIMEOUT warnings=%lu missing:%s%s%s\r\n",
                (unsigned long)watchdog_warnings,
                (bits & EVT_SENSOR)    ? "" : " Sensor",
                (bits & EVT_PROCESSOR) ? "" : " Processor",
                (bits & EVT_TELEMETRY) ? "" : " Telemetry");

            xSemaphoreTake(xUartMutex, portMAX_DELAY);
            uart_puts(buf);
            xSemaphoreGive(xUartMutex);

            xEventGroupSetBits(xSystemEventGroup, EVT_WATCHDOG_RESET);
        }
    }
}
