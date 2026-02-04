
#include "config.h"
#include "core/spsc_ring.h"
#include "gui/window.h"
#include "radio/pluto_sdr.h"
#include "radio/radio_rx.h"
#include <QApplication>
#include <atomic>
#include <cstring>
#include <iostream>
#include <memory>
#include <queue>
#include <thread>

static void process_block(const std::int16_t *data, std::size_t len,
                          std::uint64_t seq);

static void rx_thread_fn(PlutoRx *rx, RxRingBuffer &free_q,
                         RxRingBuffer &filled_q, std::atomic<bool> &running) {

    void *p_dat, *p_end;
    ptrdiff_t p_inc;
    uint64_t seq = 0;

    while (running.load(std::memory_order_relaxed)) {
        RxSlab *slab = nullptr;

        // Get an empty slab
        while (!fifo_pop(free_q, slab)) {
            std::cout << "There are no empty slabs" << std::endl;
            if (!running.load(std::memory_order_relaxed)) {
                return;
            }
        }

        size_t nbytes = rx->receive(p_dat, p_end, p_inc);

        if (static_cast<size_t>(nbytes) > SLAB_BYTES) {
            std::cout << "Received " << nbytes << " bytes, expected "
                      << SLAB_BYTES << " or less" << std::endl;
            throw std::runtime_error("Configuration error, number of bytes "
                                     "received is larger than SLAB size");
        }

        std::memcpy(slab->data, p_dat, nbytes);
        slab->len = nbytes / 2; // Length in 16-bit chunks instead of bytes
        slab->seq = seq++;

        while (!fifo_push(filled_q, slab)) {
            if (!running.load(std::memory_order_relaxed)) {
                return;
            }
        }
    }
}

static void worker_thread_fn(PlutoRx *rx, RxRingBuffer &free_q,
                             RxRingBuffer &filled_q,
                             std::atomic<bool> &running) {

    while (running.load(std::memory_order_relaxed)) {
        RxSlab *slab = nullptr;

        while (!fifo_pop(filled_q, slab)) {
            if (!running.load(std::memory_order_relaxed)) {
                return;
            }
        }

        process_block(slab->data, slab->len, slab->seq);

        slab->len = 0;

        while (!fifo_push(free_q, slab)) {
            if (!running.load(std::memory_order_relaxed)) {
                return;
            }
        }
    }
}

static void process_block(const std::int16_t *data, std::size_t len,
                          std::uint64_t seq) {

    // TODO: Send data through FIR filter

    // std::cout << "New data" << std::endl;
    // for (int idx = 0; idx < len; ++idx) {
    //     std::cout << data[idx] << std::endl;
    // }

    // Instantiate buffers with macros instead of using "len"
    // So that the arrays are preallocated
    int16_t i_buf[SLAB_BYTES / 4];
    int16_t q_buf[SLAB_BYTES / 4];

    // Separate I and Q channels into own blocks
    for (int idx = 0, jdx = 0; idx < len; idx += 2, jdx++) {
        i_buf[jdx] = data[idx];
        q_buf[jdx] = data[idx + 1];
    }

    // We are now ready to create a constellation plot of the received data
    // We would assume that the constellation plot is rotating etc.

    // PLL stuff -> updated constellation

    (void)data;
    (void)len;
    (void)seq;
}

static void init_storage(RxSlab *slabs, RxRingBuffer &free_q) {
    // Put all slabs into free queue
    for (std::size_t i = 0; i < SLAB_COUNT; ++i) {
        slabs[i].len = 0;
        slabs[i].seq = 0;
        // At startup it must succeed
        while (!fifo_push(free_q, &slabs[i])) {
        }
    }
}

int main(int argc, char **argv) {

    // QApplication app(argc, argv);

    // Preallocate storage
    RxSlab slabs[SLAB_COUNT];
    RxRingBuffer free_q;
    RxRingBuffer filled_q;

    init_storage(slabs, free_q);

    std::atomic<bool> running = true;

    // Create a session with Adalm Pluto
    std::shared_ptr<PlutoSdr> session =
        std::shared_ptr<PlutoSdr>(new PlutoSdr());

    // Create rx session
    PlutoRx rx = PlutoRx(session, {});

    // Start threads
    std::thread t_rx(rx_thread_fn, &rx, std::ref(free_q), std::ref(filled_q),
                     std::ref(running));
    std::thread t_work(worker_thread_fn, &rx, std::ref(free_q),
                       std::ref(filled_q), std::ref(running));

    // GUI
    // MainWindow w(std::ref(i_queue), std::ref(q_queue));
    // w.resize(1000, 600);
    // w.show();
    //
    // int rc = app.exec();

    while (running.load(std::memory_order_relaxed)) {
        for (RxSlab slab : slabs) {
            // After 1000 data packets have been handled, stop the program
            if (slab.seq > 1000) {
                running.store(false, std::memory_order_relaxed);
            }
        }
    }

    // while (true) {
    //
    //     if (i_queue.size() >= 3) {
    //         break;
    //     }
    // }
    //
    // stop = true;
    //
    // std::cout << "Printing I and Q queues" << std::endl;
    // for (int j = 0; j < 3; ++j) {
    //     std::array<int16_t, RX_BUFFER_SIZE> i_front = i_queue.front();
    //     std::array<int16_t, RX_BUFFER_SIZE> q_front = q_queue.front();
    //
    //     for (int k = 0; k < RX_BUFFER_SIZE; ++k) {
    //         std::cout << i_front[k] << "  " << q_front[k] << " ";
    //     }
    //     std::cout << std::endl;
    //
    //     std::cout << i_queue.size() << std::endl;
    //     i_queue.pop();
    //     q_queue.pop();
    // }

    t_rx.join();
    t_work.join();

    std::cout << "Main loop exited. Quitting" << std::endl;

    // return rc;
    return 0;
}
