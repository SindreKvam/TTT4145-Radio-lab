
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
#include <thread>

static void process_block(const std::int16_t *data, std::size_t len,
                          std::uint64_t seq, RxRingBuffer &gui_free_q,
                          RxRingBuffer &gui_filled_q);

static void rx_thread_fn(PlutoRx *rx, RxRingBuffer &free_q,
                         RxRingBuffer &filled_q, std::atomic<bool> &running) {

    void *p_dat, *p_end;
    ptrdiff_t p_inc;
    uint64_t seq = 0;

    while (running.load(std::memory_order_relaxed)) {
        RxSlab *slab = nullptr;

        // Get an empty slab
        while (!fifo_pop(free_q, slab)) {
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
                             RxRingBuffer &filled_q, std::atomic<bool> &running,
                             RxRingBuffer &gui_free_q,
                             RxRingBuffer &gui_filled_q) {

    while (running.load(std::memory_order_relaxed)) {
        RxSlab *slab = nullptr;

        while (!fifo_pop(filled_q, slab)) {
            if (!running.load(std::memory_order_relaxed)) {
                return;
            }
        }

        process_block(slab->data, slab->len, slab->seq, gui_free_q,
                      gui_filled_q);

        slab->len = 0;

        while (!fifo_push(free_q, slab)) {
            if (!running.load(std::memory_order_relaxed)) {
                return;
            }
        }
    }
}

static void process_block(const std::int16_t *data, std::size_t len,
                          std::uint64_t seq, RxRingBuffer &gui_free_q,
                          RxRingBuffer &gui_filled_q) {

    // Pass the data to the GUI
    RxSlab *gui_slab = nullptr;
    if (fifo_pop(gui_free_q, gui_slab)) {
        std::memcpy(gui_slab->data, data, len * sizeof(int16_t));
        gui_slab->len = len;
        gui_slab->seq = seq;
        fifo_push(gui_filled_q, gui_slab);
    }

    (void)data;
    (void)len;
    (void)seq;
}

static void init_storage(RxSlab *slabs, size_t count, RxRingBuffer &free_q) {
    // Put all slabs into free queue
    for (std::size_t i = 0; i < count; ++i) {
        slabs[i].len = 0;
        slabs[i].seq = 0;
        // At startup it must succeed
        while (!fifo_push(free_q, &slabs[i])) {
        }
    }
}

int main(int argc, char **argv) {

    QApplication app(argc, argv);

    // Preallocate storage for Radio RX
    RxSlab slabs[SLAB_COUNT];
    RxRingBuffer free_q;
    RxRingBuffer filled_q;
    init_storage(slabs, SLAB_COUNT, free_q);

    // Preallocate storage for GUI
    static const int GUI_SLAB_COUNT = 4;
    RxSlab gui_slabs[GUI_SLAB_COUNT];
    RxRingBuffer gui_free_q;
    RxRingBuffer gui_filled_q;
    init_storage(gui_slabs, GUI_SLAB_COUNT, gui_free_q);

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
                       std::ref(filled_q), std::ref(running),
                       std::ref(gui_free_q), std::ref(gui_filled_q));

    // GUI
    MainWindow w(gui_free_q, gui_filled_q);
    w.show();

    int rc = app.exec();

    // Signal threads to stop when GUI is closed
    running.store(false, std::memory_order_relaxed);

    t_rx.join();
    t_work.join();

    std::cout << "Main loop exited. Quitting" << std::endl;

    return rc;
}
