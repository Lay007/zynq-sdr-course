#!/usr/bin/env python3
"""Lab 7.5 — CIC decimator for SDR receiver chains.

This executable lab strengthens the DSP -> fixed-point -> FPGA bridge.
It models a CIC decimator, estimates bit growth, compares spectra before and
after decimation, and writes deterministic figures plus metrics for CI.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"


@dataclass(frozen=True)
class CicConfig:
    sample_rate_hz: float = 9_600_000.0
    decimation: int = 8
    stages: int = 4
    differential_delay: int = 1
    input_bits: int = 16
    sample_count: int = 262_144
    wanted_tone_hz: float = 220_000.0
    blocker_hz: float = 1_850_000.0
    noise_rms: float = 0.018


@dataclass(frozen=True)
class CicMetrics:
    input_sample_rate_hz: float
    output_sample_rate_hz: float
    decimation: int
    stages: int
    differential_delay: int
    input_bits: int
    theoretical_bit_growth_bits: int
    recommended_accumulator_bits: int
    passband_droop_db_at_wanted_tone: float
    wanted_tone_input_hz: float
    wanted_tone_output_hz: float
    blocker_input_hz: float
    blocker_alias_output_hz: float
    measured_output_peak_hz: float
    measured_output_frequency_error_hz: float


def make_input_signal(cfg: CicConfig) -> np.ndarray:
    rng = np.random.default_rng(705)
    n = np.arange(cfg.sample_count)
    t = n / cfg.sample_rate_hz
    wanted = 0.55 * np.exp(1j * 2.0 * np.pi * cfg.wanted_tone_hz * t)
    blocker = 0.11 * np.exp(1j * 2.0 * np.pi * cfg.blocker_hz * t)
    noise = cfg.noise_rms * (rng.standard_normal(cfg.sample_count) + 1j * rng.standard_normal(cfg.sample_count))
    return wanted + blocker + noise


def quantize_ci16(x: np.ndarray) -> np.ndarray:
    i = np.clip(np.round(np.real(x) * 32767.0), -32768, 32767).astype(np.int16)
    q = np.clip(np.round(np.imag(x) * 32767.0), -32768, 32767).astype(np.int16)
    return i.astype(np.int64) + 1j * q.astype(np.int64)


def cic_decimate_fixed_like(x: np.ndarray, cfg: CicConfig) -> np.ndarray:
    """CIC decimator using integer-like arithmetic and no multipliers.

    The implementation intentionally keeps wide Python integer semantics through
    int64 arrays to show the architecture and bit-growth requirement. A later RTL
    lab can map the same integrator/comb structure to fixed-width registers.
    """
    y_i = np.real(x).astype(np.int64)
    y_q = np.imag(x).astype(np.int64)

    for _ in range(cfg.stages):
        y_i = np.cumsum(y_i, dtype=np.int64)
        y_q = np.cumsum(y_q, dtype=np.int64)

    y_i = y_i[:: cfg.decimation]
    y_q = y_q[:: cfg.decimation]

    delay = cfg.differential_delay
    for _ in range(cfg.stages):
        y_i = y_i - np.concatenate([np.zeros(delay, dtype=np.int64), y_i[:-delay]])
        y_q = y_q - np.concatenate([np.zeros(delay, dtype=np.int64), y_q[:-delay]])

    gain = (cfg.decimation * cfg.differential_delay) ** cfg.stages
    return (y_i.astype(np.float64) + 1j * y_q.astype(np.float64)) / (32768.0 * gain)


def cic_response(cfg: CicConfig, points: int = 8192) -> tuple[np.ndarray, np.ndarray]:
    f = np.linspace(0.0, 0.5 * cfg.sample_rate_hz / cfg.decimation, points)
    numerator = np.sin(np.pi * f * cfg.decimation * cfg.differential_delay / cfg.sample_rate_hz)
    denominator = np.sin(np.pi * f / cfg.sample_rate_hz)
    response = np.ones_like(f)
    nonzero = np.abs(denominator) > 1e-15
    response[nonzero] = np.abs(numerator[nonzero] / denominator[nonzero]) ** cfg.stages
    response /= (cfg.decimation * cfg.differential_delay) ** cfg.stages
    response_db = 20.0 * np.log10(np.maximum(response, 1e-14))
    return f, response_db


def spectrum_db(x: np.ndarray, fs: float, fft_length: int = 65_536) -> tuple[np.ndarray, np.ndarray]:
    n = min(len(x), fft_length)
    window = np.hanning(n)
    cg = np.sum(window) / n
    spec = np.fft.fftshift(np.fft.fft(x[:n] * window, n=n)) / (n * cg)
    freq = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / fs))
    mag_db = 20.0 * np.log10(np.maximum(np.abs(spec), 1e-15))
    return freq, mag_db


def alias_frequency(freq_hz: float, fs_out: float) -> float:
    return ((freq_hz + 0.5 * fs_out) % fs_out) - 0.5 * fs_out


def estimate_peak(x: np.ndarray, fs: float) -> float:
    freq, mag = spectrum_db(x, fs)
    dc_mask = np.abs(freq) < 5_000.0
    idx = int(np.argmax(np.where(dc_mask, -1e9, mag)))
    return float(freq[idx])


def save_response_plot(cfg: CicConfig) -> None:
    f, response_db = cic_response(cfg)
    out = ASSET_DIR / "lab75_cic_response.png"
    plt.figure(figsize=(7.2, 4.3))
    plt.plot(f / 1e3, response_db, label="CIC response")
    plt.axvline(cfg.wanted_tone_hz / 1e3, linestyle="--", label="wanted tone")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Output-referenced frequency, kHz")
    plt.ylabel("Magnitude, dB")
    plt.title("Lab 7.5 — CIC decimator frequency response")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(out, dpi=180)
    plt.close()


def save_decimation_plot(cfg: CicConfig, x_in: np.ndarray, y_out: np.ndarray) -> None:
    fs_out = cfg.sample_rate_hz / cfg.decimation
    f_in, m_in = spectrum_db(x_in, cfg.sample_rate_hz)
    f_out, m_out = spectrum_db(y_out, fs_out)
    out = ASSET_DIR / "lab75_cic_decimation_spectrum.png"
    plt.figure(figsize=(7.2, 4.3))
    plt.plot(f_in / 1e3, m_in, label="input spectrum")
    plt.plot(f_out / 1e3, m_out, label="output spectrum")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Frequency, kHz")
    plt.ylabel("Magnitude, dBFS")
    plt.title("Lab 7.5 — input vs CIC-decimated spectrum")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(out, dpi=180)
    plt.close()


def save_bit_growth_plot(cfg: CicConfig) -> None:
    stages = np.arange(1, cfg.stages + 1)
    growth = np.ceil(stages * np.log2(cfg.decimation * cfg.differential_delay)).astype(int)
    out = ASSET_DIR / "lab75_cic_bit_growth.png"
    plt.figure(figsize=(7.2, 4.3))
    plt.step(stages, cfg.input_bits + growth, where="mid", label="recommended width")
    plt.scatter(stages, cfg.input_bits + growth)
    plt.grid(True, alpha=0.35)
    plt.xlabel("CIC stage count")
    plt.ylabel("Register width, bits")
    plt.title("Lab 7.5 — CIC accumulator bit growth")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(out, dpi=180)
    plt.close()


def main() -> int:
    cfg = CicConfig()
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    x = make_input_signal(cfg)
    xq = quantize_ci16(x)
    y = cic_decimate_fixed_like(xq, cfg)
    fs_out = cfg.sample_rate_hz / cfg.decimation

    f_resp, h_resp = cic_response(cfg)
    droop = float(np.interp(cfg.wanted_tone_hz, f_resp, h_resp))
    measured_peak = estimate_peak(y, fs_out)
    blocker_alias = alias_frequency(cfg.blocker_hz, fs_out)
    bit_growth = int(math.ceil(cfg.stages * math.log2(cfg.decimation * cfg.differential_delay)))

    metrics = CicMetrics(
        input_sample_rate_hz=cfg.sample_rate_hz,
        output_sample_rate_hz=fs_out,
        decimation=cfg.decimation,
        stages=cfg.stages,
        differential_delay=cfg.differential_delay,
        input_bits=cfg.input_bits,
        theoretical_bit_growth_bits=bit_growth,
        recommended_accumulator_bits=cfg.input_bits + bit_growth,
        passband_droop_db_at_wanted_tone=droop,
        wanted_tone_input_hz=cfg.wanted_tone_hz,
        wanted_tone_output_hz=cfg.wanted_tone_hz,
        blocker_input_hz=cfg.blocker_hz,
        blocker_alias_output_hz=blocker_alias,
        measured_output_peak_hz=measured_peak,
        measured_output_frequency_error_hz=measured_peak - cfg.wanted_tone_hz,
    )

    save_response_plot(cfg)
    save_decimation_plot(cfg, x, y)
    save_bit_growth_plot(cfg)
    metrics_path = ASSET_DIR / "lab75_cic_metrics.json"
    metrics_path.write_text(json.dumps(asdict(metrics), indent=2), encoding="utf-8")

    print(f"CIC decimation: {cfg.sample_rate_hz:.0f} -> {fs_out:.0f} Hz")
    print(f"Recommended accumulator width: {metrics.recommended_accumulator_bits} bits")
    print(f"Wanted-tone droop: {metrics.passband_droop_db_at_wanted_tone:.3f} dB")
    print(f"Measured output peak: {metrics.measured_output_peak_hz:.3f} Hz")
    print(f"Metrics JSON: {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
