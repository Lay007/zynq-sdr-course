#!/usr/bin/env python3
"""Lab 2.3 - I/Q interpretation and mirrored spectrum checks."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from block2_signal_utils import (
    estimate_negative_peak_hz,
    estimate_peak_hz,
    estimate_positive_peak_hz,
    make_complex_tone,
    spectrum_db,
)


ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"


@dataclass(frozen=True)
class IQConfig:
    sample_rate_hz: float = 1_000_000.0
    sample_count: int = 16384
    expected_tone_hz: float = 120_000.0
    amplitude: float = 0.78


@dataclass(frozen=True)
class IQMetrics:
    expected_tone_hz: float
    correct_peak_hz: float
    swapped_peak_hz: float
    real_positive_peak_hz: float
    real_negative_peak_hz: float
    correct_error_hz: float
    swapped_error_hz: float
    real_mirror_balance_hz: float


def save_time_plot(path: Path, x: np.ndarray, cfg: IQConfig) -> None:
    shown = min(220, len(x))
    t_us = np.arange(shown) / cfg.sample_rate_hz * 1e6
    plt.figure(figsize=(7.2, 4.3))
    plt.plot(t_us, np.real(x[:shown]), label="I")
    plt.plot(t_us, np.imag(x[:shown]), label="Q")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Time, us")
    plt.ylabel("Amplitude, FS")
    plt.title("Lab 2.3 - Complex I/Q components")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def save_spectra(path: Path, correct: np.ndarray, swapped: np.ndarray, real_capture: np.ndarray, cfg: IQConfig) -> None:
    plt.figure(figsize=(7.4, 4.4))
    for label, x in (
        ("correct complex IQ", correct),
        ("I/Q swapped", swapped),
        ("real-valued capture", real_capture),
    ):
        freq, mag_db = spectrum_db(x, cfg.sample_rate_hz)
        region = (freq > -260_000.0) & (freq < 260_000.0)
        plt.plot(freq[region] / 1e3, mag_db[region], label=label)
    plt.axvline(cfg.expected_tone_hz / 1e3, linestyle="--", label="expected +tone")
    plt.axvline(-cfg.expected_tone_hz / 1e3, linestyle=":", label="expected -tone")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Baseband frequency, kHz")
    plt.ylabel("Magnitude, dBFS")
    plt.title("Lab 2.3 - I/Q order mistakes and mirrored spectra")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def main() -> int:
    cfg = IQConfig()
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    correct = make_complex_tone(cfg.sample_rate_hz, cfg.sample_count, cfg.expected_tone_hz, amplitude=cfg.amplitude)
    swapped = np.imag(correct) + 1j * np.real(correct)
    real_capture = np.real(correct).astype(np.complex128)

    metrics = IQMetrics(
        expected_tone_hz=cfg.expected_tone_hz,
        correct_peak_hz=estimate_peak_hz(correct, cfg.sample_rate_hz, exclude_dc_hz=5_000.0),
        swapped_peak_hz=estimate_peak_hz(swapped, cfg.sample_rate_hz, exclude_dc_hz=5_000.0),
        real_positive_peak_hz=estimate_positive_peak_hz(real_capture, cfg.sample_rate_hz),
        real_negative_peak_hz=estimate_negative_peak_hz(real_capture, cfg.sample_rate_hz),
        correct_error_hz=estimate_peak_hz(correct, cfg.sample_rate_hz, exclude_dc_hz=5_000.0) - cfg.expected_tone_hz,
        swapped_error_hz=estimate_peak_hz(swapped, cfg.sample_rate_hz, exclude_dc_hz=5_000.0) + cfg.expected_tone_hz,
        real_mirror_balance_hz=estimate_positive_peak_hz(real_capture, cfg.sample_rate_hz)
        + estimate_negative_peak_hz(real_capture, cfg.sample_rate_hz),
    )

    save_time_plot(ASSET_DIR / "lab23_iq_components_time.png", correct, cfg)
    save_spectra(ASSET_DIR / "lab23_iq_interpretation_spectra.png", correct, swapped, real_capture, cfg)
    metrics_path = ASSET_DIR / "lab23_iq_metrics.json"
    metrics_path.write_text(json.dumps({"config": asdict(cfg), "metrics": asdict(metrics)}, indent=2), encoding="utf-8")

    print("Lab 2.3 - I/Q interpretation and mirrored spectrum checks")
    print(f"Correct peak: {metrics.correct_peak_hz:.3f} Hz")
    print(f"I/Q swapped peak: {metrics.swapped_peak_hz:.3f} Hz")
    print(f"Real-valued positive/negative peaks: {metrics.real_positive_peak_hz:.3f}/{metrics.real_negative_peak_hz:.3f} Hz")
    print(f"Metrics JSON: {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
