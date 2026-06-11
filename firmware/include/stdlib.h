#ifndef _FIRMWARE_STDLIB_H
#define _FIRMWARE_STDLIB_H

#include "stddef.h"

#define EXIT_SUCCESS 0
#define EXIT_FAILURE 1

void exit( int status ) __attribute__( ( noreturn ) );

#endif
