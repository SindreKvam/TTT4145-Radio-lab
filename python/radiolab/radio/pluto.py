"""Adalm Pluto SDR implementation."""

import logging

import adi
import numpy as np

from radiolab.config.config import RadioConfig
from radiolab.radio.interface import RadioInterface

logger = logging.getLogger(__name__)


class PlutoRadio(RadioInterface):
    """Adalm Pluto SDR implementation.

    This class wraps the pyadi-iio Pluto interface and provides a clean
    API for transmit/receive operations.
    """

    def __init__(self, uri: str = "usb:"):
        """Initialize Pluto radio.

        Args:
            uri: Device URI (default: "usb:")
        """
        self.sdr = adi.Pluto(uri)
        self._configured = False
        logger.info(f"Connected to Pluto SDR at {uri}")

    def configure(
        self,
        config: RadioConfig,
        buffer_size: int,
    ) -> None:
        """Configure the Pluto SDR.

        Args:
            config: Radio configuration object
            buffer_size: RX buffer size in samples
        """
        # Basic configuration
        self.sdr.rx_rf_bandwidth = config.rx_rf_bandwidth
        self.sdr.rx_lo = config.rx_lo
        self.sdr.tx_lo = config.tx_lo
        self.sdr.tx_cyclic_buffer = config.tx_cyclic_buffer
        self.sdr.tx_hardwaregain_chan0 = config.tx_gain
        self.sdr.rx_buffer_size = buffer_size
        self.sdr.gain_control_mode_chan0 = config.gain_control_mode

        # Access PHY device for advanced settings
        phy = self.sdr.ctx.find_device("ad9361-phy")
        if phy is not None:
            rx0 = phy.find_channel("voltage0", False)  # False => RX/input channel
            if rx0 is not None:
                # Configure tracking settings
                rx0.attrs["quadrature_tracking_en"] = (
                    "1" if config.quadrature_tracking_en else "0"
                )
                rx0.attrs["rf_dc_offset_tracking_en"].value = (
                    "1" if config.rf_dc_offset_tracking_en else "0"
                )
                rx0.attrs["bb_dc_offset_tracking_en"].value = (
                    "1" if config.bb_dc_offset_tracking_en else "0"
                )

        # Calculate buffer timing
        time_to_fill_buffer = self.sdr.rx_buffer_size / self.sdr.sample_rate
        logger.info(
            f"Pluto SDR configured - Buffer refill time: {time_to_fill_buffer * 1e3:.3f} ms"
        )
        logger.info(f"  RX LO: {self.sdr.rx_lo / 1e6:.1f} MHz")
        logger.info(f"  TX LO: {self.sdr.tx_lo / 1e6:.1f} MHz")
        logger.info(f"  Sample rate: {self.sdr.sample_rate / 1e6:.2f} MS/s")
        logger.info(f"  RX buffer size: {self.sdr.rx_buffer_size} samples")

        self._configured = True

    def transmit(self, samples: np.ndarray) -> None:
        """Transmit IQ samples.

        Args:
            samples: Complex IQ samples to transmit
        """
        if not self._configured:
            raise RuntimeError("Radio not configured. Call configure() first.")
        self.sdr.tx(samples)

    def receive(self) -> np.ndarray:
        """Receive IQ samples.

        Returns:
            Complex IQ samples received (size = rx_buffer_size)
        """
        if not self._configured:
            raise RuntimeError("Radio not configured. Call configure() first.")
        return self.sdr.rx()

    def close(self) -> None:
        """Close and cleanup radio resources."""
        if hasattr(self, "sdr"):
            del self.sdr
        logger.info("Pluto SDR closed")
