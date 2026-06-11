#ifndef PRINTF_H
#define PRINTF_H

#include <stdarg.h>
#include <stddef.h>

int mini_vsnprintf(char *buf, size_t size, const char *fmt, va_list ap);
int mini_snprintf(char *buf, size_t size, const char *fmt, ...);

#endif /* PRINTF_H */
