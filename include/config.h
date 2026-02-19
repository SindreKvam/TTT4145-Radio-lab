#pragma once

#define MHZ(x) ((long long)((x)*1000000.0))
#define GHZ(x) ((long long)((x)*1000000000.0))

// Root raised cosine parameters
#define RRC_BETA 0.5f
#define RRC_SPAN 10
#define RRC_SPS 4 /** Sample per symbol */

/* Rx */
#define RX_SAMPLING_RATE_DEFAULT MHZ(5.0)
#define RX_RF_BANDWIDTH_DEFAULT MHZ(10)
#define RX_LO_FREQUENCY_DEFAULT GHZ(2.4)
#define RX_HARDWARE_GAIN 71

#define RX_BUFFER_SIZE 1024
#define RX_CIRCULAR_BUFFER false

#define RX_QUEUE_SIZE 3

/* Tx */
#define TX_BUFFER_SIZE RX_BUFFER_SIZE

#define TX_SYMBOL_RATE_DEFAULT RX_SAMPLING_RATE_DEFAULT
#define TX_RF_BANDWIDTH_DEFAULT MHZ(10)
#define TX_LO_FREQUENCY_DEFAULT GHZ(2.4)
#define TX_HARDWARE_GAIN 0
