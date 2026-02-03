
#include "spsc_ring.h"
#include <atomic>

size_t inc(size_t i) { return (i + 1 == FIFO_CAPACITY) ? 0 : i + 1; }

bool fifo_push(RxRingBuffer &q, RxSlab *s) {
    const size_t t = q.tail.load(std::memory_order_relaxed);
    const size_t next = inc(t);
    const size_t h = q.head.load(std::memory_order_acquire);

    if (next == h) {
        return false; // Fifo is full
    }

    q.slabs[t] = s;
    q.tail.store(next, std::memory_order_release);
    return true;
}

bool fifo_pop(RxRingBuffer &q, RxSlab *&out) {
    const size_t h = q.head.load(std::memory_order_relaxed);
    const size_t t = q.tail.load(std::memory_order_acquire);
    if (h == t) {
        return false; // Fifo is empty
    }

    out = q.slabs[h];
    q.head.store(inc(h), std::memory_order_release);
    return true;
}
