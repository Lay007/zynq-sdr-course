from __future__ import annotations

import sys
import wave
from pathlib import Path

import numpy as np
import pytest


MODULE_DIR = Path(__file__).resolve().parents[1] / "blocks" / "block_09_recording_and_analysis_tools" / "python"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from lab_9_4_read_wav_iq_and_analyze import (  # noqa: E402
    compute_metrics,
    read_wav_iq,
)


def write_stereo_wav_iq(path: Path, x: np.ndarray, sample_rate_hz: int) -> None:
    scale = 32767.0
    i = np.clip(np.round(np.real(x) * scale), -32768, 32767).astype("<i2")
    q = np.clip(np.round(np.imag(x) * scale), -32768, 32767).astype("<i2")
    interleaved = np.empty(2 * len(x), dtype="<i2")
    interleaved[0::2] = i
    interleaved[1::2] = q
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sample_rate_hz)
        w.writeframes(interleaved.tobytes())


def test_read_wav_iq_restores_stereo_complex_samples(tmp_path: Path) -> None:
    sample_rate_hz = 1_000_000
    n = 4096
    tone_hz = 80_000.0
    t = np.arange(n) / sample_rate_hz
    x = 0.5 * np.exp(1j * 2.0 * np.pi * tone_hz * t)
    wav_path = tmp_path / "test_iq.wav"
    write_stereo_wav_iq(wav_path, x, sample_rate_hz)

    manifest = {
        "dataset_id": "test_wav_iq",
        "sample_rate_hz": sample_rate_hz,
        "center_frequency_hz": 100_000_000,
        "signal": {"expected_signal_offset_hz": tone_hz},
    }

    y, info = read_wav_iq(wav_path, manifest)
    metrics = compute_metrics(y, manifest, info, iq_path=wav_path, manifest_path=tmp_path / "manifest.yaml")

    assert len(y) == n
    assert info["channels"] == 2
    assert info["sample_width_bytes"] == 2
    assert metrics.measured_peak_hz == pytest.approx(tone_hz, abs=100.0)
    assert metrics.sample_count_read == n
    assert metrics.duration_s == pytest.approx(n / sample_rate_hz, abs=1e-6)
