from commpy.filters import rrcosfilter
from commpy.modulation import QAMModem
import matplotlib.pyplot as plt
import scipy.signal as sci
import numpy as np

# Parameters
N_sym = 20             # number of symbols
sps = 8                # samples per symbol (upsampling)
alpha = 0.35           # roll-off factor
span = 6               # RRC filter span in symbols

# 1. Generate QPSK / 4-QAM symbols
M = 4
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

# 5. Receiver: matched filter (RRC again)
rx_signal = np.convolve(tx_signal, rrc_taps, mode='same')

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