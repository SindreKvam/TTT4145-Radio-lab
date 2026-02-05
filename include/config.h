#pragma once

#define MHZ(x) ((long long)x * 1000000.0)
#define GHZ(x) ((long long)x * 1000000000.0)

#define RX_SAMPLING_RATE_DEFAULT MHZ(5.0)
#define RX_LO_FREQUENCY_DEFAULT GHZ(2.4)

#define RX_BUFFER_SIZE 1024 /* 8, 4096 */
#define RX_CIRCULAR_BUFFER false

#define RX_QUEUE_SIZE 3

#define I_Q_CHANNEL_BUFFER_SIZE (RX_BUFFER_SIZE / 2)

// Root raised cosine parameters
#define RRC_BETA 0.5f
#define RRC_SPAN 10
#define RRC_SPS 4

// Symbol rate (data rate * M (for M-QAM)) = SAMPLING_RATE / SPS
