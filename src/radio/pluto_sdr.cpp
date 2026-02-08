
#include "pluto_sdr.h"
#include "config.h"
#include <atomic>
#include <cstddef>
#include <cstring>
#include <iio.h>
#include <memory>
#include <stdexcept>

template <typename T>
static int print_attr_cb(T, const char *attr, const char *value, size_t len,
                         void *os_stream) {
    if (os_stream) {
        std::ostream &os = *static_cast<std::ostream *>(os_stream);
        os << "\t\tAttribute: " << attr << " = " << value << "\n";
    }
    return 0;
}

std::string agc_string(AgcModes mode) {
    switch (mode) {
    case AgcModes::MANUAL:
        return "manual";
    case AgcModes::SLOW_ATTACK:
        return "slow_attack";
    case AgcModes::FAST_ATTACK:
        return "fast_attack";
    case AgcModes::HYBRID:
        return "hybrid";
    default:
        return "slow_attack"; // The default on the pluto
    }
}

std::ostream &operator<<(std::ostream &os, const StreamConfig &cfg) {
    os << "\n----- Stream Configuration -----";
    os << "\n\033[35mBaseband sample rate: " << cfg.fs_hz / 1e6 << " MHz";
    os << "\nLO frequency: " << cfg.lo_hz / 1e6 << " MHz";
    os << "\nRF bandwidth: " << cfg.rf_bw / 1e6 << " MHz";
    os << "\nAGC mode: " << agc_string(cfg.agc_mode);
    os << "\nRF port: " << cfg.rfport << "\033[0m";
    os << "\n--------------------------------\n";

    return os;
}

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

static char *string_to_char_array(std::string str) {
    // https://cplusplus.com/reference/string/string/c_str/
    char *arr = new char[str.length() + 1];
    std::strcpy(arr, str.c_str());
    return arr;
}

void PlutoSdr::configure_rx(const StreamConfig &cfg) {

    iio_channel_attr_write(iio_device_find_channel(phy, "voltage0", false),
                           "rf_port_select", string_to_char_array(cfg.rfport));

    iio_channel_attr_write(iio_device_find_channel(phy, "voltage0", false),
                           "gain_control_mode",
                           string_to_char_array(agc_string(cfg.agc_mode)));

    // Set Rx LO frequency
    iio_channel_attr_write_longlong(
        iio_device_find_channel(phy, "altvoltage0", true), "frequency",
        cfg.lo_hz);

    // Set Rx baseband sample rate
    iio_channel_attr_write_longlong(
        iio_device_find_channel(phy, "voltage0", false), "sampling_frequency",
        cfg.fs_hz);

    // Set RF bandwidth
    iio_channel_attr_write_longlong(
        iio_device_find_channel(phy, "voltage0", false), "rf_bandwidth",
        cfg.rf_bw);
}

void PlutoSdr::configure_tx(const StreamConfig &cfg) {

    // Set Tx LO frequency
    iio_channel_attr_write_longlong(
        iio_device_find_channel(phy, "altvoltage1", true), "frequency",
        cfg.lo_hz);

    // Set Tx baseband sample rate
    iio_channel_attr_write_longlong(
        iio_device_find_channel(phy, "voltage0", true), "sampling_frequency",
        cfg.fs_hz);
}

std::ostream &operator<<(std::ostream &os, const PlutoSdr &sdr) {
    if (sdr.phy) {

        // Phy attributes
        os << "\033[34mAttributes for " << iio_device_get_name(sdr.phy)
           << ":\033[0m\n";
        iio_device_attr_read_all(sdr.phy, print_attr_cb<iio_device *>, &os);

        os << "\033[34mChannel attributes:\033[0m\n";
        // Channel attributes
        unsigned int nb_channels = iio_device_get_channels_count(sdr.phy);
        for (unsigned int i = 0; i < nb_channels; i++) {
            struct iio_channel *chn = iio_device_get_channel(sdr.phy, i);
            const char *channel_name = iio_channel_get_name(chn);
            const bool tx = iio_channel_is_output(chn);

            os << "\033[34m\n\tChannel: " << iio_channel_get_id(chn) << " ("
               << (channel_name ? channel_name : "no name") << ") ["
               << (tx ? "Tx" : "Rx") << "]\n\033[0m";

            iio_channel_attr_read_all(chn, print_attr_cb<iio_channel *>, &os);
        }
    }

    return os;
}

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
