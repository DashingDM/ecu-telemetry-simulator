#define _POSIX_C_SOURCE 200809L

#include "ecu_sim.h"

#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

struct MsgQueue {
    char name[32];
    size_t item_size;
    size_t capacity;
    size_t head;
    size_t tail;
    size_t count;
    unsigned char *storage;
    pthread_mutex_t mutex;
    pthread_cond_t not_empty;
    pthread_cond_t not_full;
};

static struct timespec deadline_from_now_ms(int timeout_ms)
{
    struct timespec now;
    clock_gettime(CLOCK_REALTIME, &now);
    now.tv_sec  += timeout_ms / 1000;
    now.tv_nsec += (long)(timeout_ms % 1000) * 1000000L;
    if (now.tv_nsec >= 1000000000L) {
        now.tv_sec  += 1;
        now.tv_nsec -= 1000000000L;
    }
    return now;
}

MsgQueue *queue_create(const char *name, size_t item_size, size_t capacity)
{
    if (item_size == 0 || capacity == 0)
        return NULL;

    MsgQueue *queue = calloc(1, sizeof(*queue));
    if (!queue)
        return NULL;

    queue->storage = calloc(capacity, item_size);
    if (!queue->storage) {
        free(queue);
        return NULL;
    }

    queue->item_size = item_size;
    queue->capacity  = capacity;
    snprintf(queue->name, sizeof(queue->name), "%s", name ? name : "queue");

    if (pthread_mutex_init(&queue->mutex, NULL) != 0 ||
        pthread_cond_init(&queue->not_empty, NULL) != 0 ||
        pthread_cond_init(&queue->not_full, NULL) != 0) {
        queue_destroy(queue);
        return NULL;
    }

    return queue;
}

void queue_destroy(MsgQueue *queue)
{
    if (!queue)
        return;
    pthread_cond_destroy(&queue->not_empty);
    pthread_cond_destroy(&queue->not_full);
    pthread_mutex_destroy(&queue->mutex);
    free(queue->storage);
    free(queue);
}

bool queue_push(MsgQueue *queue, const void *item)
{
    if (!queue || !item)
        return false;

    bool pushed = false;
    pthread_mutex_lock(&queue->mutex);
    if (queue->count < queue->capacity) {
        memcpy(queue->storage + (queue->tail * queue->item_size), item, queue->item_size);
        queue->tail = (queue->tail + 1) % queue->capacity;
        queue->count++;
        pushed = true;
        pthread_cond_signal(&queue->not_empty);
    }
    pthread_mutex_unlock(&queue->mutex);
    return pushed;
}

bool queue_pop(MsgQueue *queue, void *item, int timeout_ms)
{
    if (!queue || !item)
        return false;

    pthread_mutex_lock(&queue->mutex);

    while (queue->count == 0) {
        if (timeout_ms < 0) {
            pthread_cond_wait(&queue->not_empty, &queue->mutex);
            continue;
        }
        struct timespec deadline = deadline_from_now_ms(timeout_ms);
        int rc = pthread_cond_timedwait(&queue->not_empty, &queue->mutex, &deadline);
        if (rc == ETIMEDOUT) {
            pthread_mutex_unlock(&queue->mutex);
            return false;
        }
    }

    memcpy(item, queue->storage + (queue->head * queue->item_size), queue->item_size);
    queue->head = (queue->head + 1) % queue->capacity;
    queue->count--;
    pthread_cond_signal(&queue->not_full);
    pthread_mutex_unlock(&queue->mutex);
    return true;
}

size_t queue_count(const MsgQueue *queue)
{
    if (!queue)
        return 0;
    pthread_mutex_lock((pthread_mutex_t *)&queue->mutex);
    size_t count = queue->count;
    pthread_mutex_unlock((pthread_mutex_t *)&queue->mutex);
    return count;
}

size_t queue_capacity(const MsgQueue *queue)
{
    return queue ? queue->capacity : 0;
}

const char *queue_name(const MsgQueue *queue)
{
    return queue ? queue->name : "";
}

void queue_clear(MsgQueue *queue)
{
    if (!queue)
        return;
    pthread_mutex_lock(&queue->mutex);
    queue->head  = 0;
    queue->tail  = 0;
    queue->count = 0;
    pthread_cond_broadcast(&queue->not_full);
    pthread_mutex_unlock(&queue->mutex);
}
