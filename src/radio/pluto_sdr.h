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
    std::string rfport;                         // Port name

    friend std::ostream &operator<<(std::ostream &os, const StreamConfig &cfg) {
        os << "\n----- Stream Configuration -----";
        os << "\n\033[35mBaseband sample rate: " << cfg.fs_hz / 1e6 << " MHz";
        os << "\nLO frequency: " << cfg.lo_hz / 1e6 << " MHz";
        os << "\nRF port: " << cfg.rfport << "\033[0m";
        os << "\n--------------------------------\n";

        return os;
    }
};

/**
 * @brief PlutoSdr is the base class for connecting to the Adalm Pluto.
 *
 * When a object of type PlutoSdr is constructed, a connection with an Adalm
 * Pluto SDR will be attempted.
 */
class PlutoSdr {
  public:
    PlutoSdr();
    ~PlutoSdr();

    struct iio_context *ctx;

    void configure_rx(const StreamConfig &cfg);
    void configure_tx(const StreamConfig &cfg);
    friend std::ostream &operator<<(std::ostream &os, const PlutoSdr &sdr);

  private:
    struct iio_device *phy;
};

/**
 * @brief PlutoRx will configure Rx on an existing PlutoSdr session.
 *
 * This class requires there to already be an existing PlutoSdr session.
 * When constructing this class, connections with the Rx streaming channels are
 * made, and an Rx buffer is created
 *
 * @param session A shared pointer to an existing PlutoSdr session.
 * @param cfg A StreamConfig struct containing information about how the Pluto
 * Rx channel should be configured
 */
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

/**
 *
 */
class PlutoTx {
  public:
    PlutoTx(std::shared_ptr<PlutoSdr> session, const StreamConfig &cfg);
    ~PlutoTx();

    void transmit();

  private:
    std::shared_ptr<PlutoSdr> session_;
    StreamConfig cfg_;

    struct iio_device *tx_dev;
    struct iio_channel *tx0_i, *tx0_q;
    struct iio_buffer *txbuf;
};
