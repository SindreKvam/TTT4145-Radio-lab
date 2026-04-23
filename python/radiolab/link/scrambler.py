import numpy as np


class PayloadScrambler:
    def __init__(
        self,
        seed: int,
        polynomial: int,
        width: int = 7,
        enabled: bool = True,
    ) -> None:
        if width <= 0:
            raise ValueError("Scrambler width must be positive.")

        mask = (1 << width) - 1
        self.width = width
        self.enabled = enabled
        self.seed = seed & mask
        self.tap_mask = polynomial & mask

        if self.seed == 0:
            raise ValueError("Scrambler seed must be non-zero.")
        if self.tap_mask == 0:
            raise ValueError("Scrambler polynomial must select at least one tap.")

    def scramble_symbols(
        self, symbols: np.ndarray, modulation_order: int
    ) -> np.ndarray:
        if not self.enabled:
            return np.asarray(symbols, dtype=int)

        bits_per_symbol = int(np.log2(modulation_order))
        if (1 << bits_per_symbol) != modulation_order:
            raise ValueError("Modulation order must be a power of two.")

        out = np.asarray(symbols, dtype=int).copy()
        state = self.seed

        for idx in range(out.size):
            keystream_symbol = 0
            for _ in range(bits_per_symbol):
                keystream_symbol = (keystream_symbol << 1) | (state & 1)
                state = self._lfsr_step(state)

            out[idx] = out[idx] ^ keystream_symbol

        return out

    def descramble_symbols(
        self, symbols: np.ndarray, modulation_order: int
    ) -> np.ndarray:
        return self.scramble_symbols(symbols, modulation_order)

    def _lfsr_step(self, state: int) -> int:
        feedback = (state & self.tap_mask).bit_count() & 1
        return (state >> 1) | (feedback << (self.width - 1))
