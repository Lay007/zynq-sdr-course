#!/usr/bin/env python3
"""Lab 6.4 — Synthetic RF capture analysis.

This script reads the Block 6 example IQ metadata JSON, generates a synthetic
complex IQ capture for the planned RF tone, estimates peak frequency, frequency
error, SNR and overload indicators, and saves IEEE-style plots.

The goal is to validate the analysis workflow before working with real RF IQ
recordings from AD9363/RTL-SDR/HDSDR experiments.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_METADATA = (
    ROOT
    / "blocks"
    / "block_06_rf_frontend_and_ad9363"
    / "assets"
    / "example_first_rf_capture_metadata.json"
)
ASSET_DIR = ROOT / "docs" / "assets"
OUTPUT_IQ = ROOT / "blocks" / "block_06_rf_frontend_and_ad9363" / "assets" / "synthetic_first_rf_capture.ci16"


@dataclass(frozen=True)
class AnalysisResult:
    expected_offset_hz: float
    measured_peak_hz: float
    frequency_error_hz: float
    snr_db: float
    peak_dbfs: float
    noise_floor_dbfs: float
    overload_flag: bool
    clipping_count: int


def load_metadata(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def generate_synthetic_iq(metadata: dict[str, Any], seed: int = 23) -> np.ndarray:
    sampling = metadata["sampling"]
    signal = metadata["signal"]
    fs = float(sampling["sample_rate_hz"])
    n = int(sampling["sample_count"])
    offset_hz = float(signal["expected_offset_hz"])

    rng = np.random.default_rng(seed)
    t = np.arange(n) / fs

    tone_amplitude = 0.55
    noise_rms = 0.018
    small_spur_amplitude = 0.035
    small_spur_offset_hz = offset_hz + 350e3
    dc_offset = 0.006 + 1j * (-0.004)

    x = tone_amplitude * np.exp(1j * 2 * np.pi * offset_hz * t)
    x += small_spur_amplitude * np.exp(1j * 2 * np.pi * small_spur_offset_hz * t)
    x += noise_rms * (rng.standard_normal(n) + 1j * rng.standard_normal(n))
    x += dc_offset

    return x.astype(np.complex128)


def write_ci16(path: Path, x: np.ndarray) -> int:
    scale = 32767.0
    i = np.clip(np.round(np.real(x) * scale), -32768, 32767).astype("<i2")
    q = np.clip(np.round(np.imag(x) * scale), -32768, 32767).astype("<i2")
    interleaved = np.empty(2 * len(x), dtype="<i2")
    interleaved[0::2] = i
    interleaved[1::2] = q
    path.parent.mkdir(parents=True, exist_ok=True)
    interleaved.tofile(path)
    clipping_count = int(np.sum((i == 32767) | (i == -32768) | (q == 32767) | (q == -32768)))
    return clipping_count


def spectrum_db(x: np.ndarray, fs: float, fft_length: int) -> tuple[np.ndarray, np.ndarray]:
    n = min(len(x), fft_length)
    x = x[:n]
    window = np.hanning(n)
    coherent_gain = np.sum(window) / n
    spec = np.fft.fftshift(np.fft.fft(x * window, n=n)) / (n * coherent_gain)
    freq = np.fft.fftshift(np.fft.fftfreq(n, d=1 / fs))
    mag_db = 20 * np.log10(np.maximum(np.abs(spec), 1e-15))
    return freq, mag_db


def estimate_metrics(metadata: dict[str, Any], x: np.ndarray, clipping_count: int) -> AnalysisResult:
    fs = float(metadata["sampling"]["sample_rate_hz"])
    expected_offset_hz = float(metadata["frequency_plan"]["expected_observed_offset_hz"])
    fft_length = int(metadata["processing"].get("fft_length", 65536))
    freq, mag_db = spectrum_db(x, fs, fft_length)

    peak_idx = int(np.argmax(mag_db))
    measured_peak_hz = float(freq[peak_idx])
    peak_dbfs = float(mag_db[peak_idx])
    frequency_error_hz = measured_peak_hz - expected_offset_hz

    bin_width = fs / fft_length
    exclusion_hz = max(15e3, 20 * bin_width)
    signal_mask = np.abs(freq - measured_peak_hz) < exclusion_hz
    dc_mask = np.abs(freq) < 5e3
    noise_mask = ~(signal_mask | dc_mask)
    noise_floor_dbfs = float(np.median(mag_db[noise_mask]))
    snr_db = peak_dbfs - noise_floor_dbfs

    overload_flag = bool(clipping_count > 0 or peak_dbfs > -1.0 or snr_db < 10.0)

    return AnalysisResult(
        expected_offset_hz=expected_offset_hz,
        measured_peak_hz=measured_peak_hz,
        frequency_error_hz=frequency_error_hz,
        snr_db=float(snr_db),
        peak_dbfs=peak_dbfs,
        noise_floor_dbfs=noise_floor_dbfs,
        overload_flag=overload_flag,
        clipping_count=clipping_count,
    )


def save_spectrum_plot(metadata: dict[str, Any], x: np.ndarray, result: AnalysisResult) -> Path:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    fs = float(metadata["sampling"]["sample_rate_hz"])
    fft_length = int(metadata["processing"].get("fft_length", 65536))
    freq, mag_db = spectrum_db(x, fs, fft_length)

    out_path = ASSET_DIR / "lab64_synthetic_rf_capture_fft.png"
    plt.figure(figsize=(7.2, 4.3))
    plt.plot(freq / 1e3, mag_db, label="synthetic IQ FFT")
    plt.axvline(result.expected_offset_hz / 1e3, linestyle="--", label="expected peak")
    plt.axvline(result.measured_peak_hz / 1e3, linestyle=":", label="measured peak")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Baseband frequency, kHz")
    plt.ylabel("Magnitude, dBFS")
    plt.title("Lab 6.4 — Synthetic RF capture spectrum")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()
    return out_path


def save_time_plot(x: np.ndarray) -> Path:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    n = min(600, len(x))
    out_path = ASSET_DIR / "lab64_synthetic_rf_capture_time.png"
    plt.figure(figsize=(7.2, 4.3))
    plt.plot(np.real(x[:n]), label="I")
    plt.plot(np.imag(x[:n]), label="Q")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Sample index")
    plt.ylabel("Amplitude, normalized")
    plt.title("Lab 6.4 — Synthetic IQ time-domain preview")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()
    return out_path


def save_metrics_json(result: AnalysisResult) -> Path:
    out_path = ASSET_DIR / "lab64_synthetic_rf_capture_metrics.json"
    payload = {
        "expected_offset_hz": result.expected_offset_hz,
        "measured_peak_hz": result.measured_peak_hz,
        "frequency_error_hz": result.frequency_error_hz,
        "snr_db": result.snr_db,
        "peak_dbfs": result.peak_dbfs,
        "noise_floor_dbfs": result.noise_floor_dbfs,
        "overload_flag": result.overload_flag,
        "clipping_count": result.clipping_count,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a synthetic Block 6 RF capture")
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA, help="Path to RF metadata JSON")
    parser.add_argument("--write-iq", action="store_true", help="Write synthetic CI16 IQ file")
    args = parser.parse_args()

    metadata = load_metadata(args.metadata)
    x = generate_synthetic_iq(metadata)

    clipping_count = 0
    if args.write_iq:
        clipping_count = write_ci16(OUTPUT_IQ, x)
    else:
        # Estimate clipping in the same way without writing a file.
        scale = 32767.0
        i = np.clip(np.round(np.real(x) * scale), -32768, 32767).astype(np.int16)
        q = np.clip(np.round(np.imag(x) * scale), -32768, 32767).astype(np.int16)
        clipping_count = int(np.sum((i == 32767) | (i == -32768) | (q == 32767) | (q == -32768)))

    result = estimate_metrics(metadata, x, clipping_count)
    spectrum_path = save_spectrum_plot(metadata, x, result)
    time_path = save_time_plot(x)
    metrics_path = save_metrics_json(result)

    print("Lab 6.4 — Synthetic RF capture analysis")
    print(f"Metadata: {args.metadata}")
    print(f"Expected offset: {result.expected_offset_hz:.3f} Hz")
    print(f"Measured peak: {result.measured_peak_hz:.3f} Hz")
    print(f"Frequency error: {result.frequency_error_hz:.3f} Hz")
    print(f"Peak level: {result.peak_dbfs:.2f} dBFS")
    print(f"Noise floor: {result.noise_floor_dbfs:.2f} dBFS")
    print(f"SNR estimate: {result.snr_db:.2f} dB")
    print(f"Clipping count: {result.clipping_count}")
    print(f"Overload flag: {result.overload_flag}")
    print(f"Spectrum plot: {spectrum_path}")
    print(f"Time plot: {time_path}")
    print(f"Metrics JSON: {metrics_path}")
    if args.write_iq:
        print(f"Synthetic IQ file: {OUTPUT_IQ}")


if __name__ == "__main__":
    main()
