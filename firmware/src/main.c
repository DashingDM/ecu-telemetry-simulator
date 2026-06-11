#include "firmware.h"
#include "semihost.h"

#include <stdlib.h>
#include <stdbool.h>
#include <string.h>

typedef struct
{
    StaticQueue_t sensor_queue_buffer;
    uint8_t sensor_queue_storage[ 6 * sizeof( SensorSample ) ] __attribute__( ( aligned( 8 ) ) );

    StaticQueue_t telemetry_queue_buffer;
    uint8_t telemetry_queue_storage[ 6 * sizeof( TelemetryFrame ) ] __attribute__( ( aligned( 8 ) ) );

    StaticSemaphore_t sensor_kick_buffer;
    SemaphoreHandle_t sensor_kick;

    StaticEventGroup_t heartbeat_buffer;
    EventGroupHandle_t heartbeat_events;

    StaticTimer_t sensor_timer_buffer;
    TimerHandle_t sensor_timer;

    StaticSemaphore_t state_mutex_buffer;
    SemaphoreHandle_t state_mutex;
} AppObjects;

typedef struct
{
    StaticTask_t tcb;
    StackType_t stack[ 192 ];
} TaskSlot;

static AppObjects xAppObjects;
static TaskSlot xSensorTask;
static TaskSlot xProcessorTask;
static TaskSlot xLoggerTask;
static TaskSlot xWatchdogTask;
static TaskSlot xDiagnosticsTask;

static QueueHandle_t xSensorQueue;
static QueueHandle_t xTelemetryQueue;
static AppStats xStats;

static TaskHandle_t xSensorTaskHandle;
static TaskHandle_t xProcessorTaskHandle;
static TaskHandle_t xLoggerTaskHandle;
static TaskHandle_t xWatchdogTaskHandle;
static TaskHandle_t xDiagnosticsTaskHandle;

enum
{
    EVT_SENSOR    = ( 1U << 0 ),
    EVT_PROCESSOR = ( 1U << 1 ),
    EVT_LOGGER    = ( 1U << 2 )
};

/* --------------------------------------------------------------------------
 * Mutex helpers
 * -------------------------------------------------------------------------- */

static void prvSnapshotLock( void )
{
    xSemaphoreTake( xAppObjects.state_mutex, portMAX_DELAY );
}

static void prvSnapshotUnlock( void )
{
    xSemaphoreGive( xAppObjects.state_mutex );
}

static FaultMode prvGetFaultMode( void )
{
    FaultMode mode;

    prvSnapshotLock();
    mode = xStats.fault_mode;
    prvSnapshotUnlock();
    return mode;
}

static void prvIncrementCounter( uint32_t * counter )
{
    prvSnapshotLock();
    *counter += 1U;
    prvSnapshotUnlock();
}

static void prvResetStats( void )
{
    prvSnapshotLock();
    memset( &xStats, 0, sizeof( xStats ) );
    xStats.fault_mode = FAULT_NONE;
    prvSnapshotUnlock();

    xQueueReset( xSensorQueue );
    xQueueReset( xTelemetryQueue );
    xEventGroupClearBits( xAppObjects.heartbeat_events, EVT_SENSOR | EVT_PROCESSOR | EVT_LOGGER );
}

static const char * prvFaultName( FaultMode mode )
{
    switch( mode )
    {
        case FAULT_OVERFLOW:
            return "overflow";

        case FAULT_SENSOR:
            return "sensor";

        case FAULT_STALL:
            return "stall";

        default:
            return "none";
    }
}

/* --------------------------------------------------------------------------
 * Sensor data generation (3-axis accel via LCG, temperature sawtooth)
 * -------------------------------------------------------------------------- */

static uint32_t prvLcgNext( uint32_t state )
{
    return state * 1664525UL + 1013904223UL;
}

static SensorSample prvMakeSample( uint32_t seq )
{
    FaultMode mode = prvGetFaultMode();

    /* LCG seeded from sequence for reproducible per-axis values */
    uint32_t lcg = prvLcgNext( seq + 1UL );
    int16_t ax = ( int16_t ) ( ( int32_t ) ( lcg & 0xFFU ) - 128 );
    lcg = prvLcgNext( lcg );
    int16_t ay = ( int16_t ) ( ( int32_t ) ( lcg & 0xFFU ) - 128 );
    lcg = prvLcgNext( lcg );
    int16_t az = ( int16_t ) ( 100 + ( int32_t ) ( lcg & 0x3FU ) );

    SensorSample sample =
    {
        .sequence          = seq,
        .temperature_c_x10 = ( int16_t ) ( 720 + ( ( int32_t ) ( seq % 30U ) - 15 ) * 6 ),
        .accel_x_x100      = ax,
        .accel_y_x100      = ay,
        .accel_z_x100      = az,
        .valid             = true,
        .tick              = xTaskGetTickCount()
    };

    if( mode == FAULT_SENSOR )
    {
        sample.temperature_c_x10 = 1550;
        sample.accel_x_x100 = 420;
        sample.accel_y_x100 = 420;
        sample.accel_z_x100 = 420;
        sample.valid = false;
    }

    return sample;
}

/* --------------------------------------------------------------------------
 * Processing: derive RPM, throttle, speed from sensor sample
 * -------------------------------------------------------------------------- */

static uint16_t prvAccelMagnitude( const SensorSample * s )
{
    /* Integer magnitude approximation: max(|ax|,|ay|,|az|) + 3/8 * min-sum */
    int32_t ax = s->accel_x_x100 < 0 ? -s->accel_x_x100 : s->accel_x_x100;
    int32_t ay = s->accel_y_x100 < 0 ? -s->accel_y_x100 : s->accel_y_x100;
    int32_t az = s->accel_z_x100 < 0 ? -s->accel_z_x100 : s->accel_z_x100;
    int32_t mag = ( ax + ay + az ) / 3;

    if( mag < 0 )
    {
        mag = 0;
    }

    return ( uint16_t ) mag;
}

static TelemetryFrame prvProcessSample( const SensorSample * sample )
{
    uint16_t accel_mag = prvAccelMagnitude( sample );

    uint16_t rpm = ( uint16_t ) ( 700U
                                  + ( ( uint32_t ) sample->temperature_c_x10 / 2U )
                                  + ( ( uint32_t ) accel_mag * 3U ) );

    uint16_t throttle = ( uint16_t ) ( 120U + ( ( uint32_t ) accel_mag / 2U ) );

    if( throttle > 1000U )
    {
        throttle = 1000U;
    }

    uint16_t speed = ( uint16_t ) ( ( uint32_t ) accel_mag * 2U );

    if( speed > 2500U )
    {
        speed = 2500U;
    }

    TelemetryFrame frame =
    {
        .sequence          = sample->sequence,
        .temperature_c_x10 = sample->temperature_c_x10,
        .accel_x_x100      = sample->accel_x_x100,
        .accel_y_x100      = sample->accel_y_x100,
        .accel_z_x100      = sample->accel_z_x100,
        .rpm               = rpm,
        .throttle_pct_x10  = throttle,
        .speed_kmh_x10     = speed,
        .valid             = sample->valid,
        .tick              = xTaskGetTickCount()
    };

    return frame;
}

static int16_t prvAbs16( int16_t v )
{
    return v < 0 ? ( int16_t ) ( -v ) : v;
}

static void prvPrintFrame( const TelemetryFrame * frame )
{
    console_writef(
        "[telemetry] seq=%lu temp=%d.%dC ax=%d.%02d ay=%d.%02d az=%d.%02d spd=%u.%ukm/h rpm=%u thr=%u.%u%% valid=%s tick=%lu\n",
        ( unsigned long ) frame->sequence,
        ( int ) ( frame->temperature_c_x10 / 10 ),
        ( int ) ( frame->temperature_c_x10 < 0 ? ( -frame->temperature_c_x10 ) % 10 : frame->temperature_c_x10 % 10 ),
        ( int ) ( frame->accel_x_x100 / 100 ),
        ( int ) prvAbs16( ( int16_t ) ( frame->accel_x_x100 % 100 ) ),
        ( int ) ( frame->accel_y_x100 / 100 ),
        ( int ) prvAbs16( ( int16_t ) ( frame->accel_y_x100 % 100 ) ),
        ( int ) ( frame->accel_z_x100 / 100 ),
        ( int ) prvAbs16( ( int16_t ) ( frame->accel_z_x100 % 100 ) ),
        ( unsigned int ) ( frame->speed_kmh_x10 / 10 ),
        ( unsigned int ) ( frame->speed_kmh_x10 % 10 ),
        ( unsigned int ) frame->rpm,
        ( unsigned int ) ( frame->throttle_pct_x10 / 10 ),
        ( unsigned int ) ( frame->throttle_pct_x10 % 10 ),
        frame->valid ? "yes" : "no",
        ( unsigned long ) frame->tick );
}

/* --------------------------------------------------------------------------
 * Timer callback
 * -------------------------------------------------------------------------- */

static void prvSensorTimerCallback( TimerHandle_t xTimer )
{
    ( void ) xTimer;
    ( void ) xSemaphoreGive( xAppObjects.sensor_kick );
}

/* --------------------------------------------------------------------------
 * Stat helpers
 * -------------------------------------------------------------------------- */

static void prvRecordHeartbeat( EventBits_t bit, uint32_t * counter )
{
    prvIncrementCounter( counter );
    xEventGroupSetBits( xAppObjects.heartbeat_events, bit );
}

static void prvUpdateStatsFromSample( const SensorSample * sample )
{
    prvSnapshotLock();
    xStats.sensor_samples += 1U;
    xStats.last_sample = *sample;
    prvSnapshotUnlock();
}

static void prvUpdateStatsFromFrame( const TelemetryFrame * frame )
{
    prvSnapshotLock();
    xStats.telemetry_frames += 1U;
    xStats.last_frame = *frame;
    prvSnapshotUnlock();
}

static void prvIncrementDrop( bool sensor_queue )
{
    prvSnapshotLock();
    if( sensor_queue )
    {
        xStats.sensor_drops += 1U;
    }
    else
    {
        xStats.telemetry_drops += 1U;
    }
    prvSnapshotUnlock();
}

/* --------------------------------------------------------------------------
 * Tasks
 * -------------------------------------------------------------------------- */

static void prvSensorTask( void * pvParameters )
{
    ( void ) pvParameters;
    uint32_t sequence = 0U;

    for( ;; )
    {
        xSemaphoreTake( xAppObjects.sensor_kick, portMAX_DELAY );

        prvRecordHeartbeat( EVT_SENSOR, &xStats.task_sensor_beats );

        if( prvGetFaultMode() == FAULT_OVERFLOW )
        {
            for( int burst = 0; burst < 3; ++burst )
            {
                SensorSample sample = prvMakeSample( ++sequence );
                if( xQueueSend( xSensorQueue, &sample, 0 ) != pdTRUE )
                {
                    prvIncrementDrop( true );
                }
                else
                {
                    prvUpdateStatsFromSample( &sample );
                }
            }
            continue;
        }

        SensorSample sample = prvMakeSample( ++sequence );
        if( xQueueSend( xSensorQueue, &sample, 0 ) != pdTRUE )
        {
            prvIncrementDrop( true );
        }
        else
        {
            prvUpdateStatsFromSample( &sample );
        }
    }
}

static void prvProcessorTask( void * pvParameters )
{
    ( void ) pvParameters;
    SensorSample sample;

    for( ;; )
    {
        if( xQueueReceive( xSensorQueue, &sample, portMAX_DELAY ) == pdTRUE )
        {
            prvRecordHeartbeat( EVT_PROCESSOR, &xStats.task_processor_beats );

            if( sample.valid == false )
            {
                prvIncrementCounter( &xStats.sensor_faults );
            }

            if( ( prvGetFaultMode() == FAULT_STALL ) && ( ( sample.sequence % 6U ) == 0U ) )
            {
                console_writef( "[processor] forced stall at sample %lu\n", ( unsigned long ) sample.sequence );
                vTaskDelay( pdMS_TO_TICKS( 450 ) );
            }

            TelemetryFrame frame = prvProcessSample( &sample );
            if( xQueueSend( xTelemetryQueue, &frame, 0 ) != pdTRUE )
            {
                prvIncrementDrop( false );
            }
            else
            {
                prvUpdateStatsFromFrame( &frame );
            }
        }
    }
}

static void prvLoggerTask( void * pvParameters )
{
    ( void ) pvParameters;
    TelemetryFrame frame;

    for( ;; )
    {
        if( xQueueReceive( xTelemetryQueue, &frame, portMAX_DELAY ) == pdTRUE )
        {
            prvRecordHeartbeat( EVT_LOGGER, &xStats.task_logger_beats );
            prvPrintFrame( &frame );
        }
    }
}

static void prvWatchdogTask( void * pvParameters )
{
    ( void ) pvParameters;

    for( ;; )
    {
        EventBits_t bits = xEventGroupWaitBits(
            xAppObjects.heartbeat_events,
            EVT_SENSOR | EVT_PROCESSOR | EVT_LOGGER,
            pdTRUE,
            pdTRUE,
            pdMS_TO_TICKS( 1000 ) );

        if( bits == ( EVT_SENSOR | EVT_PROCESSOR | EVT_LOGGER ) )
        {
            console_writef(
                "[watchdog] healthy: sensor=%lu processor=%lu logger=%lu\n",
                ( unsigned long ) xStats.task_sensor_beats,
                ( unsigned long ) xStats.task_processor_beats,
                ( unsigned long ) xStats.task_logger_beats );
        }
        else
        {
            prvSnapshotLock();
            xStats.watchdog_warnings += 1U;
            prvSnapshotUnlock();
            console_writef( "[watchdog] warning bits=0x%lx\n", ( unsigned long ) bits );
        }
    }
}

/* --------------------------------------------------------------------------
 * Diagnostics command handler
 * -------------------------------------------------------------------------- */

static void prvPrintStatus( void )
{
    AppStats snapshot;

    prvSnapshotLock();
    snapshot = xStats;
    prvSnapshotUnlock();

    console_writef( "fault mode: %s\n", prvFaultName( snapshot.fault_mode ) );
    console_writef( "samples in: %lu\n", ( unsigned long ) snapshot.sensor_samples );
    console_writef( "frames out: %lu\n", ( unsigned long ) snapshot.telemetry_frames );
    console_writef( "sensor drops: %lu\n", ( unsigned long ) snapshot.sensor_drops );
    console_writef( "telemetry drops: %lu\n", ( unsigned long ) snapshot.telemetry_drops );
    console_writef( "sensor faults: %lu\n", ( unsigned long ) snapshot.sensor_faults );
    console_writef( "watchdog warnings: %lu\n", ( unsigned long ) snapshot.watchdog_warnings );
    console_writef( "queue depth: sensor=%u telemetry=%u\n",
                    ( unsigned int ) uxQueueMessagesWaiting( xSensorQueue ),
                    ( unsigned int ) uxQueueMessagesWaiting( xTelemetryQueue ) );
    console_writef(
        "latest sample: seq=%lu temp=%d.%dC ax=%d ay=%d az=%d valid=%s\n",
        ( unsigned long ) snapshot.last_sample.sequence,
        ( int ) ( snapshot.last_sample.temperature_c_x10 / 10 ),
        ( int ) ( snapshot.last_sample.temperature_c_x10 < 0
                      ? ( -snapshot.last_sample.temperature_c_x10 ) % 10
                      : snapshot.last_sample.temperature_c_x10 % 10 ),
        ( int ) snapshot.last_sample.accel_x_x100,
        ( int ) snapshot.last_sample.accel_y_x100,
        ( int ) snapshot.last_sample.accel_z_x100,
        snapshot.last_sample.valid ? "yes" : "no" );
    console_writef(
        "latest frame: seq=%lu rpm=%u thr=%u.%u%% spd=%u.%u valid=%s\n",
        ( unsigned long ) snapshot.last_frame.sequence,
        ( unsigned int ) snapshot.last_frame.rpm,
        ( unsigned int ) ( snapshot.last_frame.throttle_pct_x10 / 10 ),
        ( unsigned int ) ( snapshot.last_frame.throttle_pct_x10 % 10 ),
        ( unsigned int ) ( snapshot.last_frame.speed_kmh_x10 / 10 ),
        ( unsigned int ) ( snapshot.last_frame.speed_kmh_x10 % 10 ),
        snapshot.last_frame.valid ? "yes" : "no" );
}

static void prvPrintTasks( void )
{
    AppStats snapshot;

    prvSnapshotLock();
    snapshot = xStats;
    prvSnapshotUnlock();

    console_writef( "sensor beats=%lu stack=%u\n",
                    ( unsigned long ) snapshot.task_sensor_beats,
                    ( unsigned int ) uxTaskGetStackHighWaterMark( xSensorTaskHandle ) );
    console_writef( "processor beats=%lu stack=%u\n",
                    ( unsigned long ) snapshot.task_processor_beats,
                    ( unsigned int ) uxTaskGetStackHighWaterMark( xProcessorTaskHandle ) );
    console_writef( "logger beats=%lu stack=%u\n",
                    ( unsigned long ) snapshot.task_logger_beats,
                    ( unsigned int ) uxTaskGetStackHighWaterMark( xLoggerTaskHandle ) );
    console_writef( "watchdog stack=%u\n",
                    ( unsigned int ) uxTaskGetStackHighWaterMark( xWatchdogTaskHandle ) );
    console_writef( "diagnostics stack=%u\n",
                    ( unsigned int ) uxTaskGetStackHighWaterMark( xDiagnosticsTaskHandle ) );
}

static void prvPrintHeap( void )
{
    size_t footprint = sizeof( xAppObjects )
                       + sizeof( xSensorTask )
                       + sizeof( xProcessorTask )
                       + sizeof( xLoggerTask )
                       + sizeof( xWatchdogTask )
                       + sizeof( xDiagnosticsTask )
                       + sizeof( xStats );

    console_writef( "static footprint approx %u bytes\n", ( unsigned int ) footprint );
    console_writeln( "dynamic heap is disabled in this firmware build" );
}

static void prvPrintStats( void )
{
    console_writef( "sensor queue used=%u / 6\n", ( unsigned int ) uxQueueMessagesWaiting( xSensorQueue ) );
    console_writef( "telemetry queue used=%u / 6\n", ( unsigned int ) uxQueueMessagesWaiting( xTelemetryQueue ) );
    console_writef( "sensor samples=%lu telemetry frames=%lu\n",
                    ( unsigned long ) xStats.sensor_samples,
                    ( unsigned long ) xStats.telemetry_frames );
    console_writef( "drops sensor=%lu telemetry=%lu\n",
                    ( unsigned long ) xStats.sensor_drops,
                    ( unsigned long ) xStats.telemetry_drops );
}

static void prvSetFault( FaultMode mode )
{
    prvSnapshotLock();
    xStats.fault_mode = mode;
    prvSnapshotUnlock();
    console_writef( "fault mode set to %s\n", prvFaultName( mode ) );
}

static void prvHandleCommand( char * line )
{
    for( char * p = line; *p != '\0'; ++p )
    {
        if( ( *p >= 'A' ) && ( *p <= 'Z' ) )
        {
            *p = ( char ) ( *p - 'A' + 'a' );
        }
    }

    if( strcmp( line, "help" ) == 0 )
    {
        console_writeln( "commands: status tasks heap stats fault none fault overflow fault sensor fault stall reset quit" );
    }
    else if( strcmp( line, "status" ) == 0 )
    {
        prvPrintStatus();
    }
    else if( strcmp( line, "tasks" ) == 0 )
    {
        prvPrintTasks();
    }
    else if( strcmp( line, "heap" ) == 0 )
    {
        prvPrintHeap();
    }
    else if( strcmp( line, "stats" ) == 0 )
    {
        prvPrintStats();
    }
    else if( strcmp( line, "reset" ) == 0 )
    {
        prvResetStats();
        console_writeln( "state reset" );
    }
    else if( strcmp( line, "fault none" ) == 0 )
    {
        prvSetFault( FAULT_NONE );
    }
    else if( strcmp( line, "fault overflow" ) == 0 )
    {
        prvSetFault( FAULT_OVERFLOW );
    }
    else if( strcmp( line, "fault sensor" ) == 0 )
    {
        prvSetFault( FAULT_SENSOR );
    }
    else if( strcmp( line, "fault stall" ) == 0 )
    {
        prvSetFault( FAULT_STALL );
    }
    else
    {
        console_writeln( "unknown command, type help" );
    }
}

int xLogFd = -1;

static void prvLogWrite( const char * text )
{
    semihost_write0( text );
    if( xLogFd >= 0 )
    {
        size_t len = 0;
        while( text[ len ] ) len++;
        semihost_write( xLogFd, text, len );
    }
}

static void prvDiagnosticsTask( void * pvParameters )
{
    ( void ) pvParameters;

    vTaskDelay( pdMS_TO_TICKS( 1500 ) );

    xLogFd = semihost_open( "firmware_commands.txt", 4 );

    prvLogWrite( "=== SELF-TEST BEGIN ===\n" );

    static const char * const cmds[] = {
        "status", "tasks", "heap", "stats", "help",
        "fault sensor", "status",
        "fault overflow", "stats",
        "fault stall",   "status",
        "fault none",    "status",
        "reset",         "status",
        NULL
    };

    for( int i = 0; cmds[ i ] != NULL; i++ )
    {
        char buf[ 32 ];
        size_t j = 0;
        while( cmds[ i ][ j ] && j < sizeof( buf ) - 1U ) { buf[ j ] = cmds[ i ][ j ]; j++; }
        buf[ j ] = '\0';
        prvLogWrite( "==> " );
        prvLogWrite( buf );
        prvLogWrite( "\n" );
        prvHandleCommand( buf );
        vTaskDelay( pdMS_TO_TICKS( 100 ) );
    }

    prvLogWrite( "=== SELF-TEST END ===\n" );
    if( xLogFd >= 0 ) semihost_close( xLogFd );
    exit( 0 );
}

static void prvCreateTasks( void )
{
    xSensorTaskHandle = xTaskCreateStatic(
        prvSensorTask,
        "sensor",
        sizeof( xSensorTask.stack ) / sizeof( xSensorTask.stack[ 0 ] ),
        NULL,
        tskIDLE_PRIORITY + 3,
        xSensorTask.stack,
        &xSensorTask.tcb );

    xProcessorTaskHandle = xTaskCreateStatic(
        prvProcessorTask,
        "process",
        sizeof( xProcessorTask.stack ) / sizeof( xProcessorTask.stack[ 0 ] ),
        NULL,
        tskIDLE_PRIORITY + 2,
        xProcessorTask.stack,
        &xProcessorTask.tcb );

    xLoggerTaskHandle = xTaskCreateStatic(
        prvLoggerTask,
        "logger",
        sizeof( xLoggerTask.stack ) / sizeof( xLoggerTask.stack[ 0 ] ),
        NULL,
        tskIDLE_PRIORITY + 1,
        xLoggerTask.stack,
        &xLoggerTask.tcb );

    xWatchdogTaskHandle = xTaskCreateStatic(
        prvWatchdogTask,
        "watchdog",
        sizeof( xWatchdogTask.stack ) / sizeof( xWatchdogTask.stack[ 0 ] ),
        NULL,
        tskIDLE_PRIORITY + 2,
        xWatchdogTask.stack,
        &xWatchdogTask.tcb );

    xDiagnosticsTaskHandle = xTaskCreateStatic(
        prvDiagnosticsTask,
        "diag",
        sizeof( xDiagnosticsTask.stack ) / sizeof( xDiagnosticsTask.stack[ 0 ] ),
        NULL,
        tskIDLE_PRIORITY + 1,
        xDiagnosticsTask.stack,
        &xDiagnosticsTask.tcb );
}

int main( void )
{
    console_init();

    xAppObjects.sensor_kick = xSemaphoreCreateBinaryStatic( &xAppObjects.sensor_kick_buffer );
    xAppObjects.heartbeat_events = xEventGroupCreateStatic( &xAppObjects.heartbeat_buffer );
    xAppObjects.sensor_timer = xTimerCreateStatic(
        "sensor",
        pdMS_TO_TICKS( 100 ),
        pdTRUE,
        NULL,
        prvSensorTimerCallback,
        &xAppObjects.sensor_timer_buffer );
    xAppObjects.state_mutex = xSemaphoreCreateMutexStatic( &xAppObjects.state_mutex_buffer );

    xSensorQueue = xQueueCreateStatic(
        6,
        sizeof( SensorSample ),
        xAppObjects.sensor_queue_storage,
        &xAppObjects.sensor_queue_buffer );

    xTelemetryQueue = xQueueCreateStatic(
        6,
        sizeof( TelemetryFrame ),
        xAppObjects.telemetry_queue_storage,
        &xAppObjects.telemetry_queue_buffer );

    prvResetStats();
    prvCreateTasks();

    xTimerStart( xAppObjects.sensor_timer, 0 );

    console_writeln( "real-time vehicle telemetry ECU simulator" );
    console_writeln( "target: STM32VLDISCOVERY / FreeRTOS / QEMU" );
    console_writeln( "type help for commands" );

    vTaskStartScheduler();

    for( ;; )
    {
        ;
    }
}
