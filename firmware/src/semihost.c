#include "semihost.h"

static inline int semihost_call( int reason, void * arg )
{
    int value;

    __asm volatile(
        "mov r0, %1\n"
        "mov r1, %2\n"
        "bkpt 0xab\n"
        "mov %0, r0\n"
        : "=r"( value )
        : "r"( reason ), "r"( arg )
        : "r0", "r1", "memory" );

    return value;
}

void semihost_write0( const char * text )
{
    ( void ) semihost_call( 0x04, ( void * ) text );
}

int semihost_open( const char * path, int mode )
{
    struct
    {
        const char * path;
        int mode;
        int length;
    } block =
    {
        .path = path,
        .mode = mode,
        .length = 0
    };

    while( path[ block.length ] != '\0' )
    {
        block.length++;
    }

    return semihost_call( 0x01, &block );
}

int semihost_read( int handle, void * buffer, size_t length )
{
    struct
    {
        int handle;
        void * buffer;
        int length;
    } block =
    {
        .handle = handle,
        .buffer = buffer,
        .length = ( int ) length
    };

    return semihost_call( 0x06, &block );
}

int semihost_write( int handle, const void * buffer, size_t length )
{
    struct
    {
        int handle;
        const void * buffer;
        int length;
    } block =
    {
        .handle = handle,
        .buffer = buffer,
        .length = ( int ) length
    };

    return semihost_call( 0x05, &block );
}

int semihost_close( int handle )
{
    return semihost_call( 0x02, &handle );
}

void semihost_exit( int status )
{
    struct
    {
        uint32_t reason;
        uint32_t status;
    } block =
    {
        .reason = 0x20026U,
        .status = ( uint32_t ) status
    };

    ( void ) semihost_call( 0x20, &block );

    /* Fallback: try SYS_EXIT (0x18) with reason code directly */
    ( void ) semihost_call( 0x18, ( void * ) 0x20026U );

    for( ;; )
    {
        ;
    }
}

void exit( int status )
{
    semihost_exit( status );
}
