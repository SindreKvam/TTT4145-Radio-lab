"""Configuration system for radiolab.

Provides dataclasses for all configuration parameters and TOML file loading.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PhyConfig:
    """Physical layer configuration."""

    modulation_order: int = 4  # M in M-QAM
    samples_per_symbol: int = 8  # Oversampling factor
    rrc_rolloff: float = 0.2  # Root-raised cosine rolloff factor
    rrc_span: int = 10  # Filter span in symbols
    pll_preamble_length: int = 1200  # PLL sync preamble length in symbols
    pll_kp: float = 0.0222  # PLL proportional gain
    pll_ki: float = 0.00024  # PLL integral gain
    nasa_codeword_bits: int = 32  # NASA sync codeword length (32, 36, or 64)

    def __post_init__(self):
        """Validate configuration."""
        if self.modulation_order not in [4, 16, 64, 256]:
            raise ValueError(
                f"Unsupported modulation order: {self.modulation_order}. "
                f"Must be one of [4, 16, 64, 256]"
            )
        if self.nasa_codeword_bits not in [32, 36, 64]:
            raise ValueError(
                f"Unsupported NASA codeword length: {self.nasa_codeword_bits}. "
                f"Must be one of [32, 36, 64]"
            )


@dataclass
class RadioConfig:
    """Radio hardware configuration."""

    rx_lo: int = 2_000_000_000  # RX local oscillator frequency (Hz)
    tx_lo: int = 2_000_000_000  # TX local oscillator frequency (Hz)
    tx_gain: int = -30  # TX hardware gain (dB)
    rx_rf_bandwidth: int = 4_000_000  # RX RF bandwidth (Hz)
    tx_cyclic_buffer: bool = True  # Enable TX cyclic buffer mode
    gain_control_mode: str = "manual"  # Gain control mode
    quadrature_tracking_en: bool = False  # Quadrature tracking
    rf_dc_offset_tracking_en: bool = True  # RF DC offset tracking
    bb_dc_offset_tracking_en: bool = True  # Baseband DC offset tracking
    uri: str = "usb:"  # Radio device URI


@dataclass
class AppConfig:
    """Application layer configuration."""

    image_path: str = ""  # Path to image file (empty means use default)
    image_scale: float = 0.02  # Image scaling factor
    use_camera: bool = False  # Use camera instead of static image
    camera_device: int = 0  # Camera device ID


@dataclass
class GuiConfig:
    """GUI configuration."""

    update_rate_ms: int = 50  # GUI update rate in milliseconds (20 FPS)
    queue_maxsize: int = 10  # Maximum queue size for backpressure
    plot_history_length: int = 2000  # Number of samples to show in time plots


@dataclass
class Config:
    """Master configuration containing all subsystem configs."""

    phy: PhyConfig
    radio: RadioConfig
    app: AppConfig
    gui: GuiConfig

    @classmethod
    def default(cls) -> "Config":
        """Create default configuration."""
        return cls(
            phy=PhyConfig(),
            radio=RadioConfig(),
            app=AppConfig(),
            gui=GuiConfig(),
        )

    @classmethod
    def from_toml(cls, path: Path) -> "Config":
        """Load configuration from TOML file.

        Args:
            path: Path to TOML configuration file

        Returns:
            Config instance with values from file
        """
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            try:
                import tomli as tomllib  # Fallback for Python < 3.11
            except ImportError:
                raise ImportError(
                    "TOML support requires Python 3.11+ or 'tomli' package. "
                    "Install with: pip install tomli"
                )

        with open(path, "rb") as f:
            data = tomllib.load(f)

        return cls(
            phy=PhyConfig(**data.get("phy", {})),
            radio=RadioConfig(**data.get("radio", {})),
            app=AppConfig(**data.get("app", {})),
            gui=GuiConfig(**data.get("gui", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "phy": self.phy.__dict__,
            "radio": self.radio.__dict__,
            "app": self.app.__dict__,
            "gui": self.gui.__dict__,
        }
