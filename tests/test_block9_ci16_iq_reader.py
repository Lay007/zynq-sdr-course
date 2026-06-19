from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


MODULE_DIR = Path(__file__).resolve().parents[1] / "blocks" / "block_09_recording_and_analysis_tools" / "python"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from lab_9_2_read_ci16_iq_and_analyze import (  # noqa: E402
    compute_metrics,
    read_ci16,
)


def write_ci16(path: Path, x: np.ndarray, *, i_first: bool = True) -> None:
    i = np.clip(np.round(np.real(x) * 32767.0), -32768, 32767).astype("<i2")
    q = np.clip(np.round(np.imag(x) * 32767.0), -32768, 32767).astype("<i2")
    interleaved = np.empty(2 * len(x), dtype="<i2")
    if i_first:
        interleaved[0::2] = i
        interleaved[1::2] = q
    else:
        interleaved[0::2] = q
        interleaved[1::2] = i
    interleaved.tofile(path)


def test_read_ci16_restores_complex_samples_and_metrics(tmp_path: Path) -> None:
    sample_rate_hz = 1_000_000
    n = 8192
    tone_hz = 120_000.0
    t = np.arange(n) / sample_rate_hz
    x = 0.5 * np.exp(1j * 2.0 * np.pi * tone_hz * t)
    iq_path = tmp_path / "test_iq.ci16"
    write_ci16(iq_path, x, i_first=True)

    manifest = {
        "dataset_id": "test_ci16_iq",
        "format": "ci16",
        "endianness": "little",
        "i_first": True,
        "sample_rate_hz": sample_rate_hz,
        "center_frequency_hz": 100_000_000,
        "signal": {"expected_signal_offset_hz": tone_hz},
        "processing": {"fft_length": 8192},
    }

    y = read_ci16(iq_path, manifest)
    metrics = compute_metrics(y, manifest, iq_path=iq_path, manifest_path=tmp_path / "manifest.yaml")

    assert len(y) == n
    assert metrics.measured_peak_hz == pytest.approx(tone_hz, abs=100.0)
    assert metrics.sample_count_read == n
    assert metrics.duration_s == pytest.approx(n / sample_rate_hz, abs=1e-6)
    assert metrics.center_frequency_hz == 100_000_000
