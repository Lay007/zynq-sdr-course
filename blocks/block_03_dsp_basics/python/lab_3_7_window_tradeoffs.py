#!/usr/bin/env python3
"""Lab 3.7 — Window trade-offs and weak-signal detection.

Deterministic script-driven lab: no notebooks. It compares FFT window choices
for SDR measurements where a weak signal must be observed near a strong tone.
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
class WindowMetric:
    name: str
    coherent_gain: float
    enbw_bins: float
    peak_strong_db: float
    weak_bin_level_db: float
    weak_to_local_floor_db: float


@dataclass(frozen=True)
class WindowTradeoffMetrics:
    sample_rate_hz: float
    fft_length: int
    strong_tone_hz: float
    weak_tone_hz: float
    weak_relative_db: float
    windows: list[WindowMetric]


def make_signal(fs: float, n: int, strong_hz: float, weak_hz: float, weak_relative_db: float) -> np.ndarray:
    rng = np.random.default_rng(370)
    t = np.arange(n) / fs
    strong = np.exp(1j * 2.0 * np.pi * strong_hz * t)
    weak = 10.0 ** (weak_relative_db / 20.0) * np.exp(1j * 2.0 * np.pi * weak_hz * t)
    noise = 0.0007 * (rng.standard_normal(n) + 1j * rng.standard_normal(n))
    return strong + weak + noise


def make_windows(n: int) -> dict[str, np.ndarray]:
    return {
        "rectangular": np.ones(n),
        "hann": np.hanning(n),
        "blackman": np.blackman(n),
    }


def spectrum_db(x: np.ndarray, w: np.ndarray, fs: float) -> tuple[np.ndarray, np.ndarray]:
    n = len(w)
    coherent_gain = np.sum(w) / n
    spec = np.fft.fftshift(np.fft.fft(x[:n] * w, n=n)) / (n * coherent_gain)
    freq = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / fs))
    mag_db = 20.0 * np.log10(np.maximum(np.abs(spec), 1e-15))
    return freq, mag_db


def nearest_bin(freq: np.ndarray, target: float) -> int:
    return int(np.argmin(np.abs(freq - target)))


def compute_window_metric(name: str, w: np.ndarray, x: np.ndarray, fs: float, strong_hz: float, weak_hz: float) -> WindowMetric:
    freq, mag = spectrum_db(x, w, fs)
    strong_idx = nearest_bin(freq, strong_hz)
    weak_idx = nearest_bin(freq, weak_hz)
    local_span = 30
    weak_exclusion = 3
    lo = max(0, weak_idx - local_span)
    hi = min(len(mag), weak_idx + local_span + 1)
    mask = np.ones(hi - lo, dtype=bool)
    center = weak_idx - lo
    mask[max(0, center - weak_exclusion) : min(len(mask), center + weak_exclusion + 1)] = False
    local_floor = float(np.median(mag[lo:hi][mask]))
    coherent_gain = float(np.sum(w) / len(w))
    enbw = float(len(w) * np.sum(w * w) / (np.sum(w) ** 2))
    return WindowMetric(
        name=name,
        coherent_gain=coherent_gain,
        enbw_bins=enbw,
        peak_strong_db=float(mag[strong_idx]),
        weak_bin_level_db=float(mag[weak_idx]),
        weak_to_local_floor_db=float(mag[weak_idx] - local_floor),
    )


def save_window_spectra(x: np.ndarray, windows: dict[str, np.ndarray], fs: float, strong_hz: float, weak_hz: float) -> None:
    out = ASSET_DIR / "lab37_window_tradeoffs.png"
    plt.figure(figsize=(7.2, 4.3))
    for name, w in windows.items():
        freq, mag = spectrum_db(x, w, fs)
        region = (freq > strong_hz - 15_000.0) & (freq < weak_hz + 25_000.0)
        plt.plot(freq[region] / 1e3, mag[region], label=name)
    plt.axvline(strong_hz / 1e3, linestyle="--", label="strong tone")
    plt.axvline(weak_hz / 1e3, linestyle=":", label="weak tone")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Baseband frequency, kHz")
    plt.ylabel("Magnitude, dBFS")
    plt.title("Lab 3.7 — Window trade-offs near a strong tone")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(out, dpi=180)
    plt.close()


def save_detection_bar(metrics: list[WindowMetric]) -> None:
    out = ASSET_DIR / "lab37_weak_signal_detection.png"
    names = [m.name for m in metrics]
    values = [m.weak_to_local_floor_db for m in metrics]
    plt.figure(figsize=(7.2, 4.3))
    plt.bar(names, values)
    plt.grid(True, axis="y", alpha=0.35)
    plt.xlabel("FFT window")
    plt.ylabel("Weak tone above local floor, dB")
    plt.title("Lab 3.7 — Weak-signal visibility by window")
    plt.tight_layout()
    plt.savefig(out, dpi=180)
    plt.close()


def main() -> int:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    fs = 1_000_000.0
    n = 16_384
    strong_hz = 100_200.0
    weak_hz = 108_600.0
    weak_relative_db = -54.0
    x = make_signal(fs, n, strong_hz, weak_hz, weak_relative_db)
    windows = make_windows(n)
    metrics = [compute_window_metric(name, w, x, fs, strong_hz, weak_hz) for name, w in windows.items()]
    save_window_spectra(x, windows, fs, strong_hz, weak_hz)
    save_detection_bar(metrics)
    payload = WindowTradeoffMetrics(
        sample_rate_hz=fs,
        fft_length=n,
        strong_tone_hz=strong_hz,
        weak_tone_hz=weak_hz,
        weak_relative_db=weak_relative_db,
        windows=metrics,
    )
    out = ASSET_DIR / "lab37_window_metrics.json"
    out.write_text(json.dumps(asdict(payload), indent=2), encoding="utf-8")
    for metric in metrics:
        print(f"{metric.name}: weak visibility = {metric.weak_to_local_floor_db:.2f} dB")
    print(f"Metrics JSON: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
