import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from commpy.filters import rrcosfilter

logger = logging.getLogger(__name__)

output_folder = Path(__file__).parent / "pytest-output/"
output_folder.mkdir(parents=True, exist_ok=True)


@pytest.mark.parametrize("beta", [0.2, 0.707])
@pytest.mark.parametrize("span", [4, 8, 10])
@pytest.mark.parametrize("sps", [4, 8, 16])
def test_matched_filter(beta, span, sps):
    rrc, rrc_coeff = rrcosfilter(span * sps + 1, alpha=beta, Ts=sps, Fs=1.0)

    pytest.approx(1, np.sum(rrc_coeff))

    plt.figure()
    plt.stem(rrc_coeff)
    plt.title(f"$\\beta = {beta}$, span = {span}, sps = {sps}")
    plt.grid()
    plt.savefig(output_folder / f"rrc_{beta}_{span}_{sps}.png")
    plt.close("all")
