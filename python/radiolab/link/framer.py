"""Frame packing helpers for payload and metadata."""

import struct

import numpy as np
from hamming import Hamming


class Framer:
    FRAME_SYNC_WORD = 0xA55A
    WINDOW_SIZE = 16
    DATA_WORDS = 11
    CODED_WORDS = 16
    HEADER_BITS = CODED_WORDS * 16

    def __init__(self) -> None:
        self.hamming = Hamming(self.WINDOW_SIZE)

    def flatten_image(self, image: np.ndarray):
        """Return a 1D array of the original image"""

        return np.ravel(image).astype(int)

    def pack_frame(
        self,
        payload_symbols: np.ndarray,
        metadata: dict,
        modulation_order: int,
        frame_counter: int,
    ) -> np.ndarray:
        """Prefix payload with a Hamming-protected metadata header."""

        header_words = self._build_header_words(
            metadata,
            payload_symbol_count=int(len(payload_symbols)),
            modulation_order=modulation_order,
            frame_counter=frame_counter,
        )
        coded_header_words = np.asarray(
            self.hamming.encode_words(header_words), dtype=np.uint16
        )
        header_symbols = self._words_to_symbols(coded_header_words, modulation_order)

        return np.concatenate((header_symbols.astype(int), payload_symbols.astype(int)))

    def pack_header(
        self,
        metadata: dict,
        payload_symbol_count: int,
        modulation_order: int,
        frame_counter: int,
    ) -> np.ndarray:
        header_words = self._build_header_words(
            metadata,
            payload_symbol_count=payload_symbol_count,
            modulation_order=modulation_order,
            frame_counter=frame_counter,
        )
        coded_header_words = np.asarray(
            self.hamming.encode_words(header_words), dtype=np.uint16
        )
        return self._words_to_symbols(coded_header_words, modulation_order)

    def unpack_frame(
        self,
        received_symbols: np.ndarray,
        modulation_order: int,
    ) -> tuple[dict, np.ndarray] | tuple[None, None]:
        """Decode metadata header and return (metadata, payload_symbols)."""

        bits_per_symbol = int(np.log2(modulation_order))
        header_symbol_count = int(np.ceil(self.HEADER_BITS / bits_per_symbol))

        if len(received_symbols) < header_symbol_count:
            return None, None

        header_symbols = np.asarray(
            received_symbols[:header_symbol_count], dtype=np.uint16
        )
        header_bits = self._symbols_to_bits(
            header_symbols, bits_per_symbol, self.HEADER_BITS
        )
        packed_bytes = np.packbits(header_bits, bitorder="big").tobytes()
        coded_words = np.frombuffer(packed_bytes, dtype=">u2").astype(np.uint16)

        decoded_words = np.asarray(
            self.hamming.decode_words(coded_words), dtype=np.uint16
        )
        metadata = self._parse_header_words(decoded_words)
        if metadata is None:
            return None, None

        payload_symbol_count = metadata["payload_symbols"]
        payload_start = header_symbol_count
        payload_stop = payload_start + payload_symbol_count
        if len(received_symbols) < payload_stop:
            return None, None

        payload = np.asarray(received_symbols[payload_start:payload_stop], dtype=int)
        return metadata, payload

    def unpack_header(
        self, received_symbols: np.ndarray, modulation_order: int
    ) -> tuple[dict, int] | tuple[None, None]:
        bits_per_symbol = int(np.log2(modulation_order))
        header_symbol_count = int(np.ceil(self.HEADER_BITS / bits_per_symbol))

        if len(received_symbols) < header_symbol_count:
            return None, None

        header_symbols = np.asarray(
            received_symbols[:header_symbol_count], dtype=np.uint16
        )
        header_bits = self._symbols_to_bits(
            header_symbols, bits_per_symbol, self.HEADER_BITS
        )
        packed_bytes = np.packbits(header_bits, bitorder="big").tobytes()
        coded_words = np.frombuffer(packed_bytes, dtype=">u2").astype(np.uint16)

        decoded_words = np.asarray(
            self.hamming.decode_words(coded_words), dtype=np.uint16
        )
        metadata = self._parse_header_words(decoded_words)
        if metadata is None:
            return None, None

        return metadata, header_symbol_count

    def _build_header_words(
        self,
        metadata: dict,
        payload_symbol_count: int,
        modulation_order: int,
        frame_counter: int,
    ) -> np.ndarray:
        width = int(metadata["img_width"])
        height = int(metadata["img_height"])
        channels = int(metadata.get("channels", 3))

        header = struct.pack(
            ">HIHHBBI6x",
            self.FRAME_SYNC_WORD,
            frame_counter & 0xFFFFFFFF,
            width,
            height,
            channels,
            0,
            payload_symbol_count,
        )

        return np.frombuffer(header, dtype=">u2").astype(np.uint16)

    def _parse_header_words(self, words: np.ndarray) -> dict | None:
        if len(words) != self.DATA_WORDS:
            return None

        payload = words.astype(">u2").tobytes()
        (
            frame_sync_word,
            frame_counter,
            width,
            height,
            channels,
            _reserved,
            payload_symbols,
        ) = struct.unpack(">HIHHBBI6x", payload)

        if frame_sync_word != self.FRAME_SYNC_WORD:
            return None

        if width <= 0 or height <= 0:
            return None
        if channels not in (1, 3):
            return None
        expected_payload = int(width) * int(height) * int(channels)
        if int(payload_symbols) != expected_payload:
            return None

        return {
            "frame_counter": int(frame_counter),
            "img_width": int(width),
            "img_height": int(height),
            "channels": int(channels),
            "payload_symbols": int(payload_symbols),
        }

    @staticmethod
    def _words_to_symbols(words: np.ndarray, modulation_order: int) -> np.ndarray:
        bits_per_symbol = int(np.log2(modulation_order))
        bytes_data = words.astype(">u2").tobytes()
        bits = np.unpackbits(np.frombuffer(bytes_data, dtype=np.uint8), bitorder="big")

        pad_len = (-len(bits)) % bits_per_symbol
        if pad_len:
            bits = np.concatenate((bits, np.zeros(pad_len, dtype=np.uint8)))

        bit_groups = bits.reshape(-1, bits_per_symbol)
        powers = (1 << np.arange(bits_per_symbol - 1, -1, -1)).astype(np.uint16)
        return bit_groups.dot(powers).astype(np.uint16)

    @staticmethod
    def _symbols_to_bits(
        symbols: np.ndarray, bits_per_symbol: int, bit_count: int
    ) -> np.ndarray:
        shifts = np.arange(bits_per_symbol - 1, -1, -1, dtype=np.uint16)
        bits = ((symbols[:, None] >> shifts) & 1).astype(np.uint8).reshape(-1)
        return bits[:bit_count]
