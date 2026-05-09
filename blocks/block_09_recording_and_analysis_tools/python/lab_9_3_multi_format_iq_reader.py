#!/usr/bin/env python3
"""Lab 9.3 — Multi-format IQ reader.

Creates synthetic IQ recordings in ci16, cu8 and cf32 formats, reads them back
through one metadata-driven dispatcher and writes comparable FFT plots and
metrics JSON.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
BLOCK_DIR = ROOT / "blocks" / "block_09_recording_and_analysis_tools"
ASSET_DIR = ROOT / "docs" / "assets"
CAPTURE_DIR = BLOCK_DIR / "assets" / "lab93_multiformat"


@dataclass(frozen=True)
class CaptureConfig:
    iq_format: str
    path: str
    sample_rate_hz: float = 2.4e6
    center_frequency_hz: float = 915e6
    sample_count: int = 131072
    expected_signal_offset_hz: float = 125e3
    i_first: bool = True
    endianness: str = "little"


@dataclass(frozen=True)
class CaptureMetrics:
    iq_format: str
    sample_count_read: int
    measured_peak_hz: float
    expected_signal_offset_hz: float
    frequency_error_hz: float
    snr_db: float
    dc_offset_magnitude: float
    clipping_fraction: float


def make_signal(cfg: CaptureConfig, seed: int = 93) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.arange(cfg.sample_count) / cfg.sample_rate_hz
    tone = 0.50 * np.exp(1j * 2.0 * np.pi * cfg.expected_signal_offset_hz * t)
    spur = 0.020 * np.exp(1j * 2.0 * np.pi * (cfg.expected_signal_offset_hz - 380e3) * t)
    noise = 0.018 * (rng.standard_normal(cfg.sample_count) + 1j * rng.standard_normal(cfg.sample_count))
    dc = 0.008 + 0.004j
    return tone + spur + noise + dc


def write_capture(cfg: CaptureConfig, x: np.ndarray) -> None:
    path = Path(cfg.path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if cfg.iq_format == "ci16":
        i = np.clip(np.round(np.real(x) * 32767.0), -32768, 32767).astype("<i2")
        q = np.clip(np.round(np.imag(x) * 32767.0), -32768, 32767).astype("<i2")
        raw = interleave(i, q, cfg.i_first)
        raw.tofile(path)
    elif cfg.iq_format == "cu8":
        i = np.clip(np.round((np.real(x) * 0.48 + 0.5) * 255.0), 0, 255).astype(np.uint8)
        q = np.clip(np.round((np.imag(x) * 0.48 + 0.5) * 255.0), 0, 255).astype(np.uint8)
        raw = interleave(i, q, cfg.i_first)
        raw.tofile(path)
    elif cfg.iq_format == "cf32":
        i = np.real(x).astype("<f4")
        q = np.imag(x).astype("<f4")
        raw = interleave(i, q, cfg.i_first)
        raw.tofile(path)
    else:
        raise ValueError(f"Unsupported format for writing: {cfg.iq_format}")


def interleave(i: np.ndarray, q: np.ndarray, i_first: bool) -> np.ndarray:
    raw = np.empty(2 * len(i), dtype=i.dtype)
    if i_first:
        raw[0::2] = i
        raw[1::2] = q
    else:
        raw[0::2] = q
        raw[1::2] = i
    return raw


def write_metadata(cfg: CaptureConfig) -> Path:
    path = Path(cfg.path).with_suffix(Path(cfg.path).suffix + ".metadata.json")
    payload = asdict(cfg)
    payload["description"] = f"Synthetic {cfg.iq_format} capture for Lab 9.3"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def read_iq(metadata: dict[str, Any]) -> np.ndarray:
    fmt = metadata["iq_format"]
    path = Path(metadata["path"])
    i_first = bool(metadata.get("i_first", True))
    endian = metadata.get("endianness", "little")

    if fmt == "ci16":
        dtype = "<i2" if endian == "little" else ">i2"
        raw = np.fromfile(path, dtype=dtype)
        a = raw[0::2].astype(np.float64) / 32768.0
        b = raw[1::2].astype(np.float64) / 32768.0
    elif fmt == "cu8":
        raw = np.fromfile(path, dtype=np.uint8)
        a = (raw[0::2].astype(np.float64) - 127.5) / 127.5
        b = (raw[1::2].astype(np.float64) - 127.5) / 127.5
    elif fmt == "cf32":
        dtype = "<f4" if endian == "little" else ">f4"
        raw = np.fromfile(path, dtype=dtype)
        a = raw[0::2].astype(np.float64)
        b = raw[1::2].astype(np.float64)
    else:
        raise ValueError(f"Unsupported IQ format: {fmt}")

    if len(a) != len(b):
        raise ValueError(f"Invalid interleaved IQ length for {path}")
    return a + 1j * b if i_first else b + 1j * a


def spectrum_db(x: np.ndarray, fs: float, fft_length: int = 65536) -> tuple[np.ndarray, np.ndarray]:
    n = min(len(x), fft_length)
    window = np.hanning(n)
    coherent_gain = np.sum(window) / n
    spec = np.fft.fftshift(np.fft.fft(x[:n] * window, n=n)) / (n * coherent_gain)
    freq = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / fs))
    mag_db = 20.0 * np.log10(np.maximum(np.abs(spec), 1e-15))
    return freq, mag_db


def analyze(metadata: dict[str, Any]) -> tuple[np.ndarray, CaptureMetrics]:
    x = read_iq(metadata)
    fs = float(metadata["sample_rate_hz"])
    expected = float(metadata["expected_signal_offset_hz"])
    freq, mag_db = spectrum_db(x, fs)
    peak_idx = int(np.argmax(mag_db))
    measured = float(freq[peak_idx])
    peak = float(mag_db[peak_idx])
    signal_mask = np.abs(freq - measured) < 15e3
    dc_mask = np.abs(freq) < 5e3
    noise_floor = float(np.median(mag_db[~(signal_mask | dc_mask)]))
    dc = float(np.abs(np.mean(x)))
    clip = float(np.mean((np.abs(np.real(x)) > 0.999) | (np.abs(np.imag(x)) > 0.999)))
    metrics = CaptureMetrics(
        iq_format=str(metadata["iq_format"]),
        sample_count_read=int(len(x)),
        measured_peak_hz=measured,
        expected_signal_offset_hz=expected,
        frequency_error_hz=measured - expected,
        snr_db=peak - noise_floor,
        dc_offset_magnitude=dc,
        clipping_fraction=clip,
    )
    return x, metrics


def save_spectrum(metadata: dict[str, Any], x: np.ndarray, metrics: CaptureMetrics) -> Path:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    freq, mag_db = spectrum_db(x, float(metadata["sample_rate_hz"]))
    out = ASSET_DIR / f"lab93_multiformat_iq_spectrum_{metrics.iq_format}.png"
    plt.figure(figsize=(7.2, 4.3))
    plt.plot(freq / 1e3, mag_db, label=metrics.iq_format)
    plt.axvline(metrics.expected_signal_offset_hz / 1e3, linestyle="--", label="expected")
    plt.axvline(metrics.measured_peak_hz / 1e3, linestyle=":", label="measured")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Baseband frequency, kHz")
    plt.ylabel("Magnitude, dBFS")
    plt.title(f"Lab 9.3 — {metrics.iq_format} IQ spectrum")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(out, dpi=180)
    plt.close()
    return out


def main() -> None:
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    configs = [
        CaptureConfig("ci16", str(CAPTURE_DIR / "synthetic_ci16.ci16")),
        CaptureConfig("cu8", str(CAPTURE_DIR / "synthetic_cu8.cu8")),
        CaptureConfig("cf32", str(CAPTURE_DIR / "synthetic_cf32.cf32")),
    ]

    all_metrics: list[dict[str, Any]] = []
    for idx, cfg in enumerate(configs):
        x = make_signal(cfg, seed=93 + idx)
        write_capture(cfg, x)
        metadata_path = write_metadata(cfg)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        readback, metrics = analyze(metadata)
        save_spectrum(metadata, readback, metrics)
        all_metrics.append(asdict(metrics))
        print(f"{cfg.iq_format}: peak={metrics.measured_peak_hz:.3f} Hz, SNR={metrics.snr_db:.2f} dB")

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    metrics_path = ASSET_DIR / "lab93_multiformat_iq_metrics.json"
    metrics_path.write_text(json.dumps({"captures": all_metrics}, indent=2), encoding="utf-8")
    print(f"Metrics JSON: {metrics_path}")


if __name__ == "__main__":
    main()
