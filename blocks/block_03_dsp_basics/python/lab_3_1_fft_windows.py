#!/usr/bin/env python3
"""Lab 3.1 — FFT windows and spectral leakage.

Deterministic script-driven lab. Two complex tones are analysed with four
windows: one tone sits exactly on an FFT bin (coherent), the other falls
0.35 bin away (non-coherent). A weak tone 12 bins away from the strong one
shows how leakage hides small signals.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"

FS_HZ = 2.4e6
N = 4096
COHERENT_BIN = 250.0
NONCOHERENT_BIN = 250.35
WEAK_OFFSET_BINS = 12
WEAK_RELATIVE_DB = -60.0
LEAKAGE_OFFSET_BINS = 20


@dataclass(frozen=True)
class WindowResult:
    window: str
    coherent_gain: float
    enbw_bins: float
    coherent_peak_db: float
    noncoherent_peak_db: float
    scalloping_loss_db: float
    noncoherent_freq_error_hz: float
    leakage_at_20_bins_dbc: float
    weak_tone_visibility_db: float


def windows(n: int) -> dict[str, np.ndarray]:
    return {
        "rectangular": np.ones(n),
        "hann": np.hanning(n),
        "hamming": np.hamming(n),
        "blackman": np.blackman(n),
    }


def tone(bin_index: float, n: int = N, amplitude: float = 1.0) -> np.ndarray:
    k = np.arange(n)
    return amplitude * np.exp(1j * 2.0 * np.pi * bin_index * k / n)


def spectrum_dbfs(x: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Amplitude spectrum normalised so a full-scale tone on a bin reads 0 dBFS."""
    spec = np.fft.fft(x * w) / np.sum(w)
    return 20.0 * np.log10(np.maximum(np.abs(spec), 1e-15))


def analyse(name: str, w: np.ndarray) -> WindowResult:
    coh = spectrum_dbfs(tone(COHERENT_BIN), w)
    non = spectrum_dbfs(tone(NONCOHERENT_BIN), w)
    peak_bin = int(np.argmax(non))
    freq_error_hz = (peak_bin - NONCOHERENT_BIN) * FS_HZ / N

    leak_bin = int(round(NONCOHERENT_BIN)) + LEAKAGE_OFFSET_BINS
    leakage_dbc = float(non[leak_bin] - non[peak_bin])

    # Weak-tone visibility: the weak tone's own level at its bin compared with the
    # leakage the strong (non-coherent) tone alone puts into that same bin.
    weak_bin = int(COHERENT_BIN) + WEAK_OFFSET_BINS
    weak_only = spectrum_dbfs(
        tone(weak_bin, amplitude=10.0 ** (WEAK_RELATIVE_DB / 20.0)), w
    )
    visibility_db = float(weak_only[weak_bin] - non[weak_bin])

    return WindowResult(
        window=name,
        coherent_gain=float(np.sum(w) / len(w)),
        enbw_bins=float(len(w) * np.sum(w * w) / np.sum(w) ** 2),
        coherent_peak_db=float(np.max(coh)),
        noncoherent_peak_db=float(np.max(non)),
        scalloping_loss_db=float(np.max(coh) - np.max(non)),
        noncoherent_freq_error_hz=float(freq_error_hz),
        leakage_at_20_bins_dbc=leakage_dbc,
        weak_tone_visibility_db=visibility_db,
    )


def save_plot(path: Path) -> None:
    freq_bins = np.arange(N)
    plt.figure(figsize=(7.4, 4.4))
    pair = tone(NONCOHERENT_BIN) + tone(
        COHERENT_BIN + WEAK_OFFSET_BINS, amplitude=10.0 ** (WEAK_RELATIVE_DB / 20.0)
    )
    for name, w in windows(N).items():
        spec = spectrum_dbfs(pair, w)
        sel = (freq_bins > 225) & (freq_bins < 285)
        plt.plot((freq_bins[sel] - COHERENT_BIN), spec[sel], label=name)
    plt.axvline(WEAK_OFFSET_BINS, linestyle=":", color="k", label="weak tone (-60 dBc)")
    plt.ylim(-140, 5)
    plt.grid(True, alpha=0.35)
    plt.xlabel("Offset from bin 250, bins")
    plt.ylabel("Magnitude, dBFS")
    plt.title("Lab 3.1 — Non-coherent tone plus a -60 dBc neighbour")
    plt.legend(loc="upper right", fontsize=8)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def main() -> int:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    results = [analyse(name, w) for name, w in windows(N).items()]
    save_plot(ASSET_DIR / "lab31_fft_windows_leakage.png")
    payload = {
        "config": {
            "sample_rate_hz": FS_HZ,
            "fft_length": N,
            "bin_spacing_hz": FS_HZ / N,
            "coherent_bin": COHERENT_BIN,
            "noncoherent_bin": NONCOHERENT_BIN,
            "weak_offset_bins": WEAK_OFFSET_BINS,
            "weak_relative_db": WEAK_RELATIVE_DB,
        },
        "windows": [asdict(r) for r in results],
    }
    out = ASSET_DIR / "lab31_fft_windows_metrics.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("Lab 3.1 - FFT windows and spectral leakage")
    print(f"Fs = {FS_HZ:.0f} Hz, N = {N}, bin spacing = {FS_HZ / N:.2f} Hz")
    print(
        f"{'window':12s} {'ENBW':>6s} {'scallop':>8s} {'leak@20':>8s} {'weak vis':>9s}"
    )
    for r in results:
        print(
            f"{r.window:12s} {r.enbw_bins:6.2f} {r.scalloping_loss_db:7.2f}dB "
            f"{r.leakage_at_20_bins_dbc:7.1f}dB {r.weak_tone_visibility_db:8.1f}dB"
        )
    print(f"Metrics JSON: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
