#ifndef _FIRMWARE_STDDEF_H
#define _FIRMWARE_STDDEF_H

typedef __SIZE_TYPE__ size_t;
typedef __PTRDIFF_TYPE__ ptrdiff_t;

#ifndef NULL
#define NULL ( ( void * ) 0 )
#endif

#ifndef SIZE_MAX
#define SIZE_MAX ( ( size_t ) ~ ( size_t ) 0 )
#endif

#endif
