
#include "radio_rx.h"
#include "config.h"
#include <iio.h>
#include <iostream>
#include <stdexcept>

Rx::Rx() {

    // Connect the ADALM PLUTO
    std::cout << "RX: Connecting to the ADALM PLUTO" << std::endl;
    ctx = iio_create_context_from_uri("ip:192.168.2.1");
    if (!ctx) {
        perror("Could not connect to the ADALM PLUTO");
        throw std::runtime_error("Could not connect to ADALM PLUTO");
    }
    phy = iio_context_find_device(ctx, "ad9361-phy");
    if (!phy) {
        perror("Could not find ad9361-phy");
    }

    iio_channel_attr_write_longlong(
        iio_device_find_channel(phy, "altvoltage0", true), "frequency",
        RX_LO_FREQUENCY_DEFAULT); /* RX LO frequency 2.4GHz */

    iio_channel_attr_write_longlong(
        iio_device_find_channel(phy, "voltage0", false), "sampling_frequency",
        RX_SAMPLING_RATE_DEFAULT); /* RX baseband rate 5 MSPS */

    // Find the RX device
    dev = iio_context_find_device(ctx, "cf-ad9361-lpc");
    rx0_i = iio_device_find_channel(dev, "voltage0", 0);
    rx0_q = iio_device_find_channel(dev, "voltage1", 0);

    std::cout << "RX: Enable I and Q channels" << std::endl;
    // Enable I and Q channels
    iio_channel_enable(rx0_i);
    iio_channel_enable(rx0_q);

    // Create buffer, consider cyclic buffer?
    rxbuf = iio_device_create_buffer(dev, RX_BUFFER_SIZE, RX_CIRCULAR_BUFFER);
    if (!rxbuf) {
        perror("Could not create RX buffer");
        throw std::runtime_error("Could not create RX buffer");
    }
}

Rx::~Rx() {

    std::cout << "RX: Destroying buffers" << std::endl;
    if (rxbuf) {
        iio_buffer_destroy(rxbuf);
    }

    std::cout << "RX: Disabling streaming channels" << std::endl;
    if (rx0_i) {
        iio_channel_disable(rx0_i);
    }
    if (rx0_q) {
        iio_channel_disable(rx0_q);
    }

    std::cout << "RX: Destroying context" << std::endl;
    if (ctx) {
        iio_context_destroy(ctx);
    }
    exit(0);
}

void Rx::buffer_refill() {

    void *p_dat, *p_end, *t_dat;
    ptrdiff_t p_inc;

    iio_buffer_refill(rxbuf);

    p_inc = iio_buffer_step(rxbuf);
    p_end = iio_buffer_end(rxbuf);

    uint16_t idx = 0;
    for (p_dat = iio_buffer_first(rxbuf, rx0_i); p_dat < p_end;
         p_dat += p_inc, t_dat += p_inc) {
        const int16_t i = ((int16_t *)p_dat)[0]; // Real (I)
        const int16_t q = ((int16_t *)p_dat)[1]; // Imag (Q)

        std::cout << "I: " << i << ", Q: " << q << std::endl;
        i_buf[idx] = i;
        q_buf[idx] = q;
        ++idx;
    }
}

void Rx::rx_loop(
    std::queue<std::array<int16_t, I_Q_CHANNEL_BUFFER_SIZE>> &i_data_queue,
    std::queue<std::array<int16_t, I_Q_CHANNEL_BUFFER_SIZE>> &q_data_queue,
    bool &stop) {

    while (!stop) {

        buffer_refill();

        i_data_queue.push(i_buf);
        q_data_queue.push(q_buf);
    }

    std::cout << "RX: loop stopped" << std::endl;
}
