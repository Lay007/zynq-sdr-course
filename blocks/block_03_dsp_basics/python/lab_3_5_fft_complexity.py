#!/usr/bin/env python3
"""Lab 3.5 — FFT complexity and selected-bin trade-off.

Deterministic script-driven lab: no notebooks. It compares the theoretical
operation growth of direct DFT, FFT-style full-spectrum analysis and selected-bin
Goertzel-style detection for SDR engineering decisions.
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
class FftComplexityMetrics:
    min_n: int
    max_n: int
    dft_growth_at_max_n: float
    fft_growth_at_max_n: float
    selected_bin_count: int
    selected_bin_growth_at_max_n: float
    dft_to_fft_ratio_at_max_n: float
    fft_to_selected_bin_ratio_at_max_n: float


def normalized_complexities(n: np.ndarray, selected_bins: int = 4) -> dict[str, np.ndarray]:
    dft = n.astype(float) ** 2
    fft = n.astype(float) * np.log2(n)
    selected = selected_bins * n.astype(float)
    return {"dft": dft, "fft": fft, "selected": selected}


def save_complexity_plot(n: np.ndarray, values: dict[str, np.ndarray]) -> None:
    out = ASSET_DIR / "lab35_dft_fft_complexity.png"
    plt.figure(figsize=(7.2, 4.3))
    plt.loglog(n, values["dft"], marker="o", label="Direct DFT ~ N^2")
    plt.loglog(n, values["fft"], marker="s", label="FFT ~ N log2(N)")
    plt.grid(True, which="both", alpha=0.35)
    plt.xlabel("Transform length N")
    plt.ylabel("Relative operation growth")
    plt.title("Lab 3.5 — Direct DFT vs FFT complexity")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(out, dpi=180)
    plt.close()


def save_selected_bin_plot(n: np.ndarray, values: dict[str, np.ndarray]) -> None:
    out = ASSET_DIR / "lab35_selected_bin_tradeoff.png"
    plt.figure(figsize=(7.2, 4.3))
    plt.loglog(n, values["fft"], marker="s", label="Full FFT")
    plt.loglog(n, values["selected"], marker="^", label="4 selected bins")
    plt.grid(True, which="both", alpha=0.35)
    plt.xlabel("Analysis length N")
    plt.ylabel("Relative operation growth")
    plt.title("Lab 3.5 — Full spectrum vs selected-bin detection")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(out, dpi=180)
    plt.close()


def main() -> int:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    n = 2 ** np.arange(5, 17)
    selected_bins = 4
    values = normalized_complexities(n, selected_bins=selected_bins)
    save_complexity_plot(n, values)
    save_selected_bin_plot(n, values)

    metrics = FftComplexityMetrics(
        min_n=int(n[0]),
        max_n=int(n[-1]),
        dft_growth_at_max_n=float(values["dft"][-1]),
        fft_growth_at_max_n=float(values["fft"][-1]),
        selected_bin_count=selected_bins,
        selected_bin_growth_at_max_n=float(values["selected"][-1]),
        dft_to_fft_ratio_at_max_n=float(values["dft"][-1] / values["fft"][-1]),
        fft_to_selected_bin_ratio_at_max_n=float(values["fft"][-1] / values["selected"][-1]),
    )
    out = ASSET_DIR / "lab35_fft_complexity_metrics.json"
    out.write_text(json.dumps(asdict(metrics), indent=2), encoding="utf-8")
    print(f"DFT/FFT ratio at N={metrics.max_n}: {metrics.dft_to_fft_ratio_at_max_n:.1f}")
    print(f"FFT/selected-bin ratio at N={metrics.max_n}: {metrics.fft_to_selected_bin_ratio_at_max_n:.1f}")
    print(f"Metrics JSON: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
