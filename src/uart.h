#ifndef UART_H
#define UART_H

#include <stdarg.h>

void uart_init(void);
void uart_putchar(char c);
void uart_puts(const char *s);
void uart_printf(const char *fmt, ...);

#endif /* UART_H */
