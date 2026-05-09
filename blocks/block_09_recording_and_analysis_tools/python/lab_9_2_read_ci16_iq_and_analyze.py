#!/usr/bin/env python3
"""Lab 9.2 — Read CI16 IQ and analyze spectrum.

The script creates a deterministic synthetic CI16 IQ capture, reads it back using
metadata JSON, computes FFT, peak frequency, frequency error, SNR estimate, DC
offset and clipping fraction, then writes plots and metrics JSON.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
BLOCK_DIR = ROOT / "blocks" / "block_09_recording_and_analysis_tools"
ASSET_DIR = ROOT / "docs" / "assets"
METADATA_PATH = BLOCK_DIR / "assets" / "example_ci16_capture_metadata.json"
IQ_PATH = BLOCK_DIR / "assets" / "lab92_synthetic_ci16_tone.ci16"


@dataclass(frozen=True)
class IqMetrics:
    sample_count_read: int
    expected_offset_hz: float
    measured_peak_hz: float
    frequency_error_hz: float
    peak_dbfs: float
    noise_floor_dbfs: float
    snr_db: float
    dc_offset_magnitude: float
    clipping_fraction: float
    quality_pass: bool


def load_metadata(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_synthetic_ci16(path: Path, metadata: dict[str, Any], seed: int = 92) -> None:
    fs = float(metadata["sample_rate_hz"])
    n = int(metadata["sample_count"])
    offset = float(metadata["expected_signal_offset_hz"])
    rng = np.random.default_rng(seed)

    t = np.arange(n) / fs
    tone = 0.55 * np.exp(1j * 2.0 * np.pi * offset * t)
    spur = 0.025 * np.exp(1j * 2.0 * np.pi * (offset + 420e3) * t)
    noise = 0.018 * (rng.standard_normal(n) + 1j * rng.standard_normal(n))
    dc = 0.010 - 0.006j
    x = tone + spur + noise + dc

    scale = 32767.0
    i = np.clip(np.round(np.real(x) * scale), -32768, 32767).astype("<i2")
    q = np.clip(np.round(np.imag(x) * scale), -32768, 32767).astype("<i2")
    interleaved = np.empty(2 * n, dtype="<i2")
    if bool(metadata.get("i_first", True)):
        interleaved[0::2] = i
        interleaved[1::2] = q
    else:
        interleaved[0::2] = q
        interleaved[1::2] = i
    path.parent.mkdir(parents=True, exist_ok=True)
    interleaved.tofile(path)


def read_ci16(path: Path, metadata: dict[str, Any]) -> np.ndarray:
    dtype = "<i2" if metadata.get("endianness", "little") == "little" else ">i2"
    raw = np.fromfile(path, dtype=dtype)
    if len(raw) % 2 != 0:
        raise ValueError(f"CI16 file has odd int16 count: {len(raw)}")
    a = raw[0::2].astype(np.float64) / 32768.0
    b = raw[1::2].astype(np.float64) / 32768.0
    if bool(metadata.get("i_first", True)):
        return a + 1j * b
    return b + 1j * a


def spectrum_db(x: np.ndarray, fs: float, fft_length: int) -> tuple[np.ndarray, np.ndarray]:
    n = min(len(x), fft_length)
    window = np.hanning(n)
    coherent_gain = np.sum(window) / n
    spec = np.fft.fftshift(np.fft.fft(x[:n] * window, n=n)) / (n * coherent_gain)
    freq = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / fs))
    mag_db = 20.0 * np.log10(np.maximum(np.abs(spec), 1e-15))
    return freq, mag_db


def compute_metrics(x: np.ndarray, metadata: dict[str, Any]) -> IqMetrics:
    fs = float(metadata["sample_rate_hz"])
    expected = float(metadata["expected_signal_offset_hz"])
    fft_length = int(metadata.get("processing", {}).get("fft_length", 65536))
    freq, mag_db = spectrum_db(x, fs, fft_length)

    peak_idx = int(np.argmax(mag_db))
    measured = float(freq[peak_idx])
    peak_dbfs = float(mag_db[peak_idx])
    frequency_error = measured - expected

    bin_width = fs / fft_length
    signal_mask = np.abs(freq - measured) < max(15e3, 20 * bin_width)
    dc_mask = np.abs(freq) < 5e3
    noise_mask = ~(signal_mask | dc_mask)
    noise_floor = float(np.median(mag_db[noise_mask]))
    snr = peak_dbfs - noise_floor

    dc_offset = float(np.abs(np.mean(x)))
    clipping_fraction = float(np.mean((np.abs(np.real(x)) > 0.999) | (np.abs(np.imag(x)) > 0.999)))

    q = metadata.get("quality_expectations", {})
    quality_pass = bool(
        clipping_fraction <= float(q.get("max_clipping_fraction", 1.0))
        and dc_offset <= float(q.get("max_dc_offset", 1.0))
        and abs(frequency_error) <= float(q.get("max_frequency_error_hz", 1e99))
        and snr >= float(q.get("min_snr_db", -1e99))
    )

    return IqMetrics(
        sample_count_read=int(len(x)),
        expected_offset_hz=expected,
        measured_peak_hz=measured,
        frequency_error_hz=frequency_error,
        peak_dbfs=peak_dbfs,
        noise_floor_dbfs=noise_floor,
        snr_db=float(snr),
        dc_offset_magnitude=dc_offset,
        clipping_fraction=clipping_fraction,
        quality_pass=quality_pass,
    )


def save_spectrum_plot(x: np.ndarray, metadata: dict[str, Any], metrics: IqMetrics) -> Path:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    fs = float(metadata["sample_rate_hz"])
    fft_length = int(metadata.get("processing", {}).get("fft_length", 65536))
    freq, mag_db = spectrum_db(x, fs, fft_length)
    path = ASSET_DIR / "lab92_ci16_iq_spectrum.png"

    plt.figure(figsize=(7.2, 4.3))
    plt.plot(freq / 1e3, mag_db, label="CI16 IQ FFT")
    plt.axvline(metrics.expected_offset_hz / 1e3, linestyle="--", label="expected offset")
    plt.axvline(metrics.measured_peak_hz / 1e3, linestyle=":", label="measured peak")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Baseband frequency, kHz")
    plt.ylabel("Magnitude, dBFS")
    plt.title("Lab 9.2 — CI16 IQ spectrum")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()
    return path


def save_time_plot(x: np.ndarray) -> Path:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    n = min(800, len(x))
    path = ASSET_DIR / "lab92_ci16_iq_time_preview.png"
    plt.figure(figsize=(7.2, 4.3))
    plt.plot(np.real(x[:n]), label="I")
    plt.plot(np.imag(x[:n]), label="Q")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Sample index")
    plt.ylabel("Normalized amplitude")
    plt.title("Lab 9.2 — CI16 IQ time preview")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()
    return path


def save_metrics_json(metrics: IqMetrics) -> Path:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    path = ASSET_DIR / "lab92_ci16_iq_metrics.json"
    path.write_text(json.dumps(asdict(metrics), indent=2), encoding="utf-8")
    return path


def main() -> None:
    metadata = load_metadata(METADATA_PATH)
    write_synthetic_ci16(IQ_PATH, metadata)
    x = read_ci16(IQ_PATH, metadata)
    metrics = compute_metrics(x, metadata)
    spectrum_path = save_spectrum_plot(x, metadata, metrics)
    time_path = save_time_plot(x)
    metrics_path = save_metrics_json(metrics)

    print("Lab 9.2 — Read CI16 IQ and analyze spectrum")
    print(f"IQ file: {IQ_PATH}")
    print(f"Samples read: {metrics.sample_count_read}")
    print(f"Expected offset: {metrics.expected_offset_hz:.3f} Hz")
    print(f"Measured peak: {metrics.measured_peak_hz:.3f} Hz")
    print(f"Frequency error: {metrics.frequency_error_hz:.3f} Hz")
    print(f"SNR estimate: {metrics.snr_db:.2f} dB")
    print(f"DC offset magnitude: {metrics.dc_offset_magnitude:.6f}")
    print(f"Clipping fraction: {metrics.clipping_fraction:.6e}")
    print(f"Quality pass: {metrics.quality_pass}")
    print(f"Spectrum plot: {spectrum_path}")
    print(f"Time plot: {time_path}")
    print(f"Metrics JSON: {metrics_path}")


if __name__ == "__main__":
    main()
