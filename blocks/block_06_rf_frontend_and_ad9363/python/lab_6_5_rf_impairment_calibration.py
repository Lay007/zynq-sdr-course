#!/usr/bin/env python3
"""Lab 6.5 - RF impairment calibration.

Synthetic baseband tone with practical RX impairments:
  - DC offset
  - I/Q gain imbalance
  - I/Q quadrature skew
  - LO leakage component

The script applies a compact calibration flow and reports before/after metrics.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"


@dataclass(frozen=True)
class CalibrationConfig:
    sample_rate_hz: float = 2.4e6
    sample_count: int = 65536
    tone_offset_hz: float = 180e3
    tone_amplitude: float = 0.72
    dc_i: float = 0.085
    dc_q: float = -0.052
    iq_gain_mismatch_db: float = 1.7
    iq_phase_skew_deg: float = 6.5
    lo_leakage_amplitude: float = 0.14
    lo_leakage_phase_deg: float = -30.0
    noise_rms: float = 0.015
    seed: int = 65


@dataclass(frozen=True)
class ImpairmentMetrics:
    dc_offset_rms: float
    iq_gain_mismatch_db: float
    iq_cross_correlation: float
    image_rejection_db: float
    lo_leakage_dbfs: float


def qpsk_tone(cfg: CalibrationConfig) -> np.ndarray:
    t = np.arange(cfg.sample_count) / cfg.sample_rate_hz
    return cfg.tone_amplitude * np.exp(1j * 2.0 * np.pi * cfg.tone_offset_hz * t)


def apply_impairments(x: np.ndarray, cfg: CalibrationConfig, rng: np.random.Generator) -> np.ndarray:
    i = np.real(x)
    q = np.imag(x)
    gain_q = 10.0 ** (cfg.iq_gain_mismatch_db / 20.0)
    skew = np.deg2rad(cfg.iq_phase_skew_deg)

    i_imp = i + np.tan(skew) * q
    q_imp = gain_q * q
    y = i_imp + 1j * q_imp

    lo = cfg.lo_leakage_amplitude * np.exp(1j * np.deg2rad(cfg.lo_leakage_phase_deg))
    y = y + lo
    y = y + (cfg.dc_i + 1j * cfg.dc_q)
    y = y + cfg.noise_rms * (rng.standard_normal(len(y)) + 1j * rng.standard_normal(len(y)))
    return y


def metric_image_rejection_db(x: np.ndarray, fs_hz: float, tone_hz: float) -> float:
    spec = np.fft.fftshift(np.fft.fft(x * np.hanning(len(x))))
    freq = np.fft.fftshift(np.fft.fftfreq(len(x), d=1.0 / fs_hz))
    pos_idx = int(np.argmin(np.abs(freq - tone_hz)))
    neg_idx = int(np.argmin(np.abs(freq + tone_hz)))
    pos_pow = float(np.abs(spec[pos_idx]) ** 2)
    neg_pow = float(np.abs(spec[neg_idx]) ** 2)
    return float(10.0 * np.log10(max(pos_pow, 1e-15) / max(neg_pow, 1e-15)))


def metric_lo_leakage_dbfs(x: np.ndarray, fs_hz: float) -> float:
    spec = np.fft.fftshift(np.fft.fft(x * np.hanning(len(x))))
    center_idx = len(spec) // 2
    peak = float(np.max(np.abs(spec)))
    lo = float(np.abs(spec[center_idx]))
    return float(20.0 * np.log10(max(lo, 1e-15) / max(peak, 1e-15)))


def collect_metrics(x: np.ndarray, fs_hz: float, tone_hz: float) -> ImpairmentMetrics:
    i = np.real(x)
    q = np.imag(x)
    dc = np.mean(x)
    gain_db = float(20.0 * np.log10(max(np.std(i), 1e-15) / max(np.std(q), 1e-15)))
    corr = float(np.mean((i - np.mean(i)) * (q - np.mean(q))) / max(np.std(i) * np.std(q), 1e-15))
    return ImpairmentMetrics(
        dc_offset_rms=float(np.abs(dc)),
        iq_gain_mismatch_db=gain_db,
        iq_cross_correlation=corr,
        image_rejection_db=metric_image_rejection_db(x, fs_hz, tone_hz),
        lo_leakage_dbfs=metric_lo_leakage_dbfs(x, fs_hz),
    )


def calibrate_impairments(x: np.ndarray) -> np.ndarray:
    y = x - np.mean(x)
    i = np.real(y)
    q = np.imag(y)

    q = q * (np.std(i) / max(np.std(q), 1e-15))
    proj = np.dot(q, i) / max(np.dot(i, i), 1e-15)
    q = q - proj * i
    q = q * (np.std(i) / max(np.std(q), 1e-15))

    y_cal = i + 1j * q
    y_cal = y_cal - np.mean(y_cal)
    return y_cal


def save_spectrum(path: Path, fs_hz: float, raw: np.ndarray, cal: np.ndarray) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    f = np.fft.fftshift(np.fft.fftfreq(len(raw), d=1.0 / fs_hz))
    s_raw = np.fft.fftshift(np.fft.fft(raw * np.hanning(len(raw))))
    s_cal = np.fft.fftshift(np.fft.fft(cal * np.hanning(len(cal))))

    p_raw = 20.0 * np.log10(np.maximum(np.abs(s_raw) / np.max(np.abs(s_raw)), 1e-15))
    p_cal = 20.0 * np.log10(np.maximum(np.abs(s_cal) / np.max(np.abs(s_cal)), 1e-15))

    plt.figure(figsize=(7.5, 4.4))
    plt.plot(f / 1e3, p_raw, label="before calibration")
    plt.plot(f / 1e3, p_cal, label="after calibration")
    plt.xlim(-350, 350)
    plt.ylim(-90, 5)
    plt.grid(True, alpha=0.35)
    plt.xlabel("Frequency, kHz")
    plt.ylabel("Normalized magnitude, dB")
    plt.title("Lab 6.5 - RF impairment calibration spectrum")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def save_constellations(path: Path, raw: np.ndarray, cal: np.ndarray) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    shown = 5000
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.9), sharex=True, sharey=True)
    axes[0].scatter(np.real(raw[:shown]), np.imag(raw[:shown]), s=4, alpha=0.4)
    axes[0].set_title("Before calibration")
    axes[0].set_xlabel("I")
    axes[0].set_ylabel("Q")
    axes[0].grid(True, alpha=0.35)
    axes[0].set_aspect("equal", adjustable="box")

    axes[1].scatter(np.real(cal[:shown]), np.imag(cal[:shown]), s=4, alpha=0.4)
    axes[1].set_title("After calibration")
    axes[1].set_xlabel("I")
    axes[1].grid(True, alpha=0.35)
    axes[1].set_aspect("equal", adjustable="box")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def main() -> None:
    cfg = CalibrationConfig()
    rng = np.random.default_rng(cfg.seed)

    clean = qpsk_tone(cfg)
    impaired = apply_impairments(clean, cfg, rng)
    calibrated = calibrate_impairments(impaired)

    metrics_before = collect_metrics(impaired, cfg.sample_rate_hz, cfg.tone_offset_hz)
    metrics_after = collect_metrics(calibrated, cfg.sample_rate_hz, cfg.tone_offset_hz)

    spec_path = ASSET_DIR / "lab65_rf_impairment_spectrum_before_after.png"
    const_path = ASSET_DIR / "lab65_rf_impairment_constellation_before_after.png"
    metrics_path = ASSET_DIR / "lab65_rf_impairment_calibration_metrics.json"

    save_spectrum(spec_path, cfg.sample_rate_hz, impaired, calibrated)
    save_constellations(const_path, impaired, calibrated)
    metrics_path.write_text(
        json.dumps(
            {
                "config": asdict(cfg),
                "before": asdict(metrics_before),
                "after": asdict(metrics_after),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("Lab 6.5 - RF impairment calibration")
    print(f"DC offset RMS before/after: {metrics_before.dc_offset_rms:.6f} / {metrics_after.dc_offset_rms:.6f}")
    print(
        "Image rejection (dB) before/after: "
        f"{metrics_before.image_rejection_db:.2f} / {metrics_after.image_rejection_db:.2f}"
    )
    print(
        "IQ cross-correlation before/after: "
        f"{metrics_before.iq_cross_correlation:.4f} / {metrics_after.iq_cross_correlation:.4f}"
    )
    print(f"Metrics JSON: {metrics_path}")


if __name__ == "__main__":
    main()
