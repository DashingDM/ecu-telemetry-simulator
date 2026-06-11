#ifndef _STDIO_H_
#define _STDIO_H_
#include <stddef.h>
#include <stdarg.h>
/* Minimal stdio.h - vsnprintf/snprintf provided by printf.c */
int vsnprintf(char *buf, size_t size, const char *fmt, va_list ap);
int snprintf(char *buf, size_t size, const char *fmt, ...);
int printf(const char *fmt, ...);
#endif
