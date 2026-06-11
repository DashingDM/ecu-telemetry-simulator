#include "uart.h"
#include "printf.h"
#include <stdarg.h>

/* UART0 on lm3s6965evb (PL011) */
#define UART0_DR  (*((volatile unsigned int *)0x4000C000))
#define UART0_FR  (*((volatile unsigned int *)0x4000C018))
#define UART0_FR_TXFF  (1u << 5)

void uart_init(void)
{
    /* QEMU pre-initializes UART for us */
}

void uart_putchar(char c)
{
    while (UART0_FR & UART0_FR_TXFF);
    UART0_DR = (unsigned int)c;
}

void uart_puts(const char *s)
{
    while (*s) {
        uart_putchar(*s++);
    }
}

void uart_printf(const char *fmt, ...)
{
    char buf[256];
    va_list args;
    va_start(args, fmt);
    mini_vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    uart_puts(buf);
}
