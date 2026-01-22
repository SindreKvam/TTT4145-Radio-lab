#pragma once

// #include <array>
#include <iio.h>

class Rx {
  public:
    Rx();
    ~Rx();

    int buffer_refill();

    // std::array<int16_t, 4096> i_buf;
    // std::array<int16_t, 4096> q_buf;

  private:
    struct iio_context *ctx;
    struct iio_device *phy;
    struct iio_device *dev;
    struct iio_channel *rx0_i, *rx0_q;
    struct iio_buffer *rxbuf;
};
