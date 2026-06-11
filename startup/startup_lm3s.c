#include <stdint.h>

/* Linker script symbols */
extern uint32_t _etext;
extern uint32_t _sdata;
extern uint32_t _edata;
extern uint32_t _sbss;
extern uint32_t _ebss;
extern uint32_t _estack;

/* Main entry */
extern int main(void);

/* Default handler */
void Default_Handler(void) {
    for (;;);
}

/* Forward declarations for handlers */
void Reset_Handler(void);
void NMI_Handler(void)          __attribute__((weak, alias("Default_Handler")));
void HardFault_Handler(void)    __attribute__((weak, alias("Default_Handler")));
void MemManage_Handler(void)    __attribute__((weak, alias("Default_Handler")));
void BusFault_Handler(void)     __attribute__((weak, alias("Default_Handler")));
void UsageFault_Handler(void)   __attribute__((weak, alias("Default_Handler")));
void SVC_Handler(void)          __attribute__((weak, alias("Default_Handler")));
void DebugMon_Handler(void)     __attribute__((weak, alias("Default_Handler")));
void PendSV_Handler(void)       __attribute__((weak, alias("Default_Handler")));
void SysTick_Handler(void)      __attribute__((weak, alias("Default_Handler")));
/* IRQs 0-31 */
void IRQ0_Handler(void)  __attribute__((weak, alias("Default_Handler")));
void IRQ1_Handler(void)  __attribute__((weak, alias("Default_Handler")));
void IRQ2_Handler(void)  __attribute__((weak, alias("Default_Handler")));
void IRQ3_Handler(void)  __attribute__((weak, alias("Default_Handler")));
void IRQ4_Handler(void)  __attribute__((weak, alias("Default_Handler")));
void IRQ5_Handler(void)  __attribute__((weak, alias("Default_Handler")));
void IRQ6_Handler(void)  __attribute__((weak, alias("Default_Handler")));
void IRQ7_Handler(void)  __attribute__((weak, alias("Default_Handler")));
void IRQ8_Handler(void)  __attribute__((weak, alias("Default_Handler")));
void IRQ9_Handler(void)  __attribute__((weak, alias("Default_Handler")));
void IRQ10_Handler(void) __attribute__((weak, alias("Default_Handler")));
void IRQ11_Handler(void) __attribute__((weak, alias("Default_Handler")));
void IRQ12_Handler(void) __attribute__((weak, alias("Default_Handler")));
void IRQ13_Handler(void) __attribute__((weak, alias("Default_Handler")));
void IRQ14_Handler(void) __attribute__((weak, alias("Default_Handler")));
void IRQ15_Handler(void) __attribute__((weak, alias("Default_Handler")));
void IRQ16_Handler(void) __attribute__((weak, alias("Default_Handler")));
void IRQ17_Handler(void) __attribute__((weak, alias("Default_Handler")));
void IRQ18_Handler(void) __attribute__((weak, alias("Default_Handler")));
void IRQ19_Handler(void) __attribute__((weak, alias("Default_Handler")));
void IRQ20_Handler(void) __attribute__((weak, alias("Default_Handler")));
void IRQ21_Handler(void) __attribute__((weak, alias("Default_Handler")));
void IRQ22_Handler(void) __attribute__((weak, alias("Default_Handler")));
void IRQ23_Handler(void) __attribute__((weak, alias("Default_Handler")));
void IRQ24_Handler(void) __attribute__((weak, alias("Default_Handler")));
void IRQ25_Handler(void) __attribute__((weak, alias("Default_Handler")));
void IRQ26_Handler(void) __attribute__((weak, alias("Default_Handler")));
void IRQ27_Handler(void) __attribute__((weak, alias("Default_Handler")));
void IRQ28_Handler(void) __attribute__((weak, alias("Default_Handler")));
void IRQ29_Handler(void) __attribute__((weak, alias("Default_Handler")));
void IRQ30_Handler(void) __attribute__((weak, alias("Default_Handler")));
void IRQ31_Handler(void) __attribute__((weak, alias("Default_Handler")));

/* Vector table */
__attribute__((section(".vectors")))
const void *vector_table[] = {
    (void *)&_estack,       /* Initial stack pointer */
    Reset_Handler,          /* Reset */
    NMI_Handler,
    HardFault_Handler,
    MemManage_Handler,
    BusFault_Handler,
    UsageFault_Handler,
    0, 0, 0, 0,             /* Reserved */
    SVC_Handler,
    DebugMon_Handler,
    0,                      /* Reserved */
    PendSV_Handler,
    SysTick_Handler,
    /* External IRQs 0-31 */
    IRQ0_Handler, IRQ1_Handler, IRQ2_Handler, IRQ3_Handler,
    IRQ4_Handler, IRQ5_Handler, IRQ6_Handler, IRQ7_Handler,
    IRQ8_Handler, IRQ9_Handler, IRQ10_Handler, IRQ11_Handler,
    IRQ12_Handler, IRQ13_Handler, IRQ14_Handler, IRQ15_Handler,
    IRQ16_Handler, IRQ17_Handler, IRQ18_Handler, IRQ19_Handler,
    IRQ20_Handler, IRQ21_Handler, IRQ22_Handler, IRQ23_Handler,
    IRQ24_Handler, IRQ25_Handler, IRQ26_Handler, IRQ27_Handler,
    IRQ28_Handler, IRQ29_Handler, IRQ30_Handler, IRQ31_Handler,
};

void Reset_Handler(void) {
    /* Copy .data from FLASH to SRAM */
    uint32_t *src = &_etext;
    uint32_t *dst = &_sdata;
    while (dst < &_edata) {
        *dst++ = *src++;
    }
    /* Zero .bss */
    dst = &_sbss;
    while (dst < &_ebss) {
        *dst++ = 0;
    }
    main();
    for (;;);
}
