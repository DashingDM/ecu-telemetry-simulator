#include "fault_injection.h"
#include "FreeRTOS.h"
#include "task.h"

volatile FaultType_t g_active_fault = FAULT_NONE;

void fault_inject(FaultType_t fault)
{
    g_active_fault = fault;
}

void fault_clear(void)
{
    g_active_fault = FAULT_NONE;
}
