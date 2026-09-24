#!/usr/bin/env python3
"""Lab 3.4 — Decimation with an anti-aliasing filter.

Deterministic script-driven lab. Complex IQ at 2.4 MS/s carries a wanted tone
at +80 kHz and an interferer at +520 kHz. Decimating by 4 (to 600 kS/s)
without a filter folds the interferer to 520 - 600 = -80 kHz, right beside
the wanted signal. Filtering first with a 129-tap low-pass removes it.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"

FS_HZ = 2.4e6
M = 4
FS_OUT_HZ = FS_HZ / M
N = 65536
WANTED_HZ = 80e3
INTERFERER_HZ = 520e3
INTERFERER_AMPLITUDE = 0.5
NUM_TAPS = 129
CUTOFF_HZ = 0.40 * FS_OUT_HZ


def alias_hz(freq_hz: float, fs_hz: float) -> float:
    """Where a complex tone lands after sampling at fs_hz (range [-fs/2, fs/2))."""
    return float((freq_hz + fs_hz / 2) % fs_hz - fs_hz / 2)


def design_lowpass(
    num_taps: int = NUM_TAPS, cutoff_hz: float = CUTOFF_HZ
) -> np.ndarray:
    m = np.arange(num_taps) - (num_taps - 1) / 2
    h = 2.0 * cutoff_hz / FS_HZ * np.sinc(2.0 * cutoff_hz / FS_HZ * m)
    h *= np.blackman(num_taps)
    return h / np.sum(h)


def make_signal() -> np.ndarray:
    t = np.arange(N) / FS_HZ
    return np.exp(1j * 2 * np.pi * WANTED_HZ * t) + INTERFERER_AMPLITUDE * np.exp(
        1j * 2 * np.pi * INTERFERER_HZ * t
    )


def level_at(x: np.ndarray, fs_hz: float, freq_hz: float) -> float:
    w = np.blackman(len(x))
    spec = np.fft.fft(x * w) / np.sum(w)
    k = int(round(freq_hz / fs_hz * len(x))) % len(x)
    return float(20.0 * np.log10(max(np.max(np.abs(spec[k - 3 : k + 4])), 1e-15)))


def spectrum(x: np.ndarray, fs_hz: float) -> tuple[np.ndarray, np.ndarray]:
    w = np.blackman(len(x))
    spec = np.fft.fftshift(np.fft.fft(x * w)) / np.sum(w)
    freq = np.fft.fftshift(np.fft.fftfreq(len(x), d=1.0 / fs_hz))
    return freq, 20.0 * np.log10(np.maximum(np.abs(spec), 1e-15))


def main() -> int:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    x = make_signal()
    y_bad = x[::M]
    h = design_lowpass()
    y_good = np.convolve(x, h, mode="same")[::M]

    alias = alias_hz(INTERFERER_HZ, FS_OUT_HZ)
    bad_alias_dbc = level_at(y_bad, FS_OUT_HZ, alias) - level_at(
        y_bad, FS_OUT_HZ, WANTED_HZ
    )
    good_alias_dbc = level_at(y_good, FS_OUT_HZ, alias) - level_at(
        y_good, FS_OUT_HZ, WANTED_HZ
    )

    metrics = {
        "config": {
            "input_rate_hz": FS_HZ,
            "decimation": M,
            "output_rate_hz": FS_OUT_HZ,
            "wanted_hz": WANTED_HZ,
            "interferer_hz": INTERFERER_HZ,
            "interferer_amplitude": INTERFERER_AMPLITUDE,
            "num_taps": NUM_TAPS,
            "cutoff_hz": CUTOFF_HZ,
        },
        "output_nyquist_hz": FS_OUT_HZ / 2,
        "predicted_alias_hz": alias,
        "no_filter_alias_dbc": bad_alias_dbc,
        "filtered_alias_dbc": good_alias_dbc,
        "alias_suppression_db": bad_alias_dbc - good_alias_dbc,
        "output_samples": len(y_good),
    }
    out = ASSET_DIR / "lab34_decimation_metrics.json"
    out.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    for sig, label in ((y_bad, "decimate only"), (y_good, "FIR, then decimate")):
        f, m = spectrum(sig, FS_OUT_HZ)
        ax.plot(f / 1e3, m, label=label, linewidth=0.8)
    ax.axvline(
        alias / 1e3,
        linestyle=":",
        color="r",
        label=f"alias of 520 kHz ({alias / 1e3:.0f} kHz)",
    )
    ax.set_ylim(-160, 5)
    ax.set_xlabel("Frequency at 600 kS/s, kHz")
    ax.set_ylabel("Magnitude, dBFS")
    ax.set_title("Lab 3.4 — Decimation by 4 with and without anti-aliasing")
    ax.grid(True, alpha=0.35)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(ASSET_DIR / "lab34_decimation.png", dpi=160)
    plt.close(fig)

    print("Lab 3.4 - Decimation with anti-aliasing")
    print(
        f"Fs in/out: {FS_HZ / 1e6:.1f} / {FS_OUT_HZ / 1e3:.0f} kS/s, new Nyquist band +/-{FS_OUT_HZ / 2e3:.0f} kHz"
    )
    print(f"520 kHz interferer is predicted to alias to {alias / 1e3:.0f} kHz")
    print(
        f"Alias relative to wanted tone: no filter {bad_alias_dbc:.1f} dBc, with FIR {good_alias_dbc:.1f} dBc"
    )
    print(
        f"Alias suppression by the anti-aliasing filter: {metrics['alias_suppression_db']:.1f} dB"
    )
    print(f"Metrics JSON: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
