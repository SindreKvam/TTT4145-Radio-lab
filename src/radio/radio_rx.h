#pragma once

#include "config.h"
#include <array>
#include <iio.h>
#include <queue>

class Rx {
  public:
    Rx();
    ~Rx();

    void buffer_refill();
    void rx_loop(std::queue<std::array<int16_t, RX_BUFFER_SIZE>> &i_data_queue,
                 std::queue<std::array<int16_t, RX_BUFFER_SIZE>> &q_data_queue,
                 bool &stop);

    std::array<int16_t, RX_BUFFER_SIZE> i_buf;
    std::array<int16_t, RX_BUFFER_SIZE> q_buf;

  private:
    struct iio_context *ctx;
    struct iio_device *phy;
    struct iio_device *dev;
    struct iio_channel *rx0_i, *rx0_q;
    struct iio_buffer *rxbuf;
};
