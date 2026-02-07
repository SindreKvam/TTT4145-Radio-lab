#pragma once

#include "config.h"
#include <array>
#include <atomic>
#include <cstdio>
#include <iio.h>
#include <iostream>
#include <memory>
#include <queue>
#include <stdexcept>

struct StreamConfig {
    long long fs_hz = RX_SAMPLING_RATE_DEFAULT; // Baseband sample rate
    long long lo_hz = RX_LO_FREQUENCY_DEFAULT;  // LO frequency

    friend std::ostream &operator<<(std::ostream &os, const StreamConfig &cfg) {
        os << "----- Stream Configuration -----\n";
        os << "\033[35mBaseband sample rate: " << cfg.fs_hz / 1e6 << " MHz\n";
        os << "LO frequency: " << cfg.lo_hz / 1e6 << " MHz\033[0m\n";
        os << "--------------------------------";

        return os;
    }
};

class PlutoSdr {
  public:
    PlutoSdr();
    ~PlutoSdr();

    struct iio_context *ctx;

    void configure_rx(const StreamConfig &cfg);
    void configure_tx(const StreamConfig &cfg);

  private:
    struct iio_device *phy;
};

/* ---------- Rx ---------- */
class PlutoRx {
  public:
    PlutoRx(std::shared_ptr<PlutoSdr> session, const StreamConfig &cfg);
    ~PlutoRx();

    /**
     * @brief Receive data from Adalm Pluto.
     *
     * @param p_dat pointer to the start of data.
     * @param p_end pointer to the end of data.
     * @param p_inc increment size between symbols.
     *
     * @return Number of bytes placed in buffer.
     */
    size_t receive(void *&p_dat, void *&p_end, ptrdiff_t &p_inc);

  private:
    std::shared_ptr<PlutoSdr> session_;
    StreamConfig cfg_;

    struct iio_device *rx_dev;
    struct iio_channel *rx0_i, *rx0_q;
    struct iio_buffer *rxbuf;
};

/* ---------- Tx ---------- */
class PlutoTx {
  public:
    PlutoTx(std::shared_ptr<PlutoSdr> session, StreamConfig cfg);
    ~PlutoTx();

    void transmit();

  private:
    std::shared_ptr<PlutoSdr> session_;
    StreamConfig cfg_;

    struct iio_device *tx_dev;
    struct iio_channel *tx0_i, *tx0_q;
    struct iio_buffer *txbuf;
};
