#ifndef _STDLIB_H_
#define _STDLIB_H_
#include <stddef.h>
/* Minimal stdlib.h for bare-metal FreeRTOS build */
void *malloc(size_t size);
void  free(void *ptr);
void  abort(void) __attribute__((noreturn));
int   abs(int x);

#endif
