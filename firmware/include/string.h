#ifndef _FIRMWARE_STRING_H
#define _FIRMWARE_STRING_H

#include "stddef.h"

void * memcpy( void * dest, const void * src, size_t n );
void * memset( void * dest, int c, size_t n );
int memcmp( const void * s1, const void * s2, size_t n );
size_t strlen( const char * s );
int strcmp( const char * a, const char * b );
size_t strcspn( const char * s, const char * reject );

#endif
