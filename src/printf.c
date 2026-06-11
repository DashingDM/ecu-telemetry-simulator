/*
 * Minimal embedded vsnprintf / snprintf implementation.
 * Supports: %d, %u, %lu, %ld, %x, %02X, %s, %c, %f (basic), %%
 */
#include "printf.h"
#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>

static void buf_putc(char *buf, size_t size, size_t *pos, char c)
{
    if (*pos + 1 < size) {
        buf[*pos] = c;
    }
    (*pos)++;
}

static void buf_puts_n(char *buf, size_t size, size_t *pos,
                       const char *s, int width, int left_align, char pad)
{
    /* measure string */
    int len = 0;
    const char *p = s;
    while (*p++) len++;

    int pad_count = (width > len) ? (width - len) : 0;

    if (!left_align) {
        for (int i = 0; i < pad_count; i++) buf_putc(buf, size, pos, pad);
    }
    while (*s) buf_putc(buf, size, pos, *s++);
    if (left_align) {
        for (int i = 0; i < pad_count; i++) buf_putc(buf, size, pos, ' ');
    }
}

static void fmt_uint(char *buf, size_t size, size_t *pos,
                     unsigned long val, int base, int upper,
                     int width, char pad, int left_align)
{
    char tmp[32];
    int  tlen = 0;
    static const char digits_lo[] = "0123456789abcdef";
    static const char digits_up[] = "0123456789ABCDEF";
    const char *digits = upper ? digits_up : digits_lo;

    if (val == 0) {
        tmp[tlen++] = '0';
    } else {
        while (val) {
            tmp[tlen++] = digits[val % (unsigned)base];
            val /= (unsigned)base;
        }
    }

    int pad_count = (width > tlen) ? (width - tlen) : 0;

    if (!left_align) {
        for (int i = 0; i < pad_count; i++) buf_putc(buf, size, pos, pad);
    }
    for (int i = tlen - 1; i >= 0; i--) buf_putc(buf, size, pos, tmp[i]);
    if (left_align) {
        for (int i = 0; i < pad_count; i++) buf_putc(buf, size, pos, ' ');
    }
}

static void fmt_float(char *buf, size_t size, size_t *pos,
                      double val, int prec)
{
    if (prec < 0) prec = 6;
    if (prec > 9) prec = 9;

    if (val < 0.0) {
        buf_putc(buf, size, pos, '-');
        val = -val;
    }

    unsigned long int_part = (unsigned long)val;
    fmt_uint(buf, size, pos, int_part, 10, 0, 0, ' ', 0);
    buf_putc(buf, size, pos, '.');

    double frac = val - (double)int_part;
    /* Multiply up to prec digits */
    static const unsigned long pow10[10] = {
        1, 10, 100, 1000, 10000, 100000, 1000000, 10000000, 100000000, 1000000000
    };
    unsigned long frac_int = (unsigned long)(frac * (double)pow10[prec] + 0.5);
    /* zero-pad fractional part */
    char tmp[16];
    int  tlen = 0;
    for (int i = 0; i < prec; i++) {
        tmp[tlen++] = '0' + (int)(frac_int % 10);
        frac_int /= 10;
    }
    for (int i = tlen - 1; i >= 0; i--) buf_putc(buf, size, pos, tmp[i]);
}

int mini_vsnprintf(char *buf, size_t size, const char *fmt, va_list ap)
{
    size_t pos = 0;

    for (; *fmt; fmt++) {
        if (*fmt != '%') {
            buf_putc(buf, size, &pos, *fmt);
            continue;
        }
        fmt++;
        if (*fmt == '\0') break;

        /* Flags */
        int left_align = 0;
        char pad = ' ';
        if (*fmt == '-') { left_align = 1; fmt++; }
        if (*fmt == '0') { pad = '0'; fmt++; }

        /* Width */
        int width = 0;
        while (*fmt >= '0' && *fmt <= '9') {
            width = width * 10 + (*fmt - '0');
            fmt++;
        }

        /* Precision */
        int prec = -1;
        if (*fmt == '.') {
            fmt++;
            prec = 0;
            while (*fmt >= '0' && *fmt <= '9') {
                prec = prec * 10 + (*fmt - '0');
                fmt++;
            }
        }

        /* Length modifier */
        int is_long = 0;
        if (*fmt == 'l') {
            is_long = 1;
            fmt++;
            if (*fmt == 'l') fmt++; /* ignore ll for now */
        }

        switch (*fmt) {
        case 'd':
        case 'i': {
            long val = is_long ? va_arg(ap, long) : (long)va_arg(ap, int);
            if (val < 0) {
                buf_putc(buf, size, &pos, '-');
                val = -val;
                if (width > 0) width--;
            }
            fmt_uint(buf, size, &pos, (unsigned long)val, 10, 0, width, pad, left_align);
            break;
        }
        case 'u': {
            unsigned long val = is_long ? va_arg(ap, unsigned long)
                                        : (unsigned long)va_arg(ap, unsigned int);
            fmt_uint(buf, size, &pos, val, 10, 0, width, pad, left_align);
            break;
        }
        case 'x': {
            unsigned long val = is_long ? va_arg(ap, unsigned long)
                                        : (unsigned long)va_arg(ap, unsigned int);
            fmt_uint(buf, size, &pos, val, 16, 0, width, pad, left_align);
            break;
        }
        case 'X': {
            unsigned long val = is_long ? va_arg(ap, unsigned long)
                                        : (unsigned long)va_arg(ap, unsigned int);
            fmt_uint(buf, size, &pos, val, 16, 1, width, pad, left_align);
            break;
        }
        case 'p': {
            unsigned long val = (unsigned long)va_arg(ap, void *);
            buf_putc(buf, size, &pos, '0');
            buf_putc(buf, size, &pos, 'x');
            fmt_uint(buf, size, &pos, val, 16, 0, 8, '0', 0);
            break;
        }
        case 's': {
            const char *s = va_arg(ap, const char *);
            if (!s) s = "(null)";
            buf_puts_n(buf, size, &pos, s, width, left_align, pad);
            break;
        }
        case 'c': {
            char c = (char)va_arg(ap, int);
            buf_putc(buf, size, &pos, c);
            break;
        }
        case 'f': {
            double val = va_arg(ap, double);
            if (prec < 0) prec = 1;
            fmt_float(buf, size, &pos, val, prec);
            break;
        }
        case '%':
            buf_putc(buf, size, &pos, '%');
            break;
        default:
            buf_putc(buf, size, &pos, '%');
            buf_putc(buf, size, &pos, *fmt);
            break;
        }
    }

    if (size > 0) {
        buf[pos < size ? pos : size - 1] = '\0';
    }
    return (int)pos;
}

int mini_snprintf(char *buf, size_t size, const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    int ret = mini_vsnprintf(buf, size, fmt, ap);
    va_end(ap);
    return ret;
}
