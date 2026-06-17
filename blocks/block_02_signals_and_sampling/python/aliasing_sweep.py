#!/usr/bin/env python3
"""Lab 2.2 - Aliasing sweep and example spectra."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from block2_signal_utils import alias_frequency_hz, estimate_positive_peak_hz, make_real_tone, spectrum_db


ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"


@dataclass(frozen=True)
class AliasingConfig:
    sample_rate_hz: float = 1_000_000.0
    sample_count: int = 16384
    example_tones_hz: tuple[float, float, float] = (180_000.0, 620_000.0, 1_180_000.0)
    amplitude: float = 0.85


@dataclass(frozen=True)
class AliasingCase:
    input_tone_hz: float
    expected_alias_hz: float
    measured_alias_hz: float
    alias_error_hz: float


@dataclass(frozen=True)
class AliasingMetrics:
    sample_rate_hz: float
    nyquist_hz: float
    max_alias_error_hz: float
    cases: list[AliasingCase]


def save_alias_map(path: Path, cfg: AliasingConfig) -> None:
    tones = np.linspace(0.0, 2.5 * cfg.sample_rate_hz, 801)
    aliased = np.abs([alias_frequency_hz(tone, cfg.sample_rate_hz) for tone in tones])
    plt.figure(figsize=(7.4, 4.4))
    plt.plot(tones / 1e3, aliased / 1e3)
    plt.axhline(0.5 * cfg.sample_rate_hz / 1e3, linestyle="--", label="Nyquist")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Input tone, kHz")
    plt.ylabel("Observed alias magnitude, kHz")
    plt.title("Lab 2.2 - Aliasing map for real-valued sampling")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def save_example_spectra(path: Path, cfg: AliasingConfig) -> list[AliasingCase]:
    plt.figure(figsize=(7.4, 4.4))
    cases: list[AliasingCase] = []
    for tone_hz in cfg.example_tones_hz:
        x = make_real_tone(cfg.sample_rate_hz, cfg.sample_count, tone_hz, amplitude=cfg.amplitude).astype(np.complex128)
        freq, mag_db = spectrum_db(x, cfg.sample_rate_hz)
        positive = freq >= 0.0
        plt.plot(freq[positive] / 1e3, mag_db[positive], label=f"{tone_hz/1e3:.0f} kHz input")
        expected_alias = abs(alias_frequency_hz(tone_hz, cfg.sample_rate_hz))
        measured_alias = estimate_positive_peak_hz(x, cfg.sample_rate_hz)
        cases.append(
            AliasingCase(
                input_tone_hz=tone_hz,
                expected_alias_hz=expected_alias,
                measured_alias_hz=measured_alias,
                alias_error_hz=measured_alias - expected_alias,
            )
        )
    plt.grid(True, alpha=0.35)
    plt.xlabel("Observed frequency, kHz")
    plt.ylabel("Magnitude, dBFS")
    plt.title("Lab 2.2 - Example spectra before and after aliasing")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()
    return cases


def main() -> int:
    cfg = AliasingConfig()
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    save_alias_map(ASSET_DIR / "lab22_aliasing_map.png", cfg)
    cases = save_example_spectra(ASSET_DIR / "lab22_aliasing_examples.png", cfg)
    metrics = AliasingMetrics(
        sample_rate_hz=cfg.sample_rate_hz,
        nyquist_hz=0.5 * cfg.sample_rate_hz,
        max_alias_error_hz=max(abs(case.alias_error_hz) for case in cases),
        cases=cases,
    )
    metrics_path = ASSET_DIR / "lab22_aliasing_metrics.json"
    metrics_path.write_text(json.dumps({"config": asdict(cfg), "metrics": asdict(metrics)}, indent=2), encoding="utf-8")

    print("Lab 2.2 - Aliasing sweep and example spectra")
    for case in cases:
        print(
            f"Input {case.input_tone_hz:.0f} Hz -> expected alias {case.expected_alias_hz:.3f} Hz, "
            f"measured {case.measured_alias_hz:.3f} Hz"
        )
    print(f"Metrics JSON: {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
