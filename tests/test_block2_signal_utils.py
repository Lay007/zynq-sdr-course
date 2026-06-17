from __future__ import annotations

import sys
from pathlib import Path

import pytest


MODULE_DIR = Path(__file__).resolve().parents[1] / "blocks" / "block_02_signals_and_sampling" / "python"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from block2_signal_utils import (  # noqa: E402
    alias_frequency_hz,
    estimate_negative_peak_hz,
    estimate_peak_hz,
    estimate_positive_peak_hz,
    make_complex_tone,
    make_real_tone,
)


def test_alias_frequency_wraps_above_nyquist() -> None:
    assert alias_frequency_hz(620_000.0, 1_000_000.0) == pytest.approx(-380_000.0)
    assert alias_frequency_hz(1_180_000.0, 1_000_000.0) == pytest.approx(180_000.0)


def test_complex_tone_peak_estimate_stays_near_expected_frequency() -> None:
    sample_rate_hz = 1_000_000.0
    tone_hz = 120_000.0
    x = make_complex_tone(sample_rate_hz, 16_384, tone_hz, amplitude=0.8)
    peak_hz = estimate_peak_hz(x, sample_rate_hz, exclude_dc_hz=5_000.0)
    assert peak_hz == pytest.approx(tone_hz, abs=20.0)


def test_real_tone_creates_mirrored_positive_and_negative_peaks() -> None:
    sample_rate_hz = 1_000_000.0
    tone_hz = 120_000.0
    x = make_real_tone(sample_rate_hz, 16_384, tone_hz, amplitude=0.8).astype(complex)
    positive_peak_hz = estimate_positive_peak_hz(x, sample_rate_hz)
    negative_peak_hz = estimate_negative_peak_hz(x, sample_rate_hz)
    assert positive_peak_hz == pytest.approx(tone_hz, abs=20.0)
    assert negative_peak_hz == pytest.approx(-tone_hz, abs=20.0)
