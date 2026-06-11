#include "firmware.h"
#include "semihost.h"

#include <stdarg.h>

static StaticSemaphore_t xConsoleMutexBuffer;
static SemaphoreHandle_t xConsoleMutex;
static int xConsoleInputHandle = -1;

static void prvAppendChar( char * buffer, size_t buffer_size, size_t * used, char c )
{
    if( ( *used + 1U ) < buffer_size )
    {
        buffer[ *used ] = c;
        *used += 1U;
        buffer[ *used ] = '\0';
    }
}

static void prvAppendString( char * buffer, size_t buffer_size, size_t * used, const char * text )
{
    if( text == NULL )
    {
        text = "(null)";
    }

    for( ; *text != '\0'; text++ )
    {
        prvAppendChar( buffer, buffer_size, used, *text );
    }
}

static void prvAppendUnsigned( char * buffer,
                               size_t buffer_size,
                               size_t * used,
                               unsigned long value,
                               unsigned base,
                               unsigned width,
                               bool zero_pad )
{
    char digits[ 32 ];
    size_t count = 0U;

    do
    {
        unsigned digit = ( unsigned ) ( value % base );
        digits[ count++ ] = ( char ) ( ( digit < 10U ) ? ( '0' + digit ) : ( 'a' + ( digit - 10U ) ) );
        value /= base;
    }
    while( ( value != 0UL ) && ( count < sizeof( digits ) ) );

    while( count < width )
    {
        prvAppendChar( buffer, buffer_size, used, zero_pad ? '0' : ' ' );
        width--;
    }

    while( count > 0U )
    {
        count--;
        prvAppendChar( buffer, buffer_size, used, digits[ count ] );
    }
}

static void prvAppendSigned( char * buffer,
                             size_t buffer_size,
                             size_t * used,
                             long value,
                             unsigned width,
                             bool zero_pad )
{
    if( value < 0 )
    {
        prvAppendChar( buffer, buffer_size, used, '-' );
        prvAppendUnsigned( buffer, buffer_size, used, ( unsigned long ) ( -value ), 10U, width, zero_pad );
    }
    else
    {
        prvAppendUnsigned( buffer, buffer_size, used, ( unsigned long ) value, 10U, width, zero_pad );
    }
}

void console_init( void )
{
    xConsoleMutex = xSemaphoreCreateMutexStatic( &xConsoleMutexBuffer );
    xConsoleInputHandle = semihost_open( ":tt", 0 );
}

extern int xLogFd;

static void prvWriteBuffer( const char * buffer )
{
    if( xConsoleMutex != NULL )
    {
        xSemaphoreTake( xConsoleMutex, portMAX_DELAY );
        semihost_write0( buffer );
        if( xLogFd >= 0 )
        {
            size_t len = 0;
            while( buffer[ len ] ) len++;
            semihost_write( xLogFd, buffer, len );
        }
        xSemaphoreGive( xConsoleMutex );
    }
    else
    {
        semihost_write0( buffer );
    }
}

void console_writeln( const char * text )
{
    char buffer[ 256 ];
    size_t used = 0U;

    prvAppendString( buffer, sizeof( buffer ), &used, text );
    prvAppendChar( buffer, sizeof( buffer ), &used, '\n' );
    prvWriteBuffer( buffer );
}

void console_writef( const char * fmt, ... )
{
    char buffer[ 256 ];
    size_t used = 0U;
    va_list ap;

    va_start( ap, fmt );

    for( ; *fmt != '\0'; fmt++ )
    {
        if( *fmt != '%' )
        {
            prvAppendChar( buffer, sizeof( buffer ), &used, *fmt );
            continue;
        }

        fmt++;
        bool zero_pad = false;
        unsigned width = 0U;

        if( *fmt == '0' )
        {
            zero_pad = true;
            fmt++;
        }

        while( ( *fmt >= '0' ) && ( *fmt <= '9' ) )
        {
            width = ( width * 10U ) + ( unsigned ) ( *fmt - '0' );
            fmt++;
        }

        bool long_value = false;
        if( *fmt == 'l' )
        {
            long_value = true;
            fmt++;
        }

        switch( *fmt )
        {
            case '%':
                prvAppendChar( buffer, sizeof( buffer ), &used, '%' );
                break;

            case 's':
                prvAppendString( buffer, sizeof( buffer ), &used, va_arg( ap, const char * ) );
                break;

            case 'c':
                prvAppendChar( buffer, sizeof( buffer ), &used, ( char ) va_arg( ap, int ) );
                break;

            case 'u':
                if( long_value )
                {
                    prvAppendUnsigned( buffer, sizeof( buffer ), &used, va_arg( ap, unsigned long ), 10U, width, zero_pad );
                }
                else
                {
                    prvAppendUnsigned( buffer, sizeof( buffer ), &used, ( unsigned long ) va_arg( ap, unsigned int ), 10U, width, zero_pad );
                }
                break;

            case 'd':
                if( long_value )
                {
                    prvAppendSigned( buffer, sizeof( buffer ), &used, va_arg( ap, long ), width, zero_pad );
                }
                else
                {
                    prvAppendSigned( buffer, sizeof( buffer ), &used, ( long ) va_arg( ap, int ), width, zero_pad );
                }
                break;

            case 'x':
                if( long_value )
                {
                    prvAppendUnsigned( buffer, sizeof( buffer ), &used, va_arg( ap, unsigned long ), 16U, width, zero_pad );
                }
                else
                {
                    prvAppendUnsigned( buffer, sizeof( buffer ), &used, ( unsigned long ) va_arg( ap, unsigned int ), 16U, width, zero_pad );
                }
                break;

            default:
                prvAppendChar( buffer, sizeof( buffer ), &used, '%' );
                prvAppendChar( buffer, sizeof( buffer ), &used, *fmt );
                break;
        }
    }

    va_end( ap );
    prvWriteBuffer( buffer );
}

bool console_readline( char * buffer, size_t buffer_size )
{
    if( ( buffer == NULL ) || ( buffer_size == 0U ) )
    {
        return false;
    }

    if( xConsoleMutex != NULL )
    {
        xSemaphoreTake( xConsoleMutex, portMAX_DELAY );
    }

    semihost_write0( "ecu> " );

    size_t used = 0U;
    for( ;; )
    {
        char c = '\0';
        int remaining;

        if( xConsoleInputHandle < 0 )
        {
            if( xConsoleMutex != NULL )
            {
                xSemaphoreGive( xConsoleMutex );
            }

            return false;
        }

        remaining = semihost_read( xConsoleInputHandle, &c, sizeof( c ) );

        if( remaining != 0 )
        {
            if( xConsoleMutex != NULL )
            {
                xSemaphoreGive( xConsoleMutex );
            }

            return false;
        }

        if( ( c == '\r' ) || ( c == '\n' ) )
        {
            semihost_write0( "\n" );
            break;
        }

        if( used + 1U < buffer_size )
        {
            buffer[ used++ ] = ( char ) c;
            buffer[ used ] = '\0';
        }

        char echo[ 2 ] = { ( char ) c, '\0' };
        semihost_write0( echo );
    }

    if( xConsoleMutex != NULL )
    {
        xSemaphoreGive( xConsoleMutex );
    }

    return true;
}
