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

struct streamConfig {
    long long bw_hz; // Analog bandwidth
    long long fs_hz; // Baseband sample rate
    long long lo_hz; // LO frequency
};

class PlutoSdr {
  public:
    PlutoSdr();
    ~PlutoSdr();

    struct iio_context *ctx;

    void configure_rx(const streamConfig &cfg);
    void configure_tx(const streamConfig &cfg);

  private:
    struct iio_device *phy;
};

/* ---------- Rx ---------- */
class PlutoRx {
  public:
    PlutoRx(std::shared_ptr<PlutoSdr> session, streamConfig cfg);
    ~PlutoRx();

    size_t receive(void *&p_dat, void *&p_end, ptrdiff_t &p_inc);

  private:
    std::shared_ptr<PlutoSdr> session_;
    streamConfig cfg_;

    struct iio_device *rx_dev;
    struct iio_channel *rx0_i, *rx0_q;
    struct iio_buffer *rxbuf;
};

/* ---------- Tx ---------- */
class PlutoTx {
  public:
    PlutoTx(std::shared_ptr<PlutoSdr> session, streamConfig cfg);
    ~PlutoTx();

    void transmit();

  private:
    std::shared_ptr<PlutoSdr> session_;
    streamConfig cfg_;

    struct iio_device *tx_dev;
    struct iio_channel *tx0_i, *tx0_q;
    struct iio_buffer *txbuf;
};
