#ifndef HEALTH_MONITOR_TASK_H
#define HEALTH_MONITOR_TASK_H

void health_monitor_task(void *pvParameters);

/* watchdog_kick is no longer used — tasks call
 * xEventGroupSetBits(xHeartbeatEvents, EVT_xxx) directly */

#endif /* HEALTH_MONITOR_TASK_H */
