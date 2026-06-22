#!/usr/bin/env python3
"""Analyze the deterministic synthetic QPSK dataset and generate report-ready assets."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml


ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "datasets" / "demo_qpsk_capture"
MANIFEST_FILE = DATASET_DIR / "manifest.yaml"
METRICS_FILE = DATASET_DIR / "metrics.json"
DATA_FILE = DATASET_DIR / "demo_qpsk_capture.ci16"
ANALYSIS_JSON = DATASET_DIR / "analysis_summary.json"

ASSETS_DIR = ROOT / "docs" / "assets"
CONSTELLATION_SVG = ASSETS_DIR / "demo_qpsk_constellation.svg"
SPECTRUM_SVG = ASSETS_DIR / "demo_qpsk_spectrum.svg"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def ensure_dataset_file(generate_if_missing: bool) -> None:
    if DATA_FILE.exists():
        return
    if not generate_if_missing:
        raise FileNotFoundError(
            f"Missing dataset file: {DATA_FILE}. Run: python tools/generate_demo_qpsk_dataset.py"
        )
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "generate_demo_qpsk_dataset.py")],
        check=True,
    )


def read_ci16(path: Path) -> np.ndarray:
    raw = np.fromfile(path, dtype="<i2")
    if raw.size % 2 != 0:
        raise ValueError("CI16 file must contain an even number of int16 values.")
    i = raw[0::2].astype(np.float64)
    q = raw[1::2].astype(np.float64)
    return i + 1j * q


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.abs(x) ** 2)))


def analyze(samples_ci16: np.ndarray, sample_rate_hz: int, sps: int, ci16_amplitude: float) -> tuple[dict[str, Any], np.ndarray, np.ndarray, np.ndarray]:
    samples = samples_ci16 / ci16_amplitude
    symbols = samples[sps // 2 :: sps]

    ideal = (np.sign(np.real(symbols)) + 1j * np.sign(np.imag(symbols))) / math.sqrt(2.0)
    evm_vec = symbols - ideal
    evm_rms = math.sqrt(float(np.mean(np.abs(evm_vec) ** 2) / np.mean(np.abs(ideal) ** 2)))
    evm_peak = float(np.max(np.abs(evm_vec)) / math.sqrt(np.mean(np.abs(ideal) ** 2)))
    snr_est_db = float(-20.0 * math.log10(max(evm_rms, 1e-15)))

    fourth = symbols**4
    phase = np.unwrap(np.angle(fourth))
    slope, _ = np.polyfit(np.arange(phase.size), phase, 1)
    symbol_period_s = sps / sample_rate_hz
    cfo_est_hz = float(slope / (4.0 * 2.0 * math.pi * symbol_period_s))

    nfft = 16384
    spectrum = np.fft.fftshift(np.fft.fft(samples, n=nfft))
    freq = np.fft.fftshift(np.fft.fftfreq(nfft, d=1.0 / sample_rate_hz))
    psd_db = 20.0 * np.log10(np.maximum(np.abs(spectrum) / np.max(np.abs(spectrum)), 1e-12))

    power = np.abs(np.fft.fftshift(np.fft.fft(samples, n=65536))) ** 2
    pw_freq = np.fft.fftshift(np.fft.fftfreq(65536, d=1.0 / sample_rate_hz))
    idx = np.argsort(np.abs(pw_freq))
    csum = np.cumsum(power[idx])
    total = float(csum[-1])

    def power_bw(frac: float) -> float:
        k = int(np.searchsorted(csum, total * frac))
        return float(2.0 * abs(pw_freq[idx[k]]))

    summary: dict[str, Any] = {
        "dataset_id": "demo_qpsk_capture",
        "sample_rate_hz": int(sample_rate_hz),
        "samples_per_symbol": int(sps),
        "num_samples": int(samples.size),
        "num_symbols": int(symbols.size),
        "ci16_amplitude": float(ci16_amplitude),
        "mean_i_normalized": float(np.mean(np.real(samples))),
        "mean_q_normalized": float(np.mean(np.imag(samples))),
        "rms_normalized": rms(samples),
        "peak_normalized": float(np.max(np.abs(samples))),
        "evm_rms_percent": float(evm_rms * 100.0),
        "evm_peak_percent": float(evm_peak * 100.0),
        "snr_estimate_db": snr_est_db,
        "cfo_estimate_hz": cfo_est_hz,
        "power_bandwidth_90pct_hz": power_bw(0.90),
        "power_bandwidth_95pct_hz": power_bw(0.95),
    }
    return summary, symbols, freq, psd_db


def save_constellation(symbols: np.ndarray) -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(6, 6))
    plt.plot(np.real(symbols), np.imag(symbols), ".", markersize=3)
    ideal = np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j]) / math.sqrt(2.0)
    plt.plot(np.real(ideal), np.imag(ideal), "x", markersize=10)
    plt.xlabel("In-phase")
    plt.ylabel("Quadrature")
    plt.title("Synthetic QPSK Constellation")
    plt.grid(True)
    plt.axis("equal")
    plt.tight_layout()
    plt.savefig(CONSTELLATION_SVG, format="svg")
    plt.close()


def save_spectrum(freq: np.ndarray, psd_db: np.ndarray) -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7, 4))
    plt.plot(freq / 1e3, psd_db)
    plt.xlabel("Frequency offset (kHz)")
    plt.ylabel("Magnitude (dBFS, normalized)")
    plt.title("Synthetic QPSK Spectrum")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(SPECTRUM_SVG, format="svg")
    plt.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--generate-if-missing",
        action="store_true",
        help="Automatically generate the CI16 dataset if it is missing.",
    )
    args = parser.parse_args()

    manifest = load_yaml(MANIFEST_FILE)
    metrics = load_json(METRICS_FILE)

    ensure_dataset_file(args.generate_if_missing)
    samples_ci16 = read_ci16(DATA_FILE)

    sample_rate_hz = int(manifest["sample_rate_hz"])
    sps = int(manifest["signal"]["samples_per_symbol"])
    ci16_amplitude = float(metrics["ci16_amplitude"])

    summary, symbols, freq, psd_db = analyze(samples_ci16, sample_rate_hz, sps, ci16_amplitude)

    ANALYSIS_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    save_constellation(symbols)
    save_spectrum(freq, psd_db)

    print(f"Wrote {ANALYSIS_JSON.relative_to(ROOT)}")
    print(f"Wrote {CONSTELLATION_SVG.relative_to(ROOT)}")
    print(f"Wrote {SPECTRUM_SVG.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
