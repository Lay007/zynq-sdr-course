#!/usr/bin/env python3
"""Lab 7.2 — DUC/DDC frequency translation model.

This script models a simple transmit/receive frequency plan:

  TX baseband tone -> DUC shift -> RF frequency plan -> RX observed offset -> DDC shift

It saves IEEE-style FFT figures and a small metrics JSON file. The goal is to
make the sign convention and frequency-plan arithmetic reproducible before
moving the chain to RF hardware or HDL.
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
class ChainConfig:
    fs_hz: float = 2.4e6
    sample_count: int = 65536
    tx_lo_hz: float = 915e6
    rx_lo_hz: float = 915e6
    tx_baseband_tone_hz: float = 0.0
    tx_duc_shift_hz: float = 100e3
    ddc_shift_hz: float = -100e3
    tone_amplitude: float = 0.75
    noise_rms: float = 0.015
    seed: int = 77


@dataclass(frozen=True)
class ChainMetrics:
    tx_rf_hz: float
    rx_observed_offset_hz: float
    ddc_shift_hz: float
    final_peak_hz: float
    final_frequency_error_hz: float
    rx_peak_hz: float
    snr_db: float


def complex_tone(freq_hz: float, fs_hz: float, n: int, amplitude: float = 1.0) -> np.ndarray:
    t = np.arange(n) / fs_hz
    return amplitude * np.exp(1j * 2 * np.pi * freq_hz * t)


def spectrum_db(x: np.ndarray, fs_hz: float) -> tuple[np.ndarray, np.ndarray]:
    window = np.hanning(len(x))
    coherent_gain = np.sum(window) / len(window)
    spec = np.fft.fftshift(np.fft.fft(x * window)) / (len(x) * coherent_gain)
    freq = np.fft.fftshift(np.fft.fftfreq(len(x), d=1 / fs_hz))
    mag_db = 20 * np.log10(np.maximum(np.abs(spec), 1e-15))
    return freq, mag_db


def estimate_peak_hz(x: np.ndarray, fs_hz: float) -> float:
    freq, mag_db = spectrum_db(x, fs_hz)
    return float(freq[int(np.argmax(mag_db))])


def estimate_snr_db(x: np.ndarray, fs_hz: float, peak_hz: float) -> float:
    freq, mag_db = spectrum_db(x, fs_hz)
    peak_idx = int(np.argmin(np.abs(freq - peak_hz)))
    peak_db = float(mag_db[peak_idx])
    bin_width = fs_hz / len(x)
    signal_mask = np.abs(freq - peak_hz) < max(15e3, 20 * bin_width)
    dc_mask = np.abs(freq) < 5e3
    noise_mask = ~(signal_mask | dc_mask)
    noise_floor_db = float(np.median(mag_db[noise_mask]))
    return peak_db - noise_floor_db


def save_spectrum(path: Path, fs_hz: float, traces: list[tuple[str, np.ndarray]], title: str) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7.2, 4.3))
    for label, signal in traces:
        freq, mag_db = spectrum_db(signal, fs_hz)
        plt.plot(freq / 1e3, mag_db, label=label)
    plt.grid(True, alpha=0.35)
    plt.xlabel("Frequency, kHz")
    plt.ylabel("Magnitude, dBFS")
    plt.title(title)
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def save_frequency_plan_plot(path: Path, cfg: ChainConfig, metrics: ChainMetrics) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    labels = ["TX DUC output", "RX observed", "After DDC"]
    values = [cfg.tx_duc_shift_hz, metrics.rx_observed_offset_hz, metrics.final_peak_hz]

    plt.figure(figsize=(7.2, 4.3))
    markerline, stemlines, baseline = plt.stem(labels, np.array(values) / 1e3)
    plt.setp(markerline, markersize=7)
    plt.setp(stemlines, linewidth=1.5)
    plt.grid(True, axis="y", alpha=0.35)
    plt.ylabel("Baseband frequency, kHz")
    plt.title("Lab 7.2 — Frequency translation checkpoints")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def main() -> None:
    cfg = ChainConfig()
    rng = np.random.default_rng(cfg.seed)

    tx_baseband = complex_tone(cfg.tx_baseband_tone_hz, cfg.fs_hz, cfg.sample_count, cfg.tone_amplitude)
    duc_osc = complex_tone(cfg.tx_duc_shift_hz, cfg.fs_hz, cfg.sample_count)
    tx_duc = tx_baseband * duc_osc

    tx_rf_hz = cfg.tx_lo_hz + cfg.tx_duc_shift_hz + cfg.tx_baseband_tone_hz
    rx_observed_offset_hz = tx_rf_hz - cfg.rx_lo_hz

    rx_observed = complex_tone(rx_observed_offset_hz, cfg.fs_hz, cfg.sample_count, cfg.tone_amplitude)
    rx_observed += cfg.noise_rms * (
        rng.standard_normal(cfg.sample_count) + 1j * rng.standard_normal(cfg.sample_count)
    )

    ddc_osc = complex_tone(cfg.ddc_shift_hz, cfg.fs_hz, cfg.sample_count)
    after_ddc = rx_observed * ddc_osc

    rx_peak_hz = estimate_peak_hz(rx_observed, cfg.fs_hz)
    final_peak_hz = estimate_peak_hz(after_ddc, cfg.fs_hz)
    expected_final_hz = rx_observed_offset_hz + cfg.ddc_shift_hz
    final_frequency_error_hz = final_peak_hz - expected_final_hz
    snr_db = estimate_snr_db(after_ddc, cfg.fs_hz, final_peak_hz)

    metrics = ChainMetrics(
        tx_rf_hz=tx_rf_hz,
        rx_observed_offset_hz=rx_observed_offset_hz,
        ddc_shift_hz=cfg.ddc_shift_hz,
        final_peak_hz=final_peak_hz,
        final_frequency_error_hz=final_frequency_error_hz,
        rx_peak_hz=rx_peak_hz,
        snr_db=snr_db,
    )

    save_spectrum(
        ASSET_DIR / "lab72_duc_ddc_tx_spectrum.png",
        cfg.fs_hz,
        [("TX baseband", tx_baseband), ("After DUC", tx_duc)],
        "Lab 7.2 — TX baseband and DUC spectrum",
    )
    save_spectrum(
        ASSET_DIR / "lab72_duc_ddc_rx_spectrum.png",
        cfg.fs_hz,
        [("RX observed", rx_observed), ("After DDC", after_ddc)],
        "Lab 7.2 — RX observed and DDC spectrum",
    )
    save_frequency_plan_plot(ASSET_DIR / "lab72_duc_ddc_frequency_plan.png", cfg, metrics)

    metrics_path = ASSET_DIR / "lab72_duc_ddc_metrics.json"
    metrics_path.write_text(
        json.dumps({"config": asdict(cfg), "metrics": asdict(metrics)}, indent=2),
        encoding="utf-8",
    )

    print("Lab 7.2 — DUC/DDC frequency translation")
    print(f"TX LO: {cfg.tx_lo_hz/1e6:.6f} MHz")
    print(f"RX LO: {cfg.rx_lo_hz/1e6:.6f} MHz")
    print(f"TX DUC shift: {cfg.tx_duc_shift_hz:.3f} Hz")
    print(f"TX RF frequency: {metrics.tx_rf_hz:.3f} Hz")
    print(f"RX observed offset: {metrics.rx_observed_offset_hz:.3f} Hz")
    print(f"DDC shift: {metrics.ddc_shift_hz:.3f} Hz")
    print(f"RX peak: {metrics.rx_peak_hz:.3f} Hz")
    print(f"Final peak after DDC: {metrics.final_peak_hz:.3f} Hz")
    print(f"Final frequency error: {metrics.final_frequency_error_hz:.3f} Hz")
    print(f"SNR estimate after DDC: {metrics.snr_db:.2f} dB")
    print(f"Metrics JSON: {metrics_path}")


if __name__ == "__main__":
    main()
