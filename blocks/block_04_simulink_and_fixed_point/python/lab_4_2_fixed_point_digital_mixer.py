#!/usr/bin/env python3
"""Lab 4.2 — Fixed-point digital mixer.

This script generates a complex IQ tone, shifts it with a floating-point mixer,
implements an educational Q1.15 fixed-point mixer, estimates EVM/spurs and saves
IEEE-style figures.
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
    input_tone_hz: float = 120e3
    shift_hz: float = -120e3
    noise_rms: float = 0.01
    q_fractional_bits: int = 15
    phase_bits: int = 24
    seed: int = 11


ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"


def q15(v: np.ndarray, fractional_bits: int = 15) -> np.ndarray:
    scale = 2**fractional_bits
    return np.clip(np.round(v * scale), -32768, 32767).astype(np.int16)


def spectrum_db(x: np.ndarray, fs: float) -> tuple[np.ndarray, np.ndarray]:
    window = np.hanning(len(x))
    coherent_gain = np.sum(window) / len(window)
    xw = x * window
    spec = np.fft.fftshift(np.fft.fft(xw)) / (len(xw) * coherent_gain)
    freq = np.fft.fftshift(np.fft.fftfreq(len(xw), d=1 / fs))
    mag_db = 20 * np.log10(np.maximum(np.abs(spec), 1e-15))
    return freq, mag_db


def fixed_point_mixer_q15(x: np.ndarray, osc: np.ndarray, fractional_bits: int) -> tuple[np.ndarray, int]:
    scale = 2**fractional_bits
    xi = q15(np.real(x), fractional_bits)
    xq = q15(np.imag(x), fractional_bits)
    ci = q15(np.real(osc), fractional_bits)
    sq = q15(np.imag(osc), fractional_bits)

    n = len(x)
    yi = np.zeros(n, dtype=np.int16)
    yq = np.zeros(n, dtype=np.int16)
    saturation_count = 0

    for k in range(n):
        acc_i = int(xi[k]) * int(ci[k]) - int(xq[k]) * int(sq[k])
        acc_q = int(xi[k]) * int(sq[k]) + int(xq[k]) * int(ci[k])

        ri = int(np.round(acc_i / scale))
        rq = int(np.round(acc_q / scale))
        ri_sat = int(np.clip(ri, -32768, 32767))
        rq_sat = int(np.clip(rq, -32768, 32767))
        saturation_count += int(ri != ri_sat) + int(rq != rq_sat)

        yi[k] = ri_sat
        yq[k] = rq_sat

    y = (yi.astype(np.float64) + 1j * yq.astype(np.float64)) / scale
    return y, saturation_count


def estimate_peak_frequency(x: np.ndarray, fs: float) -> float:
    window = np.hanning(len(x))
    spec = np.fft.fftshift(np.fft.fft(x * window))
    freq = np.fft.fftshift(np.fft.fftfreq(len(x), d=1 / fs))
    return float(freq[int(np.argmax(np.abs(spec)))])


def estimate_spur_dbc(x: np.ndarray, fs: float, exclude_bins: int = 6) -> float:
    window = np.hanning(len(x))
    spec = np.abs(np.fft.fftshift(np.fft.fft(x * window)))
    peak_idx = int(np.argmax(spec))
    peak = float(spec[peak_idx])
    masked = spec.copy()
    lo = max(0, peak_idx - exclude_bins)
    hi = min(len(spec), peak_idx + exclude_bins + 1)
    masked[lo:hi] = 0.0
    spur = float(np.max(masked))
    return float(20 * np.log10(max(spur, 1e-15) / max(peak, 1e-15)))


def save_plot_spectrum(cfg: LabConfig, x: np.ndarray, y_float: np.ndarray, y_fixed: np.ndarray) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    f, xdb = spectrum_db(x, cfg.fs)
    _, yfdb = spectrum_db(y_float, cfg.fs)
    _, yqdb = spectrum_db(y_fixed, cfg.fs)

    plt.figure(figsize=(7.0, 4.2))
    plt.plot(f / 1e3, xdb, label="input")
    plt.plot(f / 1e3, yfdb, label="float mixer")
    plt.plot(f / 1e3, yqdb, label="fixed mixer")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Frequency, kHz")
    plt.ylabel("Magnitude, dBFS")
    plt.title("Lab 4.2 — Fixed-point mixer spectrum comparison")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab42_fixed_point_mixer_spectrum.png", dpi=180)
    plt.close()


def save_plot_error(cfg: LabConfig, err: np.ndarray) -> None:
    f, edb = spectrum_db(err, cfg.fs)

    plt.figure(figsize=(7.0, 4.2))
    plt.plot(f / 1e3, edb)
    plt.grid(True, alpha=0.35)
    plt.xlabel("Frequency, kHz")
    plt.ylabel("Error magnitude, dBFS")
    plt.title("Lab 4.2 — Fixed-point mixer error spectrum")
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab42_fixed_point_mixer_error.png", dpi=180)
    plt.close()


def save_plot_phase_resolution(cfg: LabConfig) -> None:
    bits = np.array([12, 16, 20, 24, 28, 32])
    resolution = cfg.fs / (2.0**bits)

    plt.figure(figsize=(7.0, 4.2))
    plt.semilogy(bits, resolution, marker="o")
    plt.grid(True, which="both", alpha=0.35)
    plt.xlabel("Phase accumulator width, bits")
    plt.ylabel("Frequency resolution, Hz")
    plt.title("Lab 4.2 — NCO frequency resolution")
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab42_nco_frequency_resolution.png", dpi=180)
    plt.close()


def main() -> None:
    cfg = LabConfig()
    rng = np.random.default_rng(cfg.seed)
    t = np.arange(cfg.sample_count) / cfg.fs

    x = np.exp(1j * 2 * np.pi * cfg.input_tone_hz * t)
    x += cfg.noise_rms * (rng.standard_normal(cfg.sample_count) + 1j * rng.standard_normal(cfg.sample_count))
    x = x / np.max(np.abs(x)) * 0.80

    phase_increment = int(round(cfg.shift_hz / cfg.fs * (2**cfg.phase_bits)))
    actual_shift_hz = phase_increment * cfg.fs / (2**cfg.phase_bits)
    phase = 2 * np.pi * (np.arange(cfg.sample_count) * phase_increment % (2**cfg.phase_bits)) / (2**cfg.phase_bits)
    osc = np.exp(1j * phase)

    y_float = x * np.exp(1j * 2 * np.pi * cfg.shift_hz * t)
    y_fixed, saturation_count = fixed_point_mixer_q15(x, osc, cfg.q_fractional_bits)

    err = y_float - y_fixed
    rms_error = float(np.sqrt(np.mean(np.abs(err) ** 2)))
    signal_rms = float(np.sqrt(np.mean(np.abs(y_float) ** 2)))
    evm_pct = float(100 * rms_error / max(signal_rms, 1e-15))
    expected_output_hz = cfg.input_tone_hz + cfg.shift_hz
    measured_peak_hz = estimate_peak_frequency(y_fixed, cfg.fs)
    frequency_shift_error_hz = measured_peak_hz - expected_output_hz
    spur_dbc = estimate_spur_dbc(y_fixed, cfg.fs)
    delta_f = cfg.fs / (2**cfg.phase_bits)

    save_plot_spectrum(cfg, x, y_float, y_fixed)
    save_plot_error(cfg, err)
    save_plot_phase_resolution(cfg)

    print("Lab 4.2 — Fixed-point digital mixer")
    print(f"Input tone: {cfg.input_tone_hz/1e3:.1f} kHz")
    print(f"Requested shift: {cfg.shift_hz/1e3:.1f} kHz")
    print(f"Actual NCO shift: {actual_shift_hz/1e3:.6f} kHz")
    print(f"Phase bits: {cfg.phase_bits}")
    print(f"NCO frequency resolution: {delta_f:.6f} Hz")
    print(f"Measured output peak: {measured_peak_hz:.3f} Hz")
    print(f"Frequency shift error: {frequency_shift_error_hz:.3f} Hz")
    print(f"RMS error: {rms_error:.6e}")
    print(f"EVM: {evm_pct:.4f} %")
    print(f"Largest spur estimate: {spur_dbc:.2f} dBc")
    print(f"Saturation count: {saturation_count}")
    print(f"Figures saved to: {ASSET_DIR}")


if __name__ == "__main__":
    main()
