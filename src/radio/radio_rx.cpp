
#include "radio_rx.h"
#include <iostream>

Rx::Rx() {

    // Connect the ADALM PLUTO
    std::cout << "Connecting to the ADALM PLUTO" << std::endl;
    ctx = iio_create_context_from_uri("ip:192.168.2.1");
    if (!ctx) {
        perror("Could not connect to the ADALM PLUTO");
    }
    phy = iio_context_find_device(ctx, "ad9361-phy");
    if (!phy) {
        perror("Could not find ad9361-phy");
    }

    iio_channel_attr_write_longlong(
        iio_device_find_channel(phy, "altvoltage0", true), "frequency",
        2400000000); /* RX LO frequency 2.4GHz */

    iio_channel_attr_write_longlong(
        iio_device_find_channel(phy, "voltage0", false), "sampling_frequency",
        5000000); /* RX baseband rate 5 MSPS */

    // Find the RX device
    dev = iio_context_find_device(ctx, "cf-ad9361-lpc");
    rx0_i = iio_device_find_channel(dev, "voltage0", 0);
    rx0_q = iio_device_find_channel(dev, "voltage1", 0);

    std::cout << "Enable I and Q channels" << std::endl;
    // Enable I and Q channels
    iio_channel_enable(rx0_i);
    iio_channel_enable(rx0_q);

    // Create buffer, consider cyclic buffer?
    rxbuf = iio_device_create_buffer(dev, 4096, false);
    if (!rxbuf) {
        perror("Could not create RX buffer");
        // shutdown();
    }
}

Rx::~Rx() {

    iio_buffer_destroy(rxbuf);
    iio_context_destroy(ctx);
}

int Rx::buffer_refill() {

    void *p_dat, *p_end, *t_dat;
    ptrdiff_t p_inc;

    iio_buffer_refill(rxbuf);

    p_inc = iio_buffer_step(rxbuf);
    p_end = iio_buffer_end(rxbuf);

    for (p_dat = iio_buffer_first(rxbuf, rx0_i); p_dat < p_end;
         p_dat += p_inc, t_dat += p_inc) {
        const int16_t i = ((int16_t *)p_dat)[0]; // Real (I)
        const int16_t q = ((int16_t *)p_dat)[1]; // Imag (Q)

        /* Process here */
        std::cout << "I: " << i << ", Q: " << q << std::endl;
    }
}
