from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from ofdm_cfo_pilot_bias import pilot_phase  # noqa: E402


def test_no_cfo_estimate_is_the_channel_angle() -> None:
    result = pilot_phase(120.0, 0.0, 2)
    assert abs(result["bias"]) < 1e-6
    assert abs(result["estimate"] - 120.0 / 180.0 * 32768.0) < 1e-6


def test_pilots_alone_are_unbiased_under_cfo() -> None:
    for ppm in (500.0, 2000.0, 4000.0):
        assert abs(pilot_phase(30.0, ppm, 8, with_data=False)["bias"]) < 0.5


def test_data_carriers_bias_the_estimate_in_proportion_to_cfo() -> None:
    biases = [pilot_phase(30.0, ppm, 8)["bias"] for ppm in (500.0, 1000.0, 2000.0, 4000.0)]
    # Grows with the offset; about 0.5 units (pi = 2^15) per ppm for small offsets.
    assert biases == sorted(biases)
    assert 240.0 < biases[0] < 270.0
    # The RTL bench measured -23533 at 120 degrees / 500 ppm / 8 symbols.
    assert abs(pilot_phase(120.0, 500.0, 8)["estimate"] - (-23533)) < 16
