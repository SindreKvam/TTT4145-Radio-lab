from dataclasses import dataclass


@dataclass
class RadioConfig:
    rx_uri: str = "ip:192.168.2.1"
    tx_uri: str = "ip:192.168.2.1"

    # --------------------------------------------------
    # RF parameters
    # --------------------------------------------------
    rx_lo_hz: int = 2_400_000_000  # RX local oscillator frequency (Hz)
    tx_lo_hz: int = 2_400_000_000  # TX local oscillator frequency (Hz)
    sample_rate_hz: int = 5_000_000  # ADC/DAC sample rate (Hz)
    rx_rf_bandwidth_hz: int = 4_000_000  # RX RF bandwidth (Hz)
    tx_rf_bandwidth_hz: int = 4_000_000  # TX RF bandwidth (Hz)
    rx_hardware_gain_db: int = 30  # RX hardware gain (dB), manual mode
    tx_hardware_gain_db: int = -30  # TX hardware gain (dB, negative = attenuation)

    # Quadrature / DC tracking
    quadrature_tracking: bool = False
    rf_dc_offset_tracking: bool = True
    bb_dc_offset_tracking: bool = True

    # --------------------------------------------------
    # Modem / PHY
    # --------------------------------------------------
    qam_order: int = 4
    sps: int = 8  # Samples per symbol (oversampling factor)
    rrc_beta: float = 0.2  # RRC roll-off factor
    rrc_span: int = 10  # RRC filter span in symbols

    # Preamble
    nasa_code_bits: int = 32
    pll_preamble_length: int = 1200

    # --------------------------------------------------
    # Buffer / pipeline
    # --------------------------------------------------
    # rx_buffer_size is the number of *samples* per sdr.rx() call.
    # It is derived as num_symbols * sps but can be overridden.
    rx_buffer_size: int = 0  # 0 = auto-compute from num_symbols * sps
    ring_slots: int = 16  # SharedRingBuffer depth (number of slots)

    # TX cyclic buffer: if True, the Pluto hardware loops the TX buffer
    # automatically without CPU involvement — good for fixed-frame looping.
    tx_cyclic_buffer: bool = False

    # --------------------------------------------------
    # PLL
    # --------------------------------------------------
    pll_kp: float = 0.0222  # Proportional gain
    pll_ki: float = 0.00024  # Integral gain

    # --------------------------------------------------
    # Debug / logging
    # --------------------------------------------------
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    enable_gui: bool = True
    gui_update_hz: int = 30  # GUI plot refresh rate

    # ------------------------------------------------------------------
    # Derived helpers
    # --------------------------------------------------
    def effective_rx_buffer_size(self, num_symbols: int) -> int:
        """Return the buffer size to use for sdr.rx_buffer_size.

        If rx_buffer_size is explicitly set (non-zero) that value is used.
        Otherwise it is derived as num_symbols * sps.
        """
        if self.rx_buffer_size > 0:
            return self.rx_buffer_size
        return num_symbols * self.sps

    @property
    def single_radio_mode(self) -> bool:
        """True when TX and RX share the same physical device."""
        return self.rx_uri == self.tx_uri

    @property
    def bits_per_symbol(self) -> int:
        import math

        return int(math.log2(self.qam_order))
