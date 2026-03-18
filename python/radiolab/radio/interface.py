"""Abstract radio interface for hardware abstraction."""

from abc import ABC, abstractmethod

import numpy as np


class RadioInterface(ABC):
    """Abstract interface for SDR hardware.

    This allows swapping different radio backends (Pluto, USRP, simulation, etc.)
    """

    @abstractmethod
    def configure(self, **kwargs) -> None:
        """Configure the radio with given parameters.

        Args:
            **kwargs: Radio-specific configuration parameters
        """
        pass

    @abstractmethod
    def transmit(self, samples: np.ndarray) -> None:
        """Transmit samples.

        Args:
            samples: Complex IQ samples to transmit
        """
        pass

    @abstractmethod
    def receive(self) -> np.ndarray:
        """Receive samples.

        Returns:
            Complex IQ samples received
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close and cleanup radio resources."""
        pass
