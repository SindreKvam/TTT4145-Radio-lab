#pragma once

#include "config.h"
#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>

// Multiply by 4 since buffer size is in 32-bit words.
// While we want to know how many bytes we receive.
#define SLAB_BYTES (RX_BUFFER_SIZE * 4)
#define SLAB_COUNT 16
#define GUI_SLAB_COUNT 4

struct RxSlab {
    // This array should be populated so that all odd indexes are from I channel
    // and all even indexes are from Q channel.
    int16_t data[SLAB_BYTES / 2];
    size_t len = 0;
    uint64_t seq = 0;
};

/**
 * @brief SPSCRingBuffer is a template class for Single-Producer Single-Consumer
 * lock-free queue.
 *
 * There should be made two instances of this Buffer. One that should be filled
 * with empty buffers ready to be used, and one filled with full buffers, ready
 * to be processed.
 *
 * @tparam T The type of elements stored in the queue.
 * @tparam Capacity The maximum number of elements the queue can hold.
 */
template <typename T, size_t Capacity> class SPSCRingBuffer {
  public:
    // Add an extra capacity internally, so that when attempting to push a new
    // item when full, the increment function will still increase to the same
    // value as the head, instead of rotating back to index 0.
    static constexpr size_t RealCapacity = Capacity + 1;

    SPSCRingBuffer() : head_(0), tail_(0) {}

    template <typename U, size_t N>
    SPSCRingBuffer(U (&storage)[N] /* Template array reference */)
        : head_(0), tail_(0) {
        static_assert(N <= Capacity, "Storage array exceeds buffer capacity");
        for (size_t i = 0; i < N; ++i) {
            push(&storage[i]);
        }
    }

    /**
     * @brief Push data to the buffer.
     * This method is only for the producer.
     */
    bool push(T item) {
        const size_t t = tail_.load(std::memory_order_relaxed);
        const size_t next = increment(t);
        const size_t h = head_.load(std::memory_order_acquire);

        if (next == h) {
            return false; // Full
        }

        buffer_[t] = item;
        tail_.store(next, std::memory_order_release);
        return true;
    }

    /**
     * @brief Pop data from the buffer.
     * This method is only for the consumer.
     */
    bool pop(T &out) {
        const size_t h = head_.load(std::memory_order_relaxed);
        const size_t t = tail_.load(std::memory_order_acquire);

        if (h == t) {
            return false; // Empty
        }

        out = buffer_[h];
        head_.store(increment(h), std::memory_order_release);
        return true;
    }

    bool empty() const {
        return head_.load(std::memory_order_acquire) ==
               tail_.load(std::memory_order_acquire);
    }

  private:
    size_t increment(size_t i) const {
        return (i + 1 == RealCapacity) ? 0 : i + 1;
    }

    // Use padding to prevent false sharing between head and tail which are
    // modified by different threads.
    // (We dont want head and tail on the same cache line)
    alignas(64) std::atomic<size_t> head_;
    alignas(64) std::atomic<size_t> tail_;

    std::array<T, RealCapacity> buffer_;
};
