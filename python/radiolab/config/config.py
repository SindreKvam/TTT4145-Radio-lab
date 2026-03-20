from dataclasses import dataclass
from typing import Any


@dataclass
class PhyConfig:
    """Configurations for PHY layer"""

    modulation_order: int = 4
    samples_per_symbol: int = 8  # sps
    pll_preamble_length: int = 600
    codeword_length: int = 64
    codeword_corr_threshold: int = 1000

    rrc_beta: float = 0.2
    rrc_span: int = 10


@dataclass
class RadioConfig:
    """Configuration directly on hardware layer"""

    sample_rate = 30_000_000
    rx_lo_hz = 2_400_000_000
    tx_lo_hz = 2_400_000_000
    rx_buffer_size = 4096 * 8 * 2

    time_to_fill_buffer = rx_buffer_size / sample_rate


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
