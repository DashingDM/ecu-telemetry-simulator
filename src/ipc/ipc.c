#include "ipc.h"
#include "timers.h"

/* ---- Queue storage (static) ---- */
#define SENSOR_QUEUE_LEN    10
#define TELEMETRY_QUEUE_LEN 10

static StaticQueue_t xSensorQueueStatic;
static uint8_t       ucSensorQueueStorage[SENSOR_QUEUE_LEN * sizeof(SensorData_t)];

static StaticQueue_t xTelemetryQueueStatic;
static uint8_t       ucTelemetryQueueStorage[TELEMETRY_QUEUE_LEN * sizeof(TelemetryData_t)];

/* ---- Semaphore storage (static) ---- */
static StaticSemaphore_t xUartMutexStatic;
static StaticSemaphore_t xDataReadySemStatic;
static StaticSemaphore_t xSensorKickSemStatic;

/* ---- Event group storage (static) ---- */
static StaticEventGroup_t xSystemEventGroupStatic;
static StaticEventGroup_t xHeartbeatEventsStatic;

/* ---- Public handles ---- */
QueueHandle_t       xSensorQueue;
QueueHandle_t       xTelemetryQueue;
SemaphoreHandle_t   xUartMutex;
SemaphoreHandle_t   xDataReadySem;
SemaphoreHandle_t   xSensorKickSem;
EventGroupHandle_t  xSystemEventGroup;
EventGroupHandle_t  xHeartbeatEvents;

/* ---- Software timer callback: kick sensor every 100 ms ---- */
static void prvSensorTimerCallback(TimerHandle_t xTimer)
{
    (void)xTimer;
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    xSemaphoreGiveFromISR(xSensorKickSem, &xHigherPriorityTaskWoken);
    portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
}

/* Timer storage */
static StaticTimer_t xSensorTimerStatic;
static TimerHandle_t xSensorTimer;

void ipc_init(void)
{
    xSensorQueue = xQueueCreateStatic(
        SENSOR_QUEUE_LEN, sizeof(SensorData_t),
        ucSensorQueueStorage, &xSensorQueueStatic);

    xTelemetryQueue = xQueueCreateStatic(
        TELEMETRY_QUEUE_LEN, sizeof(TelemetryData_t),
        ucTelemetryQueueStorage, &xTelemetryQueueStatic);

    xUartMutex      = xSemaphoreCreateMutexStatic(&xUartMutexStatic);
    xDataReadySem   = xSemaphoreCreateBinaryStatic(&xDataReadySemStatic);
    xSensorKickSem  = xSemaphoreCreateBinaryStatic(&xSensorKickSemStatic);

    xSystemEventGroup = xEventGroupCreateStatic(&xSystemEventGroupStatic);
    xHeartbeatEvents  = xEventGroupCreateStatic(&xHeartbeatEventsStatic);

    configASSERT(xSensorQueue);
    configASSERT(xTelemetryQueue);
    configASSERT(xUartMutex);
    configASSERT(xDataReadySem);
    configASSERT(xSensorKickSem);
    configASSERT(xSystemEventGroup);
    configASSERT(xHeartbeatEvents);

    /* 100 ms auto-reload timer that kicks the sensor task */
    xSensorTimer = xTimerCreateStatic(
        "SensorTick",
        pdMS_TO_TICKS(100),
        pdTRUE,                        /* auto-reload */
        NULL,
        prvSensorTimerCallback,
        &xSensorTimerStatic);
    configASSERT(xSensorTimer);
    xTimerStart(xSensorTimer, 0);
}
