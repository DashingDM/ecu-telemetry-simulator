#include "FreeRTOS.h"
#include "task.h"
#include "uart.h"
#include "ipc.h"
#include "sensor_task.h"
#include "processing_task.h"
#include "telemetry_task.h"
#include "health_monitor_task.h"
#include "diagnostics_task.h"

/* ---- Stack sizes ---- */
#define SENSOR_STACK_DEPTH      256
#define PROC_STACK_DEPTH        256
#define TELEM_STACK_DEPTH       256
#define HEALTH_STACK_DEPTH      256
#define DIAG_STACK_DEPTH        512

/* ---- Static TCBs and stacks ---- */
static StaticTask_t xSensorTCB;
static StackType_t  uxSensorStack[SENSOR_STACK_DEPTH];

static StaticTask_t xProcTCB;
static StackType_t  uxProcStack[PROC_STACK_DEPTH];

static StaticTask_t xTelemTCB;
static StackType_t  uxTelemStack[TELEM_STACK_DEPTH];

static StaticTask_t xHealthTCB;
static StackType_t  uxHealthStack[HEALTH_STACK_DEPTH];

static StaticTask_t xDiagTCB;
static StackType_t  uxDiagStack[DIAG_STACK_DEPTH];

/* ---- Required static allocation hooks ---- */

/* Idle task */
static StaticTask_t xIdleTCB;
static StackType_t  uxIdleStack[configMINIMAL_STACK_SIZE];

void vApplicationGetIdleTaskMemory(StaticTask_t **ppxIdleTaskTCBBuffer,
                                   StackType_t  **ppxIdleTaskStackBuffer,
                                   uint32_t      *pulIdleTaskStackSize)
{
    *ppxIdleTaskTCBBuffer   = &xIdleTCB;
    *ppxIdleTaskStackBuffer = uxIdleStack;
    *pulIdleTaskStackSize   = configMINIMAL_STACK_SIZE;
}

/* Timer task */
static StaticTask_t xTimerTCB;
static StackType_t  uxTimerStack[configTIMER_TASK_STACK_DEPTH];

void vApplicationGetTimerTaskMemory(StaticTask_t **ppxTimerTaskTCBBuffer,
                                    StackType_t  **ppxTimerTaskStackBuffer,
                                    uint32_t      *pulTimerTaskStackSize)
{
    *ppxTimerTaskTCBBuffer   = &xTimerTCB;
    *ppxTimerTaskStackBuffer = uxTimerStack;
    *pulTimerTaskStackSize   = configTIMER_TASK_STACK_DEPTH;
}

/* ---- Error hooks ---- */
void vApplicationStackOverflowHook(TaskHandle_t xTask, char *pcTaskName)
{
    (void)xTask;
    (void)pcTaskName;
    uart_puts("[FATAL] Stack overflow!\r\n");
    for (;;);
}

void vApplicationMallocFailedHook(void)
{
    uart_puts("[FATAL] Malloc failed!\r\n");
    for (;;);
}

int main(void)
{
    uart_init();
    uart_puts("\r\n========================================\r\n");
    uart_puts("  FreeRTOS ECU Simulator - lm3s6965evb  \r\n");
    uart_puts("========================================\r\n");

    ipc_init();

    xTaskCreateStatic(sensor_task,         "Sensor", SENSOR_STACK_DEPTH,
                      NULL, 3, uxSensorStack, &xSensorTCB);
    xTaskCreateStatic(processing_task,     "Proc",   PROC_STACK_DEPTH,
                      NULL, 3, uxProcStack,   &xProcTCB);
    xTaskCreateStatic(telemetry_task,      "Telem",  TELEM_STACK_DEPTH,
                      NULL, 2, uxTelemStack,  &xTelemTCB);
    xTaskCreateStatic(health_monitor_task, "Health", HEALTH_STACK_DEPTH,
                      NULL, 4, uxHealthStack, &xHealthTCB);
    xTaskCreateStatic(diagnostics_task,    "Diag",   DIAG_STACK_DEPTH,
                      NULL, 1, uxDiagStack,   &xDiagTCB);

    uart_puts("[MAIN] Tasks created. Starting scheduler...\r\n");
    vTaskStartScheduler();

    uart_puts("[MAIN] Scheduler returned!\r\n");
    for (;;);
}
