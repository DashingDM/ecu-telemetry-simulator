#ifndef FAULT_INJECTION_H
#define FAULT_INJECTION_H

#include <stdint.h>

typedef enum {
    FAULT_NONE = 0,
    FAULT_TASK_DELAY,       /* inject extra delay into sensor task */
    FAULT_QUEUE_OVERFLOW,   /* flood sensor queue */
    FAULT_SENSOR_FAILURE,   /* mark sensor as failed */
} FaultType_t;

extern volatile FaultType_t g_active_fault;

void fault_inject(FaultType_t fault);
void fault_clear(void);

#endif /* FAULT_INJECTION_H */
