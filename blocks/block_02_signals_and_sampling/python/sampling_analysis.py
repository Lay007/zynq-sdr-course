#!/usr/bin/env python3
"""Lab 2.1 - Sampling axis and interpretation checks."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from block2_signal_utils import clipping_fraction, estimate_peak_hz, make_complex_tone, rms_dbfs, spectrum_db


ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"


@dataclass(frozen=True)
class SamplingConfig:
    correct_sample_rate_hz: float = 1_000_000.0
    wrong_sample_rate_hz: float = 800_000.0
    sample_count: int = 16384
    expected_tone_hz: float = 123_456.0
    amplitude: float = 0.72
    dc_offset: complex = complex(0.018, -0.011)
    noise_rms: float = 0.004
    seed: int = 21


@dataclass(frozen=True)
class SamplingMetrics:
    expected_tone_hz: float
    measured_peak_correct_hz: float
    measured_peak_wrong_hz: float
    correct_frequency_error_hz: float
    wrong_interpretation_error_hz: float
    rms_level_dbfs: float
    clipping_fraction: float


def make_signal(cfg: SamplingConfig) -> np.ndarray:
    rng = np.random.default_rng(cfg.seed)
    x = make_complex_tone(
        cfg.correct_sample_rate_hz,
        cfg.sample_count,
        cfg.expected_tone_hz,
        amplitude=cfg.amplitude,
    )
    noise = cfg.noise_rms * (
        rng.standard_normal(cfg.sample_count) + 1j * rng.standard_normal(cfg.sample_count)
    )
    return x + cfg.dc_offset + noise


def save_time_plot(path: Path, x: np.ndarray, cfg: SamplingConfig) -> None:
    shown = min(280, len(x))
    t_us = np.arange(shown) / cfg.correct_sample_rate_hz * 1e6
    plt.figure(figsize=(7.2, 4.3))
    plt.plot(t_us, np.real(x[:shown]), label="I")
    plt.plot(t_us, np.imag(x[:shown]), label="Q")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Time, us")
    plt.ylabel("Amplitude, FS")
    plt.title("Lab 2.1 - Time-domain sampling preview")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def save_frequency_axis_plot(path: Path, x: np.ndarray, cfg: SamplingConfig) -> None:
    freq_correct, mag_db = spectrum_db(x, cfg.correct_sample_rate_hz)
    freq_wrong, _ = spectrum_db(x, cfg.wrong_sample_rate_hz)
    plt.figure(figsize=(8.0, 4.8))
    plt.plot(freq_correct / 1e3, mag_db, label="correct Fs axis")
    plt.plot(freq_wrong / 1e3, mag_db, label="wrong Fs axis", alpha=0.75)
    plt.axvline(cfg.expected_tone_hz / 1e3, linestyle="--", label="expected tone")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Baseband frequency, kHz")
    plt.ylabel("Magnitude, dBFS")
    plt.title("Lab 2.1 - Correct vs incorrect sampling-rate interpretation")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def main() -> int:
    cfg = SamplingConfig()
    x = make_signal(cfg)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    measured_correct = estimate_peak_hz(x, cfg.correct_sample_rate_hz, exclude_dc_hz=5_000.0)
    measured_wrong = estimate_peak_hz(x, cfg.wrong_sample_rate_hz, exclude_dc_hz=5_000.0)
    metrics = SamplingMetrics(
        expected_tone_hz=cfg.expected_tone_hz,
        measured_peak_correct_hz=measured_correct,
        measured_peak_wrong_hz=measured_wrong,
        correct_frequency_error_hz=measured_correct - cfg.expected_tone_hz,
        wrong_interpretation_error_hz=measured_wrong - cfg.expected_tone_hz,
        rms_level_dbfs=rms_dbfs(x),
        clipping_fraction=clipping_fraction(x),
    )

    save_time_plot(ASSET_DIR / "lab21_sampling_time_domain.png", x, cfg)
    save_frequency_axis_plot(ASSET_DIR / "lab21_sampling_frequency_axis.png", x, cfg)
    metrics_path = ASSET_DIR / "lab21_sampling_metrics.json"
    config_payload = asdict(cfg)
    config_payload["dc_offset"] = {
        "i": float(np.real(cfg.dc_offset)),
        "q": float(np.imag(cfg.dc_offset)),
    }
    metrics_path.write_text(
        json.dumps({"config": config_payload, "metrics": asdict(metrics)}, indent=2),
        encoding="utf-8",
    )

    print("Lab 2.1 - Sampling axis and interpretation checks")
    print(f"Expected tone: {cfg.expected_tone_hz:.3f} Hz")
    print(f"Measured peak with correct Fs: {metrics.measured_peak_correct_hz:.3f} Hz")
    print(f"Measured peak with wrong Fs: {metrics.measured_peak_wrong_hz:.3f} Hz")
    print(f"Correct interpretation error: {metrics.correct_frequency_error_hz:.3f} Hz")
    print(f"Wrong interpretation error: {metrics.wrong_interpretation_error_hz:.3f} Hz")
    print(f"Metrics JSON: {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
