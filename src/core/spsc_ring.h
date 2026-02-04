#pragma once

#include "config.h"
#include <array>
#include <atomic>
#include <cstdio>

// Multiply by 4 since buffer size is in 32-bit words.
// While we want to know how many bytes we receive.
#define SLAB_BYTES (RX_BUFFER_SIZE * 4)
#define SLAB_COUNT 16
#define FIFO_CAPACITY (SLAB_COUNT + 1)

struct RxSlab {
    // This array should be populated so that all odd indexes are from I channel
    // and all even indexes are from Q channel.
    int16_t data[SLAB_BYTES / 2];
    size_t len = 0;
    uint64_t seq = 0;
};

struct RxRingBuffer {
    RxSlab *slabs[FIFO_CAPACITY];
    // Consumer
    std::atomic<size_t> head = 0;
    // Producer
    std::atomic<size_t> tail = 0;
};

size_t inc(size_t i);

// Producer only
bool fifo_push(RxRingBuffer &q, RxSlab *s);

// Consumer only
bool fifo_pop(RxRingBuffer &q, RxSlab *&out);
