""""""

import adi


def connect_and_configure_pluto(
    N,
    rx_lo,
    tx_lo,
    sps,
    tx_cyclic_buffer: bool = False,
) -> adi.Pluto:
    """Connect to an Adalm Pluto software defined radio and configure it"""
    sdr = adi.Pluto("usb:")

    # Configure properties
    sdr.rx_rf_bandwidth = 4000000
    sdr.rx_lo = rx_lo
    sdr.tx_lo = tx_lo
    sdr.tx_cyclic_buffer = tx_cyclic_buffer
    sdr.tx_hardwaregain_chan0 = -30
    sdr.rx_buffer_size = N * sps
    sdr.gain_control_mode_chan0 = "manual"

    phy = sdr.ctx.find_device("ad9361-phy")
    rx0 = phy.find_channel("voltage0", False)  # False => RX/input channel
    print(list(rx0.attrs.keys()))

    # disable quadrature tracking:
    rx0.attrs["quadrature_tracking_en"] = "0"

    # Disable DC tracking only if needed
    rx0.attrs["rf_dc_offset_tracking_en"].value = "1"
    rx0.attrs["bb_dc_offset_tracking_en"].value = "1"

    time_to_fill_buffer = sdr.rx_buffer_size / sdr.sample_rate
    print(f"Time between new RX data buffer ready: {time_to_fill_buffer * 1e3:.3f} ms")

    return sdr
