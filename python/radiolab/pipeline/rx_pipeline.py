"""RX + DSP pipeline process for continuous reception and processing."""

import logging
import multiprocessing as mp
import time

import numpy as np

from radiolab.config.config import Config
from radiolab.phy.rx import ModemRx
from radiolab.phy.tx import ModemTx
from radiolab.radio.pluto import PlutoRadio

logger = logging.getLogger(__name__)


def rx_pipeline_process(
    config: Config,
    gui_queue: mp.Queue,
    stop_event: mp.Event,
):
    """RX + DSP pipeline process - continuously receives and processes data.

    Args:
        config: System configuration
        gui_queue: Queue for sending data to GUI
        stop_event: Event to signal shutdown
    """
    logger.info("RX Pipeline starting...")

    try:
        # Initialize components
        rx_modem = ModemRx(config.phy)
        tx_modem = ModemTx(config.phy)  # Need for generating templates
        radio = PlutoRadio(config.radio.uri)

        # Generate reference templates for sync
        nasa_code = tx_modem.get_nasa_codeword()
        pll_preamble = tx_modem.get_pll_preamble()

        # Upsample and pulse-shape the codeword for correlation template
        upsampled_code = tx_modem.upsample(nasa_code)
        pulse_shaped_code = tx_modem.pulse_shape(upsampled_code)
        matched_code = np.convolve(pulse_shaped_code, rx_modem.rrc_coeff, mode="same")
        template = upsampled_code  # Use oversampled version for template

        # Configure radio
        # Buffer size should be large enough to capture full frame
        buffer_size = (
            config.phy.samples_per_symbol * 10000
        )  # Adjust based on your needs
        radio.configure(config.radio, buffer_size)

        logger.info(f"RX: Buffer size = {buffer_size} samples")
        logger.info(f"RX: Template length = {len(template)} samples")
        logger.info("RX Pipeline ready")

        frame_count = 0

        # Continuous RX loop
        while not stop_event.is_set():
            try:
                # Receive samples
                rx_samples = radio.receive()

                # Matched filtering
                filtered_samples = rx_modem.matched_filter(rx_samples)

                # Frame synchronization
                frame_start, correlation = rx_modem.detect_frame_start(
                    filtered_samples, template
                )

                # Account for filter delay and timing
                bits_per_symbol = int(np.log2(config.phy.modulation_order))
                timing_offset = frame_start + config.phy.samples_per_symbol * (
                    bits_per_symbol - 1
                )

                # Rotate samples to align frame
                aligned_samples = np.concatenate(
                    (filtered_samples[timing_offset:], filtered_samples[:timing_offset])
                )

                # Remove sync code from aligned samples
                code_length_samples = len(nasa_code) * config.phy.samples_per_symbol
                aligned_samples = aligned_samples[
                    code_length_samples // 2 : -code_length_samples // 2
                ]

                # Downsample to symbol rate
                symbols = rx_modem.downsample(aligned_samples)

                # Normalize symbols
                symbols = symbols / (np.max(np.abs(symbols)) + 1e-10)

                # Phase-locked loop for carrier recovery
                phase_corrected, pll_error, pll_theta = rx_modem.phase_locked_loop(
                    symbols, preamble=pll_preamble
                )

                # Remove preamble
                payload_symbols = phase_corrected[len(pll_preamble) :]
                symbols_before_pll = symbols[len(pll_preamble) :]

                # Demodulate
                decoded_bits = rx_modem.demodulate(payload_symbols)

                frame_count += 1

                # Send data to GUI (non-blocking)
                try:
                    gui_data = {
                        "type": "rx_update",
                        "frame_count": frame_count,
                        "rx_samples": rx_samples[:2000],
                        "filtered_samples": filtered_samples[:2000],
                        "correlation": correlation,
                        "frame_start": int(frame_start),
                        "symbols_raw": symbols_before_pll[:500],
                        "symbols_pll": payload_symbols[:500],
                        "pll_error": pll_error,
                        "pll_theta": pll_theta,
                        "decoded_bits": decoded_bits,
                        "timestamp": time.time(),
                    }
                    gui_queue.put_nowait(gui_data)
                except:
                    pass  # Queue full, skip this frame

                # Small delay to avoid overwhelming the system
                time.sleep(0.001)

            except Exception as e:
                logger.error(f"RX processing error: {e}", exc_info=True)
                time.sleep(0.1)

    except Exception as e:
        logger.error(f"RX Pipeline error: {e}", exc_info=True)
    finally:
        if "radio" in locals():
            radio.close()
        logger.info("RX Pipeline stopped")
