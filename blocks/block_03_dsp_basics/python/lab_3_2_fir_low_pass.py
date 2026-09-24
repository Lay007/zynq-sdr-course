#!/usr/bin/env python3
"""Lab 3.2 — FIR low-pass filtering of IQ data.

Deterministic script-driven lab. A 129-tap Blackman windowed-sinc low-pass
filter removes an interferer from complex IQ data. The script reports the
filter's own response (passband gain, -3 dB edge, transition width, group
delay), the measured interferer suppression on the signal, and the effect of
quantizing the taps to Q1.15.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"

FS_HZ = 2.4e6
N = 32768
WANTED_HZ = 120e3
INTERFERER_HZ = 620e3
INTERFERER_AMPLITUDE = 0.35
NOISE_RMS = 0.03
NUM_TAPS = 129
CUTOFF_HZ = 250e3
SEED = 32
STOPBAND_START_HZ = 400e3


def design_lowpass(
    num_taps: int = NUM_TAPS, cutoff_hz: float = CUTOFF_HZ, fs_hz: float = FS_HZ
) -> np.ndarray:
    m = np.arange(num_taps) - (num_taps - 1) / 2
    h = 2.0 * cutoff_hz / fs_hz * np.sinc(2.0 * cutoff_hz / fs_hz * m)
    h *= np.blackman(num_taps)
    return h / np.sum(h)


def quantize_q15(h: np.ndarray) -> np.ndarray:
    return np.round(h * 32768.0) / 32768.0


def response_db(h: np.ndarray, freqs_hz: np.ndarray) -> np.ndarray:
    n = np.arange(len(h))
    resp = np.exp(-1j * 2.0 * np.pi * np.outer(freqs_hz, n) / FS_HZ) @ h
    return 20.0 * np.log10(np.maximum(np.abs(resp), 1e-15))


def make_signal() -> np.ndarray:
    rng = np.random.default_rng(SEED)
    t = np.arange(N) / FS_HZ
    wanted = np.exp(1j * 2.0 * np.pi * WANTED_HZ * t)
    interferer = INTERFERER_AMPLITUDE * np.exp(1j * 2.0 * np.pi * INTERFERER_HZ * t)
    noise = NOISE_RMS * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
    return wanted + interferer + noise


def tone_level_db(x: np.ndarray, freq_hz: float) -> float:
    w = np.hanning(len(x))
    spec = np.fft.fft(x * w) / np.sum(w)
    k = int(round(freq_hz / FS_HZ * len(x))) % len(x)
    return float(20.0 * np.log10(np.max(np.abs(spec[k - 2 : k + 3]))))


def main() -> int:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    h = design_lowpass()
    hq = quantize_q15(h)
    grid = np.linspace(0.0, FS_HZ / 2, 12001)
    resp = response_db(h, grid)
    resp_q = response_db(hq, grid)

    minus3_hz = float(grid[np.argmax(resp < -3.0)])
    first_minus60 = float(grid[np.argmax(resp < -60.0)])
    stopband = grid >= STOPBAND_START_HZ
    stop_peak_db = float(np.max(resp[stopband]))
    stop_peak_q_db = float(np.max(resp_q[stopband]))

    x = make_signal()
    y = np.convolve(x, h, mode="same")
    before_i = tone_level_db(x, INTERFERER_HZ)
    after_i = tone_level_db(y, INTERFERER_HZ)
    before_w = tone_level_db(x, WANTED_HZ)
    after_w = tone_level_db(y, WANTED_HZ)

    metrics = {
        "config": {
            "sample_rate_hz": FS_HZ,
            "samples": N,
            "wanted_hz": WANTED_HZ,
            "interferer_hz": INTERFERER_HZ,
            "interferer_amplitude": INTERFERER_AMPLITUDE,
            "num_taps": NUM_TAPS,
            "cutoff_hz": CUTOFF_HZ,
            "window": "blackman",
            "seed": SEED,
        },
        "filter": {
            "gain_at_wanted_db": float(response_db(h, np.array([WANTED_HZ]))[0]),
            "gain_at_interferer_db": float(
                response_db(h, np.array([INTERFERER_HZ]))[0]
            ),
            "minus3db_edge_hz": minus3_hz,
            "first_minus60db_hz": first_minus60,
            "transition_width_hz": first_minus60 - minus3_hz,
            "stopband_start_hz": STOPBAND_START_HZ,
            "stopband_peak_db": stop_peak_db,
            "group_delay_samples": (NUM_TAPS - 1) / 2,
            "group_delay_us": (NUM_TAPS - 1) / 2 / FS_HZ * 1e6,
            "q15_stopband_peak_db": stop_peak_q_db,
        },
        "signal": {
            "interferer_before_dbfs": before_i,
            "interferer_after_dbfs": after_i,
            "interferer_suppression_db": before_i - after_i,
            "wanted_change_db": after_w - before_w,
        },
    }
    out = ASSET_DIR / "lab32_fir_low_pass_metrics.json"
    out.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    fig, axes = plt.subplots(2, 1, figsize=(7.4, 6.4))
    axes[0].plot(grid / 1e3, resp, label="float taps")
    axes[0].plot(grid / 1e3, resp_q, label="Q1.15 taps", alpha=0.7)
    axes[0].axvline(WANTED_HZ / 1e3, linestyle=":", color="g")
    axes[0].axvline(INTERFERER_HZ / 1e3, linestyle=":", color="r")
    axes[0].set_ylim(-160, 5)
    axes[0].set_ylabel("Gain, dB")
    axes[0].set_title("Lab 3.2 — 129-tap Blackman low-pass, cutoff 250 kHz")
    axes[0].legend(loc="upper right")
    axes[0].grid(True, alpha=0.35)
    freq = np.fft.fftshift(np.fft.fftfreq(N, d=1 / FS_HZ))
    wind = np.hanning(N)
    for sig, label in ((x, "before"), (y, "after")):
        spec = np.fft.fftshift(np.fft.fft(sig * wind)) / np.sum(wind)
        axes[1].plot(
            freq / 1e3,
            20 * np.log10(np.maximum(np.abs(spec), 1e-12)),
            label=label,
            linewidth=0.8,
        )
    axes[1].set_xlabel("Frequency, kHz")
    axes[1].set_ylabel("Magnitude, dBFS")
    axes[1].set_ylim(-140, 5)
    axes[1].legend(loc="upper right")
    axes[1].grid(True, alpha=0.35)
    fig.tight_layout()
    fig.savefig(ASSET_DIR / "lab32_fir_low_pass.png", dpi=160)
    plt.close(fig)

    f = metrics["filter"]
    s = metrics["signal"]
    print("Lab 3.2 - FIR low-pass filtering of IQ data")
    print(
        f"Gain at 120 kHz / 620 kHz: {f['gain_at_wanted_db']:.3f} / {f['gain_at_interferer_db']:.1f} dB"
    )
    print(
        f"-3 dB edge: {f['minus3db_edge_hz'] / 1e3:.1f} kHz, first -60 dB point: {f['first_minus60db_hz'] / 1e3:.1f} kHz"
    )
    print(f"Transition width (-3 to -60 dB): {f['transition_width_hz'] / 1e3:.1f} kHz")
    print(
        f"Stopband peak above 400 kHz: float {f['stopband_peak_db']:.1f} dB, Q1.15 {f['q15_stopband_peak_db']:.1f} dB"
    )
    print(
        f"Group delay: {f['group_delay_samples']:.0f} samples ({f['group_delay_us']:.2f} us)"
    )
    print(
        f"Interferer: {s['interferer_before_dbfs']:.1f} -> {s['interferer_after_dbfs']:.1f} dBFS "
        f"(suppression {s['interferer_suppression_db']:.1f} dB), wanted change {s['wanted_change_db']:+.3f} dB"
    )
    print(f"Metrics JSON: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
