"""Combined TX/RX pipeline process for full-duplex operation."""

import logging
import multiprocessing as mp
import time

import numpy as np

from radiolab.app.sources import image_path, image_to_m_bit
from radiolab.config.config import Config
from radiolab.phy.rx import ModemRx
from radiolab.phy.tx import ModemTx
from radiolab.radio.pluto import PlutoRadio

logger = logging.getLogger(__name__)


def txrx_pipeline_process(
    config: Config,
    gui_queue: mp.Queue,
    stop_event: mp.Event,
):
    """Combined TX/RX pipeline process - full-duplex operation.

    This process:
    1. Continuously transmits frames in a tight loop (no cyclic buffer)
    2. Receives and processes data interleaved with TX
    3. Sends all intermediate results to GUI

    Args:
        config: System configuration
        gui_queue: Queue for sending data to GUI
        stop_event: Event to signal shutdown
    """
    logger.info("TXRX Pipeline starting...")

    try:
        # Initialize components
        tx_modem = ModemTx(config.phy)
        rx_modem = ModemRx(config.phy)
        radio = PlutoRadio(config.radio.uri)

        # ========== TX SETUP ==========
        # Prepare image data
        img_path = config.app.image_path if config.app.image_path else image_path
        m_bit_image, img_width, img_height = image_to_m_bit(
            str(img_path), config.phy.modulation_order, scale=config.app.image_scale
        )
        payload = m_bit_image.flatten().astype(int)

        logger.info(
            f"TX: Image loaded - {img_width}x{img_height}, {len(payload)} symbols"
        )

        # Build complete TX frame
        tx_samples = tx_modem.build_frame(payload)
        num_symbols = (
            len(tx_modem.get_nasa_codeword())
            + len(tx_modem.get_pll_preamble())
            + len(payload)
        )

        logger.info(f"TX: Frame built - {len(tx_samples)} samples")

        # ========== RX SETUP ==========
        # Generate reference templates for sync
        nasa_code = tx_modem.get_nasa_codeword()
        pll_preamble = tx_modem.get_pll_preamble()

        # Upsample and pulse-shape the codeword for correlation template
        upsampled_code = tx_modem.upsample(nasa_code)
        pulse_shaped_code = tx_modem.pulse_shape(upsampled_code)
        matched_code = np.convolve(pulse_shaped_code, rx_modem.rrc_coeff, mode="same")
        template = upsampled_code  # Use oversampled version for template

        # Configure radio for RX (buffer size for receiving)
        rx_buffer_size = config.phy.samples_per_symbol * 10000
        radio.configure(config.radio, rx_buffer_size)

        logger.info(f"RX: Buffer size = {rx_buffer_size} samples")
        logger.info(f"RX: Template length = {len(template)} samples")

        # ========== SLIDING BUFFER FOR NON-CYCLIC TX ==========
        # Calculate minimum buffer size to hold one complete frame
        frame_size = len(tx_samples)  # Total samples in one frame
        min_buffer_size = frame_size + 20000  # Extra margin for correlation overlap
        logger.info(f"RX: Sliding buffer size = {min_buffer_size} samples")

        # Sliding buffer to accumulate samples
        sample_buffer = np.zeros(min_buffer_size, dtype=complex)
        buffer_write_pos = 0
        buffer_filled = False
        waiting_for_frame = False
        frame_start_detected = None
        accumulated_samples = 0

        # Send TX metadata to GUI (once)
        try:
            gui_queue.put_nowait(
                {
                    "type": "tx_info",
                    "num_symbols": num_symbols,
                    "num_samples": len(tx_samples),
                    "image_shape": (img_height, img_width),
                    "payload": payload,
                }
            )

            # Send TX constellation (modulated symbols before pulse shaping)
            # These are the QPSK symbols that form the image
            try:
                gui_queue.put_nowait(
                    {
                        "type": "tx_constellation",
                        "symbols": tx_modem.modulate_payload(payload),
                    }
                )
            except:
                pass  # Queue full, skip

        except:
            pass  # GUI queue full, skip

        logger.info("TXRX Pipeline ready - entering TX/RX loop")

        frame_count = 0
        tx_count = 0

        # ========== CONTINUOUS TX/RX LOOP ==========
        # Transmit frame once, then accumulate RX samples until we have complete frame
        while not stop_event.is_set():
            try:
                # ===== TRANSMIT ONE FRAME =====
                radio.transmit(tx_samples)
                tx_count += 1

                if tx_count % 100 == 0:
                    logger.debug(f"TX: Transmitted {tx_count} frames")

                # ===== ACCUMULATE RX SAMPLES =====
                # Reset buffer for new frame
                buffer_write_pos = 0
                accumulated_samples = 0
                samples_needed = frame_size + 10000  # Frame + margin

                # Receive until we have enough samples
                while accumulated_samples < samples_needed and not stop_event.is_set():
                    rx_samples = radio.receive()

                    # Add samples to buffer (with wraparound)
                    samples_to_add = len(rx_samples)
                    end_pos = buffer_write_pos + samples_to_add

                    if end_pos <= min_buffer_size:
                        sample_buffer[buffer_write_pos:end_pos] = rx_samples
                    else:
                        # Wrap around to beginning of buffer
                        first_part = min_buffer_size - buffer_write_pos
                        sample_buffer[buffer_write_pos:] = rx_samples[:first_part]
                        sample_buffer[: samples_to_add - first_part] = rx_samples[
                            first_part:
                        ]

                    buffer_write_pos = (
                        buffer_write_pos + samples_to_add
                    ) % min_buffer_size
                    accumulated_samples += samples_to_add

                    if accumulated_samples >= samples_needed:
                        break

                # ===== PROCESS RECEIVED FRAME =====
                # Matched filtering on received buffer
                filtered_samples = rx_modem.matched_filter(sample_buffer)

                # Frame synchronization
                frame_start, correlation = rx_modem.detect_frame_start(
                    filtered_samples, template
                )

                # Extract frame starting from frame_start
                # Buffer is sized to hold complete frame, so no wraparound needed
                frame_samples = filtered_samples[frame_start : frame_start + frame_size]

                # Account for filter delay and timing
                bits_per_symbol = int(np.log2(config.phy.modulation_order))
                timing_offset = config.phy.samples_per_symbol * (bits_per_symbol - 1)

                # Rotate samples to align frame
                aligned_samples = np.concatenate(
                    (frame_samples[timing_offset:], frame_samples[:timing_offset])
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
                        "rx_constellation": symbols_before_pll[:500],
                        "decoded_bits": decoded_bits,
                    }
                    gui_queue.put_nowait(gui_data)
                except:
                    pass  # Queue full, skip this frame

                # No sleep - transmit as fast as possible

            except Exception as e:
                logger.error(f"TXRX processing error: {e}", exc_info=True)
                time.sleep(0.1)

    except Exception as e:
        logger.error(f"TXRX Pipeline error: {e}", exc_info=True)
    finally:
        if "radio" in locals():
            radio.close()
        logger.info("TXRX Pipeline stopped")
