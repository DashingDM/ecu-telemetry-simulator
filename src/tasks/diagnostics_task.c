#include "diagnostics_task.h"
#include "ipc.h"
#include "fault_injection.h"
#include "uart.h"
#include "compat.h"
#include "FreeRTOS.h"
#include "task.h"
#include "event_groups.h"
#include <string.h>
#include <stdint.h>

/* UART0 receive */
#define UART0_DR  (*((volatile unsigned int *)0x4000C000))
#define UART0_FR  (*((volatile unsigned int *)0x4000C018))
#define UART0_FR_RXFE (1u << 4)

static char cmd_buf[64];
static int  cmd_len = 0;

static void do_cmd(const char *cmd)
{
    char buf[256];
    if (strcmp(cmd, "status") == 0) {
        mini_snprintf(buf, sizeof(buf),
            "[DIAG] Uptime=%lu ms  FreeHeap=%u\r\n",
            (unsigned long)(xTaskGetTickCount() * portTICK_PERIOD_MS),
            (unsigned int)xPortGetFreeHeapSize());
        xSemaphoreTake(xUartMutex, portMAX_DELAY);
        uart_puts(buf);
        xSemaphoreGive(xUartMutex);

    } else if (strcmp(cmd, "tasks") == 0) {
        /* vTaskList requires configUSE_STATS_FORMATTING_FUNCTIONS which
         * is incompatible with static-only allocation in this build.
         * Print task count as a minimal substitute. */
        mini_snprintf(buf, sizeof(buf),
            "[DIAG] Tasks running: %u\r\n",
            (unsigned int)uxTaskGetNumberOfTasks());
        xSemaphoreTake(xUartMutex, portMAX_DELAY);
        uart_puts(buf);
        xSemaphoreGive(xUartMutex);

    } else if (strcmp(cmd, "heap") == 0) {
        mini_snprintf(buf, sizeof(buf), "[DIAG] FreeHeap=%u\r\n",
            (unsigned int)xPortGetFreeHeapSize());
        xSemaphoreTake(xUartMutex, portMAX_DELAY);
        uart_puts(buf);
        xSemaphoreGive(xUartMutex);

    } else if (strcmp(cmd, "stats") == 0) {
        /* vTaskGetRunTimeStats requires configGENERATE_RUN_TIME_STATS.
         * Print heap and task count instead. */
        mini_snprintf(buf, sizeof(buf),
            "[DIAG] Heap=%u Tasks=%u\r\n",
            (unsigned int)xPortGetFreeHeapSize(),
            (unsigned int)uxTaskGetNumberOfTasks());
        xSemaphoreTake(xUartMutex, portMAX_DELAY);
        uart_puts(buf);
        xSemaphoreGive(xUartMutex);

    } else if (strcmp(cmd, "fault none") == 0) {
        fault_clear();
        xSemaphoreTake(xUartMutex, portMAX_DELAY);
        uart_puts("[DIAG] Fault cleared\r\n");
        xSemaphoreGive(xUartMutex);

    } else if (strcmp(cmd, "fault overflow") == 0) {
        fault_inject(FAULT_QUEUE_OVERFLOW);
        xSemaphoreTake(xUartMutex, portMAX_DELAY);
        uart_puts("[DIAG] Fault: QUEUE_OVERFLOW\r\n");
        xSemaphoreGive(xUartMutex);

    } else if (strcmp(cmd, "fault sensor") == 0 || strcmp(cmd, "fault") == 0) {
        fault_inject(FAULT_SENSOR_FAILURE);
        xSemaphoreTake(xUartMutex, portMAX_DELAY);
        uart_puts("[DIAG] Fault: SENSOR_FAILURE\r\n");
        xSemaphoreGive(xUartMutex);

    } else if (strcmp(cmd, "fault process") == 0) {
        fault_inject(FAULT_TASK_DELAY);
        xSemaphoreTake(xUartMutex, portMAX_DELAY);
        uart_puts("[DIAG] Fault: TASK_DELAY (process stall)\r\n");
        xSemaphoreGive(xUartMutex);

    } else if (strcmp(cmd, "reset") == 0) {
        volatile unsigned int *AIRCR = (volatile unsigned int *)0xE000ED0Cu;
        *AIRCR = (0x5FAu << 16) | (1u << 2);

    } else if (strcmp(cmd, "help") == 0) {
        xSemaphoreTake(xUartMutex, portMAX_DELAY);
        uart_puts("[DIAG] Commands: status tasks heap stats "
                  "fault none/overflow/sensor/process reset help\r\n");
        xSemaphoreGive(xUartMutex);

    } else {
        xSemaphoreTake(xUartMutex, portMAX_DELAY);
        uart_puts("[DIAG] Unknown cmd. Type 'help'\r\n");
        xSemaphoreGive(xUartMutex);
    }
}

static void poll_uart(void)
{
    while (!(UART0_FR & UART0_FR_RXFE)) {
        char c = (char)(UART0_DR & 0xFFu);
        if (c == '\r' || c == '\n') {
            if (cmd_len > 0) {
                cmd_buf[cmd_len] = '\0';
                cmd_len = 0;
                xSemaphoreTake(xUartMutex, portMAX_DELAY);
                uart_puts("\r\n");
                xSemaphoreGive(xUartMutex);
                do_cmd(cmd_buf);
            }
        } else if (cmd_len < (int)(sizeof(cmd_buf) - 1)) {
            cmd_buf[cmd_len++] = c;
        }
    }
}

void diagnostics_task(void *pvParameters)
{
    (void)pvParameters;

    vTaskDelay(pdMS_TO_TICKS(500));
    xSemaphoreTake(xUartMutex, portMAX_DELAY);
    uart_puts("[DIAG] Ready. Commands: status tasks heap stats "
              "fault none/overflow/sensor/process reset help\r\n");
    xSemaphoreGive(xUartMutex);

    for (;;) {
        poll_uart();
        vTaskDelay(pdMS_TO_TICKS(50));
    }
}
