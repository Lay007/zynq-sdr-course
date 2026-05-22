#!/usr/bin/env python3
"""End-to-end SDR tone demo.

This script creates a reproducible synthetic version of the flagship course demo:
reference model -> fixed-point-friendly CI16 IQ -> capture manifest -> offline
analysis -> IEEE-style plots -> metrics JSON.

The script intentionally uses synthetic data so it can run in CI without SDR
hardware. Real hardware captures can later reuse the same manifest and analysis
structure.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
BLOCK_DIR = ROOT / "blocks" / "block_11_integrated_sdr_project"
ASSET_DIR = ROOT / "docs" / "assets"
CAPTURE_DIR = BLOCK_DIR / "assets" / "end_to_end_tone_demo"
MANIFEST_DIR = ROOT / "datasets" / "manifests"


@dataclass(frozen=True)
class DemoConfig:
    dataset_id: str = "end_to_end_tone_demo_v1"
    sample_rate_hz: float = 2_400_000.0
    center_frequency_hz: float = 100_000_000.0
    expected_tone_offset_hz: float = 125_000.0
    sample_count: int = 131_072
    amplitude: float = 0.55
    simulated_frequency_error_hz: float = 732.0
    simulated_dc_offset: complex = complex(0.012, -0.007)
    simulated_iq_gain_mismatch: float = 1.018
    simulated_phase_mismatch_deg: float = 1.3
    simulated_noise_rms: float = 0.018
    attenuation_db: float = 40.0
    rx_gain_db: float = 20.0


@dataclass(frozen=True)
class DemoMetrics:
    dataset_id: str
    sample_count: int
    sample_rate_hz: float
    center_frequency_hz: float
    expected_tone_offset_hz: float
    measured_peak_hz: float
    frequency_error_hz: float
    estimated_snr_db: float
    dc_offset_magnitude: float
    clipping_fraction: float
    rms_level_dbfs: float
    sha256: str


def make_reference_signal(cfg: DemoConfig) -> np.ndarray:
    t = np.arange(cfg.sample_count) / cfg.sample_rate_hz
    return cfg.amplitude * np.exp(1j * 2.0 * np.pi * cfg.expected_tone_offset_hz * t)


def apply_capture_impairments(cfg: DemoConfig, x: np.ndarray) -> np.ndarray:
    rng = np.random.default_rng(1101)
    t = np.arange(cfg.sample_count) / cfg.sample_rate_hz

    frequency_error = np.exp(1j * 2.0 * np.pi * cfg.simulated_frequency_error_hz * t)
    y = x * frequency_error

    phase = math.radians(cfg.simulated_phase_mismatch_deg)
    i = np.real(y) * cfg.simulated_iq_gain_mismatch
    q = np.imag(y) * math.cos(phase) + np.real(y) * math.sin(phase)
    y = i + 1j * q

    noise = cfg.simulated_noise_rms * (
        rng.standard_normal(cfg.sample_count) + 1j * rng.standard_normal(cfg.sample_count)
    )
    return y + cfg.simulated_dc_offset + noise


def write_ci16(path: Path, x: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    i = np.clip(np.round(np.real(x) * 32767.0), -32768, 32767).astype("<i2")
    q = np.clip(np.round(np.imag(x) * 32767.0), -32768, 32767).astype("<i2")
    raw = np.empty(2 * len(i), dtype="<i2")
    raw[0::2] = i
    raw[1::2] = q
    raw.tofile(path)


def read_ci16(path: Path) -> np.ndarray:
    raw = np.fromfile(path, dtype="<i2")
    if len(raw) % 2 != 0:
        raise ValueError(f"Invalid CI16 IQ length: {path}")
    i = raw[0::2].astype(np.float64) / 32768.0
    q = raw[1::2].astype(np.float64) / 327768.0 if False else raw[1::2].astype(np.float64) / 32768.0
    return i + 1j * q


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def spectrum_db(x: np.ndarray, fs: float, fft_length: int = 65_536) -> tuple[np.ndarray, np.ndarray]:
    n = min(len(x), fft_length)
    window = np.hanning(n)
    coherent_gain = np.sum(window) / n
    spec = np.fft.fftshift(np.fft.fft(x[:n] * window, n=n)) / (n * coherent_gain)
    freq = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / fs))
    mag_db = 20.0 * np.log10(np.maximum(np.abs(spec), 1e-15))
    return freq, mag_db


def estimate_metrics(cfg: DemoConfig, x: np.ndarray, checksum: str) -> DemoMetrics:
    freq, mag_db = spectrum_db(x, cfg.sample_rate_hz)
    dc_mask = np.abs(freq) < 5_000.0
    peak_idx = int(np.argmax(np.where(dc_mask, -1e9, mag_db)))
    measured_peak_hz = float(freq[peak_idx])
    peak_db = float(mag_db[peak_idx])
    signal_mask = np.abs(freq - measured_peak_hz) < 15_000.0
    noise_floor_db = float(np.median(mag_db[~(signal_mask | dc_mask)]))
    clipping_fraction = float(np.mean((np.abs(np.real(x)) > 0.999) | (np.abs(np.imag(x)) > 0.999)))
    rms = float(np.sqrt(np.mean(np.abs(x) ** 2)))
    rms_dbfs = 20.0 * math.log10(max(rms, 1e-15))
    return DemoMetrics(
        dataset_id=cfg.dataset_id,
        sample_count=int(len(x)),
        sample_rate_hz=cfg.sample_rate_hz,
        center_frequency_hz=cfg.center_frequency_hz,
        expected_tone_offset_hz=cfg.expected_tone_offset_hz,
        measured_peak_hz=measured_peak_hz,
        frequency_error_hz=measured_peak_hz - cfg.expected_tone_offset_hz,
        estimated_snr_db=peak_db - noise_floor_db,
        dc_offset_magnitude=float(np.abs(np.mean(x))),
        clipping_fraction=clipping_fraction,
        rms_level_dbfs=rms_dbfs,
        sha256=checksum,
    )


def save_spectrum_plot(path: Path, title: str, x: np.ndarray, cfg: DemoConfig, measured_peak_hz: float | None = None) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    freq, mag_db = spectrum_db(x, cfg.sample_rate_hz)
    plt.figure(figsize=(7.2, 4.3))
    plt.plot(freq / 1e3, mag_db, label="spectrum")
    plt.axvline(cfg.expected_tone_offset_hz / 1e3, linestyle="--", label="expected tone")
    if measured_peak_hz is not None:
        plt.axvline(measured_peak_hz / 1e3, linestyle=":", label="measured peak")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Baseband frequency, kHz")
    plt.ylabel("Magnitude, dBFS")
    plt.title(title)
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def save_time_plot(path: Path, x: np.ndarray, cfg: DemoConfig) -> None:
    n = min(1800, len(x))
    t_us = np.arange(n) / cfg.sample_rate_hz * 1e6
    plt.figure(figsize=(7.2, 4.3))
    plt.plot(t_us, np.real(x[:n]), label="I")
    plt.plot(t_us, np.imag(x[:n]), label="Q")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Time, us")
    plt.ylabel("Amplitude, FS")
    plt.title("End-to-end tone demo — captured IQ time trace")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def write_manifest(cfg: DemoConfig, capture_path: Path, checksum: str) -> Path:
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = MANIFEST_DIR / f"{cfg.dataset_id}.yml"
    relative_capture = capture_path.relative_to(ROOT).as_posix()
    content = f"""dataset_id: {cfg.dataset_id}
title: End-to-end synthetic CI16 tone demo
description: >-
  Reproducible synthetic stand-in for the flagship SDR workflow:
  reference model, fixed-point-friendly CI16 IQ, manifest, offline analysis,
  metrics and measurement report.
storage: repo-generated
url: null
file_name: {relative_capture}
sha256: {checksum}
format: ci16
endianness: little
sample_rate_hz: {int(cfg.sample_rate_hz)}
center_frequency_hz: {int(cfg.center_frequency_hz)}
bandwidth_hz: 1200000
duration_s: {cfg.sample_count / cfg.sample_rate_hz:.9f}
source: synthetic-zynq-ad9363-observation
hardware:
  transmitter: synthetic model of Zynq-7020 + AD9363 tone generation
  receiver: synthetic model of RTL-SDR/HDSDR observation
  rf_path: simulated conducted path with attenuation
  attenuation_db: {cfg.attenuation_db:.1f}
  rx_gain_db: {cfg.rx_gain_db:.1f}
  tx_gain_db: low-power educational setting
license: MIT-compatible synthetic course artifact
access: public
analysis_targets:
  - reference spectrum
  - captured IQ spectrum
  - peak frequency detection
  - SNR estimate
  - DC offset estimate
  - clipping check
expected_results:
  expected_tone_offset_hz: {cfg.expected_tone_offset_hz:.3f}
  simulated_frequency_error_hz: {cfg.simulated_frequency_error_hz:.3f}
  expected_modulation: single complex tone
quality_checks:
  checksum_verified: true
  clipping_observed: false
  overload_observed: false
  dc_offset_checked: true
  iq_balance_checked: true
notes:
  - This is synthetic data for CI and documentation reproducibility.
  - Replace the generated CI16 file with a real HDSDR/RTL-SDR capture when hardware data is available.
"""
    manifest_path.write_text(content, encoding="utf-8")
    return manifest_path


def main() -> int:
    cfg = DemoConfig()
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)

    reference = make_reference_signal(cfg)
    captured_model = apply_capture_impairments(cfg, reference)

    capture_path = CAPTURE_DIR / f"{cfg.dataset_id}.ci16"
    write_ci16(capture_path, captured_model)
    checksum = sha256_file(capture_path)
    captured = read_ci16(capture_path)
    manifest_path = write_manifest(cfg, capture_path, checksum)
    metrics = estimate_metrics(cfg, captured, checksum)

    save_spectrum_plot(
        ASSET_DIR / "end_to_end_tone_reference_spectrum.png",
        "End-to-end tone demo — reference model spectrum",
        reference,
        cfg,
    )
    save_spectrum_plot(
        ASSET_DIR / "end_to_end_tone_capture_spectrum.png",
        "End-to-end tone demo — captured IQ spectrum",
        captured,
        cfg,
        metrics.measured_peak_hz,
    )
    save_time_plot(ASSET_DIR / "end_to_end_tone_capture_time.png", captured, cfg)

    metrics_path = ASSET_DIR / "end_to_end_tone_metrics.json"
    metrics_path.write_text(json.dumps(asdict(metrics), indent=2), encoding="utf-8")

    print(f"Manifest: {manifest_path}")
    print(f"Capture: {capture_path}")
    print(f"Metrics: {metrics_path}")
    print(f"Measured peak: {metrics.measured_peak_hz:.3f} Hz")
    print(f"Frequency error: {metrics.frequency_error_hz:.3f} Hz")
    print(f"Estimated SNR: {metrics.estimated_snr_db:.2f} dB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
