/*
 * syscalls.c — bare-metal C library stubs
 * Provides malloc/free (via FreeRTOS heap), abort, and string functions.
 */
#include <stddef.h>
#include <stdint.h>

/* ---- Memory ---- */
/* Static-allocation build: no heap manager linked.
 * Provide stubs so code that references these symbols links. */
void *malloc(size_t size) { (void)size; return (void *)0; }
void  free(void *ptr)     { (void)ptr; }

/* xPortGetFreeHeapSize is normally provided by heap_4.c.
 * With static allocation only there is no heap, so return 0. */
#include <stdint.h>
size_t xPortGetFreeHeapSize(void) { return 0; }

void abort(void) { for (;;); }

int abs(int x) { return x < 0 ? -x : x; }

/* ---- String functions ---- */
void *memset(void *dst, int c, size_t n)
{
    unsigned char *d = (unsigned char *)dst;
    while (n--) *d++ = (unsigned char)c;
    return dst;
}

void *memcpy(void *dst, const void *src, size_t n)
{
    unsigned char *d = (unsigned char *)dst;
    const unsigned char *s = (const unsigned char *)src;
    while (n--) *d++ = *s++;
    return dst;
}

void *memmove(void *dst, const void *src, size_t n)
{
    unsigned char *d = (unsigned char *)dst;
    const unsigned char *s = (const unsigned char *)src;
    if (d < s) {
        while (n--) *d++ = *s++;
    } else {
        d += n; s += n;
        while (n--) *--d = *--s;
    }
    return dst;
}

int memcmp(const void *a, const void *b, size_t n)
{
    const unsigned char *p = (const unsigned char *)a;
    const unsigned char *q = (const unsigned char *)b;
    while (n--) {
        if (*p != *q) return (int)*p - (int)*q;
        p++; q++;
    }
    return 0;
}

size_t strlen(const char *s)
{
    const char *p = s;
    while (*p) p++;
    return (size_t)(p - s);
}

char *strcpy(char *dst, const char *src)
{
    char *d = dst;
    while ((*d++ = *src++));
    return dst;
}

char *strncpy(char *dst, const char *src, size_t n)
{
    char *d = dst;
    while (n && (*d++ = *src++)) n--;
    while (n--) *d++ = '\0';
    return dst;
}

int strcmp(const char *a, const char *b)
{
    while (*a && (*a == *b)) { a++; b++; }
    return (unsigned char)*a - (unsigned char)*b;
}

int strncmp(const char *a, const char *b, size_t n)
{
    while (n && *a && (*a == *b)) { a++; b++; n--; }
    if (n == 0) return 0;
    return (unsigned char)*a - (unsigned char)*b;
}

char *strchr(const char *s, int c)
{
    while (*s) {
        if (*s == (char)c) return (char *)s;
        s++;
    }
    return (c == '\0') ? (char *)s : NULL;
}

/* ---- stdio stubs (forward to our mini_printf) ---- */
#include "printf.h"
#include <stdarg.h>

int vsnprintf(char *buf, size_t size, const char *fmt, va_list ap)
{
    return mini_vsnprintf(buf, size, fmt, ap);
}

int snprintf(char *buf, size_t size, const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    int r = mini_vsnprintf(buf, size, fmt, ap);
    va_end(ap);
    return r;
}

int printf(const char *fmt, ...)
{
    char buf[256];
    va_list ap;
    va_start(ap, fmt);
    int r = mini_vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    /* Output to UART */
    extern void uart_puts(const char *);
    uart_puts(buf);
    return r;
}

/* ---- Math stubs ---- */
/* sinf via Taylor series approximation */
float sinf(float x)
{
    const float PI = 3.14159265f;
    const float TWO_PI = 6.28318530f;
    while (x >  PI) x -= TWO_PI;
    while (x < -PI) x += TWO_PI;
    float x2 = x * x;
    float x3 = x2 * x;
    float x5 = x3 * x2;
    float x7 = x5 * x2;
    return x - x3 / 6.0f + x5 / 120.0f - x7 / 5040.0f;
}

float cosf(float x)
{
    return sinf(x + 1.5707963f);
}

float sqrtf(float x)
{
    if (x <= 0.0f) return 0.0f;
    float g = x * 0.5f;
    int i;
    for (i = 0; i < 8; i++) g = (g + x / g) * 0.5f;
    return g;
}

float fabsf(float x) { return x < 0.0f ? -x : x; }
