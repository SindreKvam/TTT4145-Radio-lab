#pragma once

#define MHZ(x) ((long long)x * 1000000.0)
#define GHZ(x) ((long long)x * 1000000000.0)

#define RX_SAMPLING_RATE_DEFAULT MHZ(5.0)
#define RX_LO_FREQUENCY_DEFAULT GHZ(2.4)

#define RX_BUFFER_SIZE 4096
#define RX_CIRCULAR_BUFFER false

#define I_Q_CHANNEL_BUFFER_SIZE (RX_BUFFER_SIZE / 2)
