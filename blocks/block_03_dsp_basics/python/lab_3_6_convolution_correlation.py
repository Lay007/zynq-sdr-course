#!/usr/bin/env python3
"""Lab 3.6 — Convolution vs correlation for SDR.

Deterministic script-driven lab: no notebooks. It separates convolution for
filtering from correlation for detection/synchronization and writes generated
figures plus JSON metrics for CI.
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
class ConvCorrMetrics:
    sample_count: int
    preamble_length: int
    true_delay_samples: int
    estimated_delay_samples: int
    delay_error_samples: int
    fir_tap_count: int
    input_snr_db: float
    correlation_peak_to_median_db: float
    output_rms_after_filter: float


def qpsk_preamble(length: int = 64) -> np.ndarray:
    rng = np.random.default_rng(360)
    bits = rng.integers(0, 4, size=length)
    symbols = np.exp(1j * (np.pi / 4.0 + bits * np.pi / 2.0))
    return symbols / np.sqrt(np.mean(np.abs(symbols) ** 2))


def lowpass_fir(num_taps: int = 41, cutoff: float = 0.18) -> np.ndarray:
    n = np.arange(num_taps) - (num_taps - 1) / 2.0
    h = 2.0 * cutoff * np.sinc(2.0 * cutoff * n)
    h *= np.blackman(num_taps)
    h /= np.sum(h)
    return h


def make_received_signal(preamble: np.ndarray, delay: int, n: int = 2048, snr_db: float = 9.0) -> np.ndarray:
    rng = np.random.default_rng(361)
    x = np.zeros(n, dtype=np.complex128)
    x[delay : delay + len(preamble)] = preamble
    channel = np.array([1.0 + 0.0j, 0.30 * np.exp(1j * 0.8), 0.16 * np.exp(-1j * 1.3)])
    y = np.convolve(x, channel, mode="same")
    signal_power = np.mean(np.abs(y) ** 2)
    noise_power = signal_power / (10.0 ** (snr_db / 10.0))
    noise = np.sqrt(noise_power / 2.0) * (rng.standard_normal(n) + 1j * rng.standard_normal(n))
    return y + noise


def matched_correlation(rx: np.ndarray, preamble: np.ndarray) -> np.ndarray:
    return np.abs(np.correlate(rx, preamble, mode="valid"))


def save_filtering_plot(rx: np.ndarray, filtered: np.ndarray) -> None:
    n = min(500, len(rx), len(filtered))
    out = ASSET_DIR / "lab36_convolution_filtering.png"
    plt.figure(figsize=(7.2, 4.3))
    plt.plot(np.abs(rx[:n]), label="received magnitude")
    plt.plot(np.abs(filtered[:n]), label="after FIR convolution")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Sample index")
    plt.ylabel("Magnitude")
    plt.title("Lab 3.6 — Convolution as filtering")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(out, dpi=180)
    plt.close()


def save_correlation_plot(corr: np.ndarray, true_delay: int, estimated_delay: int) -> None:
    out = ASSET_DIR / "lab36_correlation_detection.png"
    plt.figure(figsize=(7.2, 4.3))
    plt.plot(corr, label="matched correlation")
    plt.axvline(true_delay, linestyle="--", label="true delay")
    plt.axvline(estimated_delay, linestyle=":", label="estimated delay")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Candidate delay, samples")
    plt.ylabel("Correlation magnitude")
    plt.title("Lab 3.6 — Correlation for preamble detection")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(out, dpi=180)
    plt.close()


def main() -> int:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    snr_db = 9.0
    true_delay = 512
    preamble = qpsk_preamble(64)
    rx = make_received_signal(preamble, true_delay, snr_db=snr_db)
    h = lowpass_fir()
    filtered = np.convolve(rx, h, mode="same")
    corr = matched_correlation(filtered, preamble)
    estimated_delay = int(np.argmax(corr))
    peak = float(np.max(corr))
    median = float(np.median(corr))
    peak_to_median_db = 20.0 * np.log10(max(peak, 1e-15) / max(median, 1e-15))

    save_filtering_plot(rx, filtered)
    save_correlation_plot(corr, true_delay, estimated_delay)

    metrics = ConvCorrMetrics(
        sample_count=int(len(rx)),
        preamble_length=int(len(preamble)),
        true_delay_samples=true_delay,
        estimated_delay_samples=estimated_delay,
        delay_error_samples=estimated_delay - true_delay,
        fir_tap_count=int(len(h)),
        input_snr_db=snr_db,
        correlation_peak_to_median_db=peak_to_median_db,
        output_rms_after_filter=float(np.sqrt(np.mean(np.abs(filtered) ** 2))),
    )
    out = ASSET_DIR / "lab36_correlation_metrics.json"
    out.write_text(json.dumps(asdict(metrics), indent=2), encoding="utf-8")
    print(f"Estimated delay: {estimated_delay} samples")
    print(f"Delay error: {metrics.delay_error_samples} samples")
    print(f"Correlation peak/median: {peak_to_median_db:.2f} dB")
    print(f"Metrics JSON: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
