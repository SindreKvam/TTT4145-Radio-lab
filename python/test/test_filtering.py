import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from commpy.filters import rrcosfilter

logger = logging.getLogger(__name__)

output_folder = Path(__file__).parent / "pytest-output/"
output_folder.mkdir(parents=True, exist_ok=True)


# @pytest.mark.parametrize("beta", [0.2, 0.707, 1])
@pytest.mark.parametrize("span", [4, 8, 10])
@pytest.mark.parametrize("sps", [4, 8, 16])
def test_matched_filter(span, sps):
    _, rrc_coeff_0_2 = rrcosfilter(span * sps + 1, alpha=0.2, Ts=sps, Fs=1.0)
    _, rrc_coeff_0_707 = rrcosfilter(span * sps + 1, alpha=0.707, Ts=sps, Fs=1.0)
    _, rrc_coeff_1 = rrcosfilter(span * sps + 1, alpha=1.0, Ts=sps, Fs=1.0)

    pytest.approx(1, np.sum(rrc_coeff_0_2))
    pytest.approx(1, np.sum(rrc_coeff_0_707))
    pytest.approx(1, np.sum(rrc_coeff_1))

    plt.figure()
    plt.grid()
    # plt.stem(rrc_coeff_0_2, label="$\\beta=0.2$", markerfmt="C0")
    # plt.stem(rrc_coeff_0_707, label="$\\beta=0.707$", markerfmt="C1")
    # plt.stem(rrc_coeff_1, label="$\\beta=1.0$", markerfmt="C2")
    plt.plot(rrc_coeff_0_2, "o", label="$\\beta=0.2$", alpha=0.8)
    plt.plot(rrc_coeff_0_707, "x", label="$\\beta=0.707$", alpha=0.8)
    plt.plot(rrc_coeff_1, "*", label="$\\beta=1.0$", alpha=0.8)

    plt.suptitle("Root Raised Cosine impulse response")
    plt.title(f"span = {span}, sps = {sps}")
    plt.xlabel("Coefficient")
    plt.ylabel("Amplitude")
    plt.legend()
    plt.savefig(output_folder / f"rrc_span={span}_sps={sps}.png", dpi=300)
    plt.close("all")
