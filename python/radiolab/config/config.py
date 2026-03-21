from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class PhyConfig:
    """Configurations for PHY layer"""

    modulation_order: int = 4
    samples_per_symbol: int = 8  # sps
    pll_preamble_length: int = 600
    codeword_length: int = 64
    codeword_corr_threshold: int = 1000 // np.log2(modulation_order)

    rrc_beta: float = 0.2
    rrc_span: int = 10


@dataclass
class RadioConfig:
    """Configuration directly on hardware layer"""

    rx_rf_bandwidth: int = 40_000_000
    sample_rate: int = 20_000_000
    rx_buffer_size: int = 10240 * 8 * 4
    rx_lo_hz: int = 2_400_000_000
    tx_lo_hz: int = 2_400_000_000
    tx_cyclic_buffer: bool = False
    tx_hardwaregain_chan0 = -30
    gain_control_mode_chan0 = (
        "manual"  # Valid configurations: ["manual", "slow_attack", "fast_attack"]
    )

    quadrature_tracking_en = False

    time_to_fill_buffer: float = rx_buffer_size / sample_rate


@dataclass
class GuiConfig:
    """Configurations for the GUI"""

    update_rate_ms = 20


@dataclass
class Config:
    """Configurations"""

    phy: PhyConfig
    radio: RadioConfig
    gui: GuiConfig

    @classmethod
    def default(cls) -> "Config":
        """Create default configuration"""
        return cls(phy=PhyConfig(), radio=RadioConfig(), gui=GuiConfig())

    def to_dict(self) -> dict[str, Any]:
        return {
            "phy": self.phy.__dict__,
            "radio": self.radio.__dict__,
            "gui": self.gui.__dict__,
        }
