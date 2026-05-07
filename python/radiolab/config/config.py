from dataclasses import dataclass
from typing import Any


@dataclass
class PhyConfig:
    """Configurations for PHY layer"""

    modulation_order: int = 16
    samples_per_symbol: int = 8  # sps
    pll_preamble_length: int = 600
    codeword_length: int = 64
    codeword_corr_threshold: int = 800  # 800 for 4-QAM

    rrc_beta: float = 0.707
    rrc_span: int = 10

    scrambler_enabled: bool = True
    scrambler_seed: int = 0x7F
    scrambler_polynomial: int = 0x89
    scrambler_width: int = 7

    tx_static_image_scale: float = 0.1
    tx_camera_image_scale: float = 0.4
    tx_camera_capture_width: int = 320
    tx_camera_capture_height: int = 240

    tx_constellation_preview_len: int = 250


@dataclass
class RadioConfig:
    """Configuration directly on hardware layer"""

    rx_rf_bandwidth: int = 20_000_000
    sample_rate: int = 10_000_000
    rx_buffer_size: int = 400_000
    rx_lo_hz: int = 2_472_000_000  # Centre of channel 13: 2.472 GHz
    tx_lo_hz: int = 2_472_000_000  # Centre of channel 14: 2.484 GHz
    tx_cyclic_buffer: bool = False
    tx_hardwaregain_chan0 = 0
    gain_control_mode_chan0 = (
        "fast_attack"  # Valid configurations: ["manual", "slow_attack", "fast_attack"]
    )

    quadrature_tracking_en = False

    time_to_fill_buffer: float = rx_buffer_size / sample_rate


@dataclass
class GuiConfig:
    """Configurations for the GUI"""

    update_rate_ms = 20
    tx_queue_size: int = 8
    rx_queue_size: int = 8
    control_queue_size: int = 8


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
