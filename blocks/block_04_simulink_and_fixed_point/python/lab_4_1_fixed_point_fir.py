#!/usr/bin/env python3
"""Lab 4.1 — Fixed-point FIR filtering.

This script generates a synthetic complex IQ signal, designs a floating-point
low-pass FIR filter, quantizes the signal and coefficients to Q1.15, runs an
educational fixed-point FIR model and saves IEEE-style comparison figures.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


@dataclass(frozen=True)
class LabConfig:
    fs: float = 2.4e6
    sample_count: int = 32768
    wanted_hz: float = 120e3
    interferer_hz: float = 620e3
    interferer_amplitude: float = 0.35
    noise_rms: float = 0.02
    fir_taps: int = 129
    cutoff_hz: float = 250e3
    q_fractional_bits: int = 15
    seed: int = 7


ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"


def q15(v: np.ndarray, fractional_bits: int = 15) -> np.ndarray:
    scale = 2**fractional_bits
    return np.clip(np.round(v * scale), -32768, 32767).astype(np.int16)


def design_fir(cfg: LabConfig) -> np.ndarray:
    m = np.arange(cfg.fir_taps) - (cfg.fir_taps - 1) / 2
    h = 2 * cfg.cutoff_hz / cfg.fs * np.sinc(2 * cfg.cutoff_hz / cfg.fs * m)
    h *= np.blackman(cfg.fir_taps)
    h /= np.sum(h)
    return h


def fixed_point_fir_q15(x: np.ndarray, h: np.ndarray, fractional_bits: int) -> tuple[np.ndarray, int]:
    scale = 2**fractional_bits
    xi = q15(np.real(x), fractional_bits)
    xq = q15(np.imag(x), fractional_bits)
    hq = q15(h, fractional_bits)

    n = len(x)
    taps = len(hq)
    half = taps // 2
    yi = np.zeros(n, dtype=np.int16)
    yq = np.zeros(n, dtype=np.int16)
    saturation_count = 0

    for i in range(n):
        acc_i = 0
        acc_q = 0
        for k in range(taps):
            idx = i - k + half
            if 0 <= idx < n:
                acc_i += int(xi[idx]) * int(hq[k])
                acc_q += int(xq[idx]) * int(hq[k])

        ri = int(np.round(acc_i / scale))
        rq = int(np.round(acc_q / scale))
        ri_sat = int(np.clip(ri, -32768, 32767))
        rq_sat = int(np.clip(rq, -32768, 32767))
        saturation_count += int(ri != ri_sat) + int(rq != rq_sat)
        yi[i] = ri_sat
        yq[i] = rq_sat

    y = (yi.astype(np.float64) + 1j * yq.astype(np.float64)) / scale
    return y, saturation_count


def spectrum_db(x: np.ndarray, fs: float) -> tuple[np.ndarray, np.ndarray]:
    window = np.hanning(len(x))
    coherent_gain = np.sum(window) / len(window)
    xw = x * window
    spec = np.fft.fftshift(np.fft.fft(xw)) / (len(xw) * coherent_gain)
    freq = np.fft.fftshift(np.fft.fftfreq(len(xw), d=1 / fs))
    mag_db = 20 * np.log10(np.maximum(np.abs(spec), 1e-15))
    return freq, mag_db


def response_db(h: np.ndarray, fs: float, nfft: int = 16384) -> tuple[np.ndarray, np.ndarray]:
    hpad = np.zeros(nfft)
    hpad[: len(h)] = h
    spec = np.fft.fftshift(np.fft.fft(hpad))
    freq = np.fft.fftshift(np.fft.fftfreq(nfft, d=1 / fs))
    mag_db = 20 * np.log10(np.maximum(np.abs(spec), 1e-15))
    return freq, mag_db


def save_plot_response(cfg: LabConfig, h_float: np.ndarray, h_quant: np.ndarray) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    f1, h1 = response_db(h_float, cfg.fs)
    f2, h2 = response_db(h_quant, cfg.fs)

    plt.figure(figsize=(7.0, 4.2))
    plt.plot(f1 / 1e3, h1, label="float coefficients")
    plt.plot(f2 / 1e3, h2, label="Q1.15 coefficients")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Frequency, kHz")
    plt.ylabel("Magnitude, dB")
    plt.title("Lab 4.1 — FIR coefficient quantization")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab41_fixed_point_fir_response.png", dpi=180)
    plt.close()


def save_plot_spectrum(cfg: LabConfig, x: np.ndarray, y_float: np.ndarray, y_fixed: np.ndarray) -> None:
    f, xdb = spectrum_db(x, cfg.fs)
    _, yfdb = spectrum_db(y_float, cfg.fs)
    _, yqdb = spectrum_db(y_fixed, cfg.fs)

    plt.figure(figsize=(7.0, 4.2))
    plt.plot(f / 1e3, xdb, label="input")
    plt.plot(f / 1e3, yfdb, label="float FIR")
    plt.plot(f / 1e3, yqdb, label="fixed FIR")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Frequency, kHz")
    plt.ylabel("Magnitude, dBFS")
    plt.title("Lab 4.1 — Fixed-point FIR spectrum comparison")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab41_fixed_point_fir_spectrum.png", dpi=180)
    plt.close()


def save_plot_error(cfg: LabConfig, err: np.ndarray) -> None:
    f, edb = spectrum_db(err, cfg.fs)

    plt.figure(figsize=(7.0, 4.2))
    plt.plot(f / 1e3, edb)
    plt.grid(True, alpha=0.35)
    plt.xlabel("Frequency, kHz")
    plt.ylabel("Error magnitude, dBFS")
    plt.title("Lab 4.1 — Fixed-point FIR error spectrum")
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab41_fixed_point_fir_error.png", dpi=180)
    plt.close()


def main() -> None:
    cfg = LabConfig()
    rng = np.random.default_rng(cfg.seed)
    t = np.arange(cfg.sample_count) / cfg.fs

    x = (
        np.exp(1j * 2 * np.pi * cfg.wanted_hz * t)
        + cfg.interferer_amplitude * np.exp(1j * 2 * np.pi * cfg.interferer_hz * t)
        + cfg.noise_rms * (rng.standard_normal(cfg.sample_count) + 1j * rng.standard_normal(cfg.sample_count))
    )
    x = x / np.max(np.abs(x)) * 0.85

    h_float = design_fir(cfg)
    h_quant = q15(h_float, cfg.q_fractional_bits).astype(np.float64) / (2**cfg.q_fractional_bits)

    y_float = np.convolve(x, h_float, mode="same")
    y_fixed, saturation_count = fixed_point_fir_q15(x, h_float, cfg.q_fractional_bits)

    err = y_float - y_fixed
    rms_error = float(np.sqrt(np.mean(np.abs(err) ** 2)))
    signal_rms = float(np.sqrt(np.mean(np.abs(y_float) ** 2)))
    sqnr_db = float(20 * np.log10(signal_rms / max(rms_error, 1e-15)))
    max_abs_error = float(np.max(np.abs(err)))
    guard_bits = int(np.ceil(np.log2(cfg.fir_taps)))

    save_plot_response(cfg, h_float, h_quant)
    save_plot_spectrum(cfg, x, y_float, y_fixed)
    save_plot_error(cfg, err)

    print("Lab 4.1 — Fixed-point FIR")
    print(f"FIR taps: {cfg.fir_taps}")
    print(f"Cutoff: {cfg.cutoff_hz/1e3:.1f} kHz")
    print(f"Input/coefficient format: Q1.{cfg.q_fractional_bits}")
    print(f"Recommended FIR guard bits: {guard_bits}")
    print(f"RMS error: {rms_error:.6e}")
    print(f"Max abs error: {max_abs_error:.6e}")
    print(f"SQNR: {sqnr_db:.2f} dB")
    print(f"Saturation count: {saturation_count}")
    print(f"Figures saved to: {ASSET_DIR}")


if __name__ == "__main__":
    main()
