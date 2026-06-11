#ifndef SEMIHOST_H
#define SEMIHOST_H

#include "stddef.h"
#include "stdint.h"

void semihost_write0( const char * text );
int semihost_open( const char * path, int mode );
int semihost_read( int handle, void * buffer, size_t length );
int semihost_write( int handle, const void * buffer, size_t length );
int semihost_close( int handle );
void semihost_exit( int status ) __attribute__( ( noreturn ) );

#endif
