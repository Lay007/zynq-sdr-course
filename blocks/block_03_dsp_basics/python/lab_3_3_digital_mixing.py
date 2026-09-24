#!/usr/bin/env python3
"""Lab 3.3 — Digital mixing and frequency shift with an NCO.

Deterministic script-driven lab. A complex tone at +420 kHz is shifted to DC
three ways: an ideal floating-point complex exponential, the same shift with
the wrong sign, and a hardware-style NCO (32-bit phase accumulator addressing
a 1024-entry Q1.15 sine/cosine table). The script reports where the tone
lands and how clean the hardware-style NCO output is (worst spur).
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
TONE_HZ = 420e3
SHIFT_HZ = -420e3
ACC_BITS = 32
LUT_ADDR_BITS = 10
AMP_BITS = 16


def ideal_nco(shift_hz: float, n: int = N) -> np.ndarray:
    return np.exp(1j * 2.0 * np.pi * shift_hz * np.arange(n) / FS_HZ)


def phase_increment(shift_hz: float, acc_bits: int = ACC_BITS) -> int:
    return int(round(shift_hz / FS_HZ * 2**acc_bits)) % 2**acc_bits


def hardware_nco(
    shift_hz: float,
    n: int = N,
    acc_bits: int = ACC_BITS,
    lut_addr_bits: int = LUT_ADDR_BITS,
    amp_bits: int = AMP_BITS,
) -> np.ndarray:
    """Phase accumulator -> truncated address -> quantized sin/cos table."""
    inc = phase_increment(shift_hz, acc_bits)
    acc = (np.arange(n, dtype=np.uint64) * np.uint64(inc)) % np.uint64(2**acc_bits)
    addr = (acc >> np.uint64(acc_bits - lut_addr_bits)).astype(np.int64)
    lut_phase = 2.0 * np.pi * np.arange(2**lut_addr_bits) / 2**lut_addr_bits
    scale = 2 ** (amp_bits - 1) - 1
    cos_lut = np.round(np.cos(lut_phase) * scale) / scale
    sin_lut = np.round(np.sin(lut_phase) * scale) / scale
    return cos_lut[addr] + 1j * sin_lut[addr]


def spectrum_db(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    w = np.blackman(len(x))
    spec = np.fft.fftshift(np.fft.fft(x * w)) / np.sum(w)
    freq = np.fft.fftshift(np.fft.fftfreq(len(x), d=1.0 / FS_HZ))
    return freq, 20.0 * np.log10(np.maximum(np.abs(spec), 1e-15))


def peak_hz(x: np.ndarray) -> float:
    freq, mag = spectrum_db(x)
    return float(freq[int(np.argmax(mag))])


def worst_spur_dbc(x: np.ndarray, exclude_bins: int = 8) -> float:
    freq, mag = spectrum_db(x)
    k = int(np.argmax(mag))
    mask = np.ones(len(mag), dtype=bool)
    mask[max(0, k - exclude_bins) : k + exclude_bins + 1] = False
    return float(np.max(mag[mask]) - mag[k])


def main() -> int:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    t = np.arange(N) / FS_HZ
    x = np.exp(1j * 2.0 * np.pi * TONE_HZ * t)

    y_ideal = x * ideal_nco(SHIFT_HZ)
    y_wrong = x * ideal_nco(-SHIFT_HZ)
    nco_hw = hardware_nco(SHIFT_HZ)
    y_hw = x * nco_hw

    inc = phase_increment(SHIFT_HZ)
    signed_inc = inc - 2**ACC_BITS if inc >= 2 ** (ACC_BITS - 1) else inc
    realized_hz = signed_inc / 2**ACC_BITS * FS_HZ

    metrics = {
        "config": {
            "sample_rate_hz": FS_HZ,
            "samples": N,
            "tone_hz": TONE_HZ,
            "shift_hz": SHIFT_HZ,
            "phase_accumulator_bits": ACC_BITS,
            "lut_address_bits": LUT_ADDR_BITS,
            "lut_amplitude_bits": AMP_BITS,
        },
        "input_peak_hz": peak_hz(x),
        "ideal_output_peak_hz": peak_hz(y_ideal),
        "wrong_sign_output_peak_hz": peak_hz(y_wrong),
        "hardware_output_peak_hz": peak_hz(y_hw),
        "phase_increment": inc,
        "realized_shift_hz": realized_hz,
        "shift_error_hz": realized_hz - SHIFT_HZ,
        "frequency_resolution_hz": FS_HZ / 2**ACC_BITS,
        "hardware_nco_worst_spur_dbc": worst_spur_dbc(nco_hw),
    }
    out = ASSET_DIR / "lab33_digital_mixing_metrics.json"
    out.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    for sig, label in (
        (x, "input"),
        (y_ideal, "after ideal NCO"),
        (y_hw, "after 32-bit / 1024-entry NCO"),
    ):
        f, m = spectrum_db(sig)
        ax.plot(f / 1e3, m, label=label, linewidth=0.8)
    ax.set_ylim(-160, 5)
    ax.set_xlabel("Frequency, kHz")
    ax.set_ylabel("Magnitude, dBFS")
    ax.set_title("Lab 3.3 — Shifting a +420 kHz tone to DC")
    ax.grid(True, alpha=0.35)
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(ASSET_DIR / "lab33_digital_mixing.png", dpi=160)
    plt.close(fig)

    print("Lab 3.3 - Digital mixing and frequency shift")
    print(f"Input peak: {metrics['input_peak_hz']:.1f} Hz")
    print(f"After ideal NCO (-420 kHz): {metrics['ideal_output_peak_hz']:.1f} Hz")
    print(
        f"After wrong-sign NCO (+420 kHz): {metrics['wrong_sign_output_peak_hz']:.1f} Hz"
    )
    print(
        f"32-bit phase increment: {inc} -> realized shift {realized_hz:.6f} Hz "
        f"(error {metrics['shift_error_hz']:.6f} Hz, resolution {metrics['frequency_resolution_hz']:.6f} Hz)"
    )
    print(
        f"After hardware NCO: {metrics['hardware_output_peak_hz']:.1f} Hz, "
        f"worst NCO spur {metrics['hardware_nco_worst_spur_dbc']:.1f} dBc"
    )
    print(f"Metrics JSON: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
