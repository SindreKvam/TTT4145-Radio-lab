
#include "config.h"
#include "core/root_raised_cosine.h"
#include "core/spsc_ring.h"
#include "gui/window.h"
#include "radio/pluto_sdr.h"
#include <QApplication>
#include <atomic>
#include <cstring>
#include <iostream>
#include <memory>
#include <thread>
#include <vector>

static void
process_block(const std::int16_t *data, std::size_t len, std::uint64_t seq,
              SPSCRingBuffer<RxSlab *, GUI_SLAB_COUNT> &gui_free_q,
              SPSCRingBuffer<RxSlab *, GUI_SLAB_COUNT> &gui_filled_q,
              Fir &fir_i, Fir &fir_q);

static void rx_thread_fn(PlutoRx *rx,
                         SPSCRingBuffer<RxSlab *, SLAB_COUNT> &free_q,
                         SPSCRingBuffer<RxSlab *, SLAB_COUNT> &filled_q,
                         std::atomic<bool> &running) {

    void *p_dat, *p_end;
    ptrdiff_t p_inc;
    uint64_t seq = 0;

    while (running.load(std::memory_order_relaxed)) {
        RxSlab *slab = nullptr;

        // Get an empty slab
        while (!free_q.pop(slab)) {
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

        while (!filled_q.push(slab)) {
            if (!running.load(std::memory_order_relaxed)) {
                return;
            }
        }
    }
}

static void
worker_thread_fn(PlutoRx *rx, SPSCRingBuffer<RxSlab *, SLAB_COUNT> &free_q,
                 SPSCRingBuffer<RxSlab *, SLAB_COUNT> &filled_q,
                 std::atomic<bool> &running,
                 SPSCRingBuffer<RxSlab *, GUI_SLAB_COUNT> &gui_free_q,
                 SPSCRingBuffer<RxSlab *, GUI_SLAB_COUNT> &gui_filled_q) {

    RootRaisedCosine fir_i(RRC_BETA, RRC_SPAN, RRC_SPS);
    RootRaisedCosine fir_q(RRC_BETA, RRC_SPAN, RRC_SPS);

    while (running.load(std::memory_order_relaxed)) {
        RxSlab *slab = nullptr;

        while (!filled_q.pop(slab)) {
            if (!running.load(std::memory_order_relaxed)) {
                return;
            }
        }

        process_block(slab->data, slab->len, slab->seq, gui_free_q,
                      gui_filled_q, fir_i, fir_q);

        slab->len = 0;

        while (!free_q.push(slab)) {
            if (!running.load(std::memory_order_relaxed)) {
                return;
            }
        }
    }
}

static void
process_block(const std::int16_t *data, std::size_t len, std::uint64_t seq,
              SPSCRingBuffer<RxSlab *, GUI_SLAB_COUNT> &gui_free_q,
              SPSCRingBuffer<RxSlab *, GUI_SLAB_COUNT> &gui_filled_q,
              Fir &fir_i, Fir &fir_q) {

    size_t num_samples = len / 2;
    if (num_samples == 0)
        return;

    // Data needs to be floating to perform FIR filtering
    std::vector<float> i_in(num_samples), q_in(num_samples);
    for (size_t i = 0; i < num_samples; ++i) {
        i_in[i] = static_cast<float>(data[i * 2]);
        q_in[i] = static_cast<float>(data[i * 2 + 1]);
    }

    // Apply Matched Filter
    std::vector<float> i_out = fir_i.filter(i_in);
    std::vector<float> q_out = fir_q.filter(q_in);

    // Pass the filtered data to the GUI
    RxSlab *gui_slab = nullptr;
    if (gui_free_q.pop(gui_slab)) {

        for (size_t i = 0; i < num_samples; ++i) {
            gui_slab->data[i * 2] = static_cast<int16_t>(i_out[i]);
            gui_slab->data[i * 2 + 1] = static_cast<int16_t>(q_out[i]);
        }
        gui_slab->len = len;
        gui_slab->seq = seq;
        gui_filled_q.push(gui_slab);
    }
}

static int parse_arguments(int argc, char **argv, bool &debug) {
    bool help_found = false;
    for (int i = 0; i < argc; ++i) {

        if (std::string(argv[i]) == "--help") {
            help_found = true;
            break;
        }
        if (std::string(argv[i]) == "--debug") {
            debug = true;
        }
    }

    if (help_found) {
        std::cout << "Help menu:" << std::endl;
        std::cout << "\t--debug : prints extra debug information." << std::endl;
        return -1;
    }
    return 0;
}

int main(int argc, char **argv) {

    bool debug = false;
    int err = parse_arguments(argc, argv, debug);
    if (err < 0) {
        return err;
    }

    QApplication app(argc, argv);

    // Preallocate storage for Radio RX
    RxSlab slabs[SLAB_COUNT];
    SPSCRingBuffer<RxSlab *, SLAB_COUNT> free_q(slabs);
    SPSCRingBuffer<RxSlab *, SLAB_COUNT> filled_q;

    // Preallocate storage for GUI
    RxSlab gui_slabs[GUI_SLAB_COUNT];
    SPSCRingBuffer<RxSlab *, GUI_SLAB_COUNT> gui_free_q(gui_slabs);
    SPSCRingBuffer<RxSlab *, GUI_SLAB_COUNT> gui_filled_q;

    std::atomic<bool> running = true;

    // Create a session with Adalm Pluto
    std::shared_ptr<PlutoSdr> session =
        std::shared_ptr<PlutoSdr>(new PlutoSdr());

    // Create rx session
    StreamConfig rx_cfg = StreamConfig{.rfport = "A_BALANCED"};
    PlutoRx rx = PlutoRx(session, rx_cfg);

    // StreamConfig tx_cfg = StreamConfig{.rfport = "A"};

    if (debug) {
        std::cout << *session << std::endl;
    }
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

    std::cout << "\033[34mMain loop exited. Quitting\033[0m" << std::endl;

    return rc;
}
