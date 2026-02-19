#pragma once

#include "config.h"
#include <array>
#include <atomic>
#include <complex>
#include <cstdio>
#include <iio.h>
#include <iostream>
#include <memory>
#include <queue>
#include <stdexcept>

enum class AgcModes {
    MANUAL,
    SLOW_ATTACK,
    FAST_ATTACK,
    HYBRID,
};

std::string agc_string(AgcModes mode);

/**
 * @brief Configurations for Rx and Tx streaming
 *
 * Default values are set based on the values read from an unconfigured Adalm
 * Pluto.
 */
struct StreamConfig {
    long long fs_hz = 30720000;   // Baseband sample rate
    long long lo_hz = 2450000000; // LO frequency
    long long rf_bw = 18000000;   // RF bandwidth
    long long rx_gain = 71;       // dB gain; [-3 1 71]
    long long tx_gain = -10;      // dB gain; [-89.750000 0.250000 0.000000]
    AgcModes rx_agc_mode = AgcModes::SLOW_ATTACK; // AGC mode
    std::string rx_rfport = "A_BALANCED";         // Port name
    std::string tx_rfport = "A";                  // Port name

    friend std::ostream &operator<<(std::ostream &os, const StreamConfig &cfg);
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

    size_t transmit(const std::vector<std::complex<float>> &samples);

  private:
    std::shared_ptr<PlutoSdr> session_;
    StreamConfig cfg_;

    struct iio_device *tx_dev;
    struct iio_channel *tx0_i, *tx0_q;
    struct iio_buffer *txbuf;
};
