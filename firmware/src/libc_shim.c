#include "string.h"

void * memcpy( void * dest, const void * src, size_t n )
{
    unsigned char * d = ( unsigned char * ) dest;
    const unsigned char * s = ( const unsigned char * ) src;

    for( size_t i = 0U; i < n; i++ )
    {
        d[ i ] = s[ i ];
    }

    return dest;
}

void * memset( void * dest, int c, size_t n )
{
    unsigned char * d = ( unsigned char * ) dest;

    for( size_t i = 0U; i < n; i++ )
    {
        d[ i ] = ( unsigned char ) c;
    }

    return dest;
}

int memcmp( const void * s1, const void * s2, size_t n )
{
    const unsigned char * a = ( const unsigned char * ) s1;
    const unsigned char * b = ( const unsigned char * ) s2;

    for( size_t i = 0U; i < n; i++ )
    {
        if( a[ i ] != b[ i ] )
        {
            return ( int ) a[ i ] - ( int ) b[ i ];
        }
    }

    return 0;
}

size_t strlen( const char * s )
{
    size_t len = 0U;

    while( ( s != NULL ) && ( s[ len ] != '\0' ) )
    {
        len++;
    }

    return len;
}

int strcmp( const char * a, const char * b )
{
    while( ( *a != '\0' ) && ( *a == *b ) )
    {
        a++;
        b++;
    }

    return ( unsigned char ) *a - ( unsigned char ) *b;
}

size_t strcspn( const char * s, const char * reject )
{
    size_t count = 0U;

    for( ; s[ count ] != '\0'; count++ )
    {
        for( const char * r = reject; *r != '\0'; r++ )
        {
            if( s[ count ] == *r )
            {
                return count;
            }
        }
    }

    return count;
}
