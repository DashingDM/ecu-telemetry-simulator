#include "firmware.h"

static StaticTask_t xIdleTaskTCB;
static StackType_t uxIdleTaskStack[ configMINIMAL_STACK_SIZE ];

static StaticTask_t xTimerTaskTCB;
static StackType_t uxTimerTaskStack[ configTIMER_TASK_STACK_DEPTH ];

void vAssertCalled( const char * file, int line )
{
    taskDISABLE_INTERRUPTS();
    console_writef( "ASSERT FAILED: %s:%d", file, line );
    for( ;; )
    {
        ;
    }
}

void vApplicationMallocFailedHook( void )
{
    console_writeln( "Malloc failed" );
    taskDISABLE_INTERRUPTS();
    for( ;; )
    {
        ;
    }
}

void vApplicationStackOverflowHook( TaskHandle_t xTask,
                                    char * pcTaskName )
{
    ( void ) xTask;
    console_writef( "Stack overflow in %s", pcTaskName );
    taskDISABLE_INTERRUPTS();
    for( ;; )
    {
        ;
    }
}

void vApplicationIdleHook( void )
{
    __asm volatile( "wfi" );
}

void vApplicationGetIdleTaskMemory( StaticTask_t ** ppxIdleTaskTCBBuffer,
                                    StackType_t ** ppxIdleTaskStackBuffer,
                                    size_t * pulIdleTaskStackSize )
{
    *ppxIdleTaskTCBBuffer = &xIdleTaskTCB;
    *ppxIdleTaskStackBuffer = uxIdleTaskStack;
    *pulIdleTaskStackSize = configMINIMAL_STACK_SIZE;
}

void vApplicationGetTimerTaskMemory( StaticTask_t ** ppxTimerTaskTCBBuffer,
                                     StackType_t ** ppxTimerTaskStackBuffer,
                                     size_t * pulTimerTaskStackSize )
{
    *ppxTimerTaskTCBBuffer = &xTimerTaskTCB;
    *ppxTimerTaskStackBuffer = uxTimerTaskStack;
    *pulTimerTaskStackSize = configTIMER_TASK_STACK_DEPTH;
}
