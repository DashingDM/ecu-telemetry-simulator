#include <stdint.h>

uint32_t SystemCoreClock = 8000000UL;

void SystemInit( void )
{
    /* QEMU's STM32F100 model starts with a usable default clock tree for this
     * demo. Leave the reset clock tree in place and let SysTick use the
     * configured CPU clock constant. */
}
