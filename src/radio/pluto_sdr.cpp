
#include "pluto_sdr.h"
#include "config.h"
#include <atomic>
#include <cstddef>
#include <iio.h>
#include <memory>
#include <stdexcept>

PlutoSdr::PlutoSdr() {

    // Connecting to ADALM Pluto
    std::cout << "\033[34mConnecting to the ADALM PLUTO\033[0m" << std::endl;
    ctx = iio_create_context_from_uri("ip:192.168.2.1");
    if (!ctx) {
        perror("Could not connect to the ADALM PLUTO");
        throw std::runtime_error("Could not connect to the ADALM PLUTO");
    }

    phy = iio_context_find_device(ctx, "ad9361-phy");
    if (!phy) {
        perror("Could not find ad9361-phy");
    }

    std::cout << "\033[32mSuccessfully connected to the Adalm Pluto\033[0m"
              << std::endl;
};

PlutoSdr::~PlutoSdr() {

    if (ctx) {
        std::cout << "Destroying context" << std::endl;
        iio_context_destroy(ctx);
    }

    std::cout << "\033[32mSuccessfully disconnected from the Adalm Pluto\033[0m"
              << std::endl;
}

void PlutoSdr::configure_rx(const StreamConfig &cfg) {

    // Set RX LO frequency
    iio_channel_attr_write_longlong(
        iio_device_find_channel(phy, "altvoltage0", true), "frequency",
        cfg.lo_hz);

    // Set RX baseband sample rate
    iio_channel_attr_write_longlong(
        iio_device_find_channel(phy, "voltage0", false), "sampling_frequency",
        cfg.fs_hz);
}

void PlutoSdr::configure_tx(const StreamConfig &cfg) {}

/* ---------- Rx ---------- */
PlutoRx::PlutoRx(std::shared_ptr<PlutoSdr> session, const StreamConfig &cfg)
    : session_(std::move(session)), cfg_(std::move(cfg)) {

    if (!session_) {
        throw std::runtime_error("No Pluto session");
    }

    std::cout << "Configuring RX streaming channel: \n" << cfg << std::endl;
    session_->configure_rx(cfg);

    std::cout << "Enabling streaming channels" << std::endl;
    rx_dev = iio_context_find_device(session_->ctx, "cf-ad9361-lpc");
    if (!rx_dev) {
        perror("Could not find RX device");
    }
    rx0_i = iio_device_find_channel(rx_dev, "voltage0", 0);
    rx0_q = iio_device_find_channel(rx_dev, "voltage1", 0);

    iio_channel_enable(rx0_i);
    iio_channel_enable(rx0_q);

    std::cout << "Creating Rx buffer" << std::endl;
    rxbuf =
        iio_device_create_buffer(rx_dev, RX_BUFFER_SIZE, RX_CIRCULAR_BUFFER);
    if (!rxbuf) {
        perror("Could not create Rx buffer");
        throw std::runtime_error("Could not create Rx buffer");
    }

    std::cout << "\033[32mSuccessfully configured Adalm Pluto in Rx mode\033[0m"
              << std::endl;
}

PlutoRx::~PlutoRx() {

    std::cout << "Destroying buffers" << std::endl;
    if (rxbuf) {
        iio_buffer_destroy(rxbuf);
    }

    std::cout << "Disabling streaming channels" << std::endl;
    if (rx0_i) {
        iio_channel_disable(rx0_i);
    }
    if (rx0_q) {
        iio_channel_disable(rx0_q);
    }
}

size_t PlutoRx::receive(void *&p_dat, void *&p_end, ptrdiff_t &p_inc) {

    // Refill RX buffer
    size_t nbytes = iio_buffer_refill(rxbuf);
    if (nbytes < 0) {
        throw std::runtime_error("Unable to fill Rx buffer");
    }

    p_inc = iio_buffer_step(rxbuf);
    p_dat = iio_buffer_first(rxbuf, rx0_i);
    p_end = iio_buffer_end(rxbuf);

    return nbytes;
}

/* ---------- Tx ---------- */
PlutoTx::PlutoTx(std::shared_ptr<PlutoSdr> session, const StreamConfig &cfg)
    : session_(std::move(session)), cfg_(std::move(cfg)) {

    if (!session_) {
        throw std::runtime_error("No Pluto session");
    }

    tx_dev = iio_context_find_device(session_->ctx, "cf-ad9361-dds-core-lpc");
    if (!tx_dev) {
        perror("Could not find TX device");
    }
    tx0_i = iio_device_find_channel(tx_dev, "voltage0", 1);
    tx0_q = iio_device_find_channel(tx_dev, "voltage1", 1);

    iio_channel_enable(tx0_i);
    iio_channel_enable(tx0_q);

    txbuf =
        iio_device_create_buffer(tx_dev, RX_BUFFER_SIZE, RX_CIRCULAR_BUFFER);
    if (!txbuf) {
        perror("Could not create Rx buffer");
        throw std::runtime_error("Could not create Rx buffer");
    }
}

PlutoTx::~PlutoTx() {

    std::cout << "Destroying buffers" << std::endl;
    if (txbuf) {
        iio_buffer_destroy(txbuf);
    }

    std::cout << "Disabling streaming channels" << std::endl;
    if (tx0_i) {
        iio_channel_disable(tx0_i);
    }
    if (tx0_q) {
        iio_channel_disable(tx0_q);
    }
}
