from commpy.filters import rrcosfilter
from commpy.modulation import QAMModem
import matplotlib.pyplot as plt
import scipy.signal as sci
import numpy as np

class Muller_Muller:
    def __init__(self, Modulations = 16, sps = 2):
        self.prev_val = np.zeros(2, dtype=complex)
        self.prev_a_hat = np.zeros(2, dtype=complex)

        self.timing_error_estimate = 0
        self.timing_error_scalar = 0.01

        self.modem = QAMModem(Modulations)
        self.sps = 8
        
    
    #remember to adjust the received sampling based on error estimate
    def timing_error(self, received): 
        #decision block (figure)
        a_hat = modem.demodulate(received)

        #store a_hat in buffer
        self.prev_a_hat = np.roll(self.prev_a_hat,1)
        self.prev_a_hat[0] = a_hat

        #store received in buffer
        self.prev_val = np.roll(self.prev_val, 1)
        self.prev_a_hat[0] = received

        #multiplyers refference to figure
        top_mult = self.prev_a_hat[0] * self.prev_val[1]
        bot_mult = self.prev_a_hat[1] * self.prev_val[0]

        #summation
        error = bot_mult + (-top_mult)
        self.timing_error_estimate = error * self.timing_error_scalar
        return self.timing_error_estimate


# Parameters
N_sym = 21             # number of symbols
sps = 2                # samples per symbol (upsampling)
alpha = 0.35           # roll-off factor
span = 11              # RRC filter span in symbols

# 1. Generate QPSK / 4-QAM symbols
M = 16
message_len = 16
modem = QAMModem(M)
symbols = np.random.randint(0, M, N_sym)
x = modem.constellation[symbols]  # complex symbols


# 2. Upsample (insert zeros between symbols)
x_upsampled = np.zeros(N_sym*sps, dtype=complex)
x_upsampled[::sps] = x

# 3. Create RRC filter
t, rrc_taps = rrcosfilter(span*sps+1, alpha, 1, sps)

# 4. Transmit: convolve symbols with RRC
tx_signal = np.convolve(x_upsampled, rrc_taps, mode='same')
x_signal = np.arange(len(tx_signal))

#apply phase offset
#interpolate tx with 8 times the length

interpol_val = 8
interpol_tx = np.arange(0,len(tx_signal), 1/interpol_val)
interpol_tx = np.interp(interpol_tx, x_signal, tx_signal)

phaseshift_samples = 100
interpol_tx = np.pad(interpol_tx, (0,phaseshift_samples))
phaseshifted_rx = interpol_tx[phaseshift_samples::interpol_val]


plt.subplot(2,1,1)
plt.stem(tx_signal)
plt.subplot(2,1,2)
plt.stem(phaseshifted_rx)
plt.show()


# 5. Receiver: matched filter (RRC again)
rx_signal = np.convolve(tx_signal, rrc_taps, mode='same')












"""
# 6. Plot
plt.figure(figsize=(12,5))
plt.subplot(3,1,1)
plt.title("Transmitted RRC-shaped signal")
plt.plot(tx_signal.real, label='I')
plt.plot(tx_signal.imag, label='Q')
plt.legend()
plt.grid()

plt.subplot(3,1,2)
plt.title("After matched filter (receiver)")
plt.plot(rx_signal.real, label='I')
plt.plot(rx_signal.imag, label='Q')
plt.legend()
plt.grid()
plt.tight_layout()

plt.subplot(3,1,3)
plt.title("X_updsampled")
plt.plot(x_upsampled.real, label='I')
plt.plot(x_upsampled.imag, label='Q')
plt.legend()
plt.grid()
plt.tight_layout()
plt.show()

plt.stem(rrc_taps)
plt.show()
"""
