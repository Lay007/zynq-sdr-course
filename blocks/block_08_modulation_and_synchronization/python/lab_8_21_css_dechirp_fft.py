#!/usr/bin/env python3
"""Lab 8.21 - CSS dechirp + FFT detector with SNR and CFO sweeps."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"


@dataclass(frozen=True)
class DetectorConfig:
    spreading_factor: int = 7
    bandwidth_hz: float = 125_000.0
    symbols_per_point: int = 800
    snr_db_values: tuple[float, ...] = (
        -18.0,
        -15.0,
        -12.0,
        -9.0,
        -6.0,
        -3.0,
        0.0,
    )
    cfo_bin_values: tuple[float, ...] = (
        -0.45,
        -0.30,
        -0.15,
        0.0,
        0.15,
        0.30,
        0.45,
    )
    cfo_snr_db: float = -9.0
    seed: int = 821

    @property
    def chips_per_symbol(self) -> int:
        return 1 << self.spreading_factor

    @property
    def symbol_duration_s(self) -> float:
        return self.chips_per_symbol / self.bandwidth_hz


@dataclass(frozen=True)
class DetectorMetrics:
    symbol_count_per_point: int
    ser_at_lowest_snr: float
    ser_at_zero_db: float
    best_cfo_ser: float
    worst_cfo_ser: float
    noiseless_mapping_is_permutation: bool
    example_symbol: int
    example_detected_symbol: int
    example_peak_to_second_db: float


def upchirp(n_chips: int) -> np.ndarray:
    n = np.arange(n_chips, dtype=np.float64)
    phase_cycles = 0.5 * n * n / n_chips - 0.5 * n
    return np.exp(1j * 2.0 * np.pi * phase_cycles)


def symbol_bank(n_chips: int) -> np.ndarray:
    base = upchirp(n_chips)
    return np.asarray([np.roll(base, -m) for m in range(n_chips)])


def detector_mapping(
    bank: np.ndarray, reference: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    spectra = np.fft.fft(bank * np.conj(reference)[None, :], axis=1)
    peak_bins = np.argmax(np.abs(spectra), axis=1)
    inverse = np.empty(len(peak_bins), dtype=np.int64)
    inverse[peak_bins] = np.arange(len(peak_bins), dtype=np.int64)
    return peak_bins, inverse


def add_awgn(
    x: np.ndarray, snr_db: float, rng: np.random.Generator
) -> np.ndarray:
    signal_power = np.mean(np.abs(x) ** 2, axis=1, keepdims=True)
    noise_power = signal_power / (10.0 ** (snr_db / 10.0))
    noise = np.sqrt(noise_power / 2.0) * (
        rng.standard_normal(x.shape) + 1j * rng.standard_normal(x.shape)
    )
    return x + noise


def detect_symbols(
    rx: np.ndarray, reference: np.ndarray, inverse_mapping: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    spectra = np.fft.fft(rx * np.conj(reference)[None, :], axis=1)
    peak_bins = np.argmax(np.abs(spectra), axis=1)
    return inverse_mapping[peak_bins], spectra


def ser_sweep(
    cfg: DetectorConfig,
    bank: np.ndarray,
    reference: np.ndarray,
    inverse_mapping: np.ndarray,
    rng: np.random.Generator,
) -> list[dict[str, float]]:
    results = []
    for snr_db in cfg.snr_db_values:
        tx = rng.integers(
            0, cfg.chips_per_symbol, size=cfg.symbols_per_point
        )
        rx = add_awgn(bank[tx], snr_db, rng)
        detected, _ = detect_symbols(rx, reference, inverse_mapping)
        results.append(
            {"snr_db": float(snr_db), "ser": float(np.mean(detected != tx))}
        )
    return results


def cfo_sweep(
    cfg: DetectorConfig,
    bank: np.ndarray,
    reference: np.ndarray,
    inverse_mapping: np.ndarray,
    rng: np.random.Generator,
) -> list[dict[str, float]]:
    n = np.arange(cfg.chips_per_symbol, dtype=np.float64)
    results = []
    for cfo_bins in cfg.cfo_bin_values:
        tx = rng.integers(
            0, cfg.chips_per_symbol, size=cfg.symbols_per_point
        )
        rotation = np.exp(
            1j * 2.0 * np.pi * cfo_bins * n / cfg.chips_per_symbol
        )
        impaired = bank[tx] * rotation[None, :]
        rx = add_awgn(impaired, cfg.cfo_snr_db, rng)
        detected, _ = detect_symbols(rx, reference, inverse_mapping)
        results.append(
            {"cfo_bins": float(cfo_bins), "ser": float(np.mean(detected != tx))}
        )
    return results


def peak_to_second_db(spectrum: np.ndarray) -> float:
    power = np.abs(spectrum) ** 2
    largest = np.partition(power, -2)[-2:]
    return float(
        10.0
        * np.log10(max(largest[-1], 1e-15) / max(largest[-2], 1e-15))
    )


def main() -> None:
    cfg = DetectorConfig()
    rng = np.random.default_rng(cfg.seed)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    reference = upchirp(cfg.chips_per_symbol)
    bank = symbol_bank(cfg.chips_per_symbol)
    peak_bins, inverse_mapping = detector_mapping(bank, reference)
    mapping_is_permutation = len(np.unique(peak_bins)) == cfg.chips_per_symbol
    if not mapping_is_permutation:
        raise RuntimeError("Noiseless CSS symbol-to-bin mapping is not one-to-one")

    snr_results = ser_sweep(cfg, bank, reference, inverse_mapping, rng)
    cfo_results = cfo_sweep(cfg, bank, reference, inverse_mapping, rng)

    example_symbol = 37
    example_rx = add_awgn(bank[[example_symbol]], -6.0, rng)
    example_detected, example_spectra = detect_symbols(
        example_rx, reference, inverse_mapping
    )
    example_spectrum = example_spectra[0]

    metrics = DetectorMetrics(
        symbol_count_per_point=cfg.symbols_per_point,
        ser_at_lowest_snr=snr_results[0]["ser"],
        ser_at_zero_db=snr_results[-1]["ser"],
        best_cfo_ser=min(item["ser"] for item in cfo_results),
        worst_cfo_ser=max(item["ser"] for item in cfo_results),
        noiseless_mapping_is_permutation=mapping_is_permutation,
        example_symbol=example_symbol,
        example_detected_symbol=int(example_detected[0]),
        example_peak_to_second_db=peak_to_second_db(example_spectrum),
    )

    plt.figure(figsize=(7.8, 4.4))
    plt.semilogy(
        [item["snr_db"] for item in snr_results],
        [
            max(item["ser"], 1.0 / (10.0 * cfg.symbols_per_point))
            for item in snr_results
        ],
        marker="o",
    )
    plt.grid(True, which="both", alpha=0.35)
    plt.xlabel("SNR, dB")
    plt.ylabel("Symbol error rate")
    plt.title(
        f"Lab 8.21 - CSS dechirp + FFT detector, SF={cfg.spreading_factor}"
    )
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab821_css_ser_vs_snr.png", dpi=180)
    plt.close()

    plt.figure(figsize=(7.8, 4.4))
    plt.plot(
        [item["cfo_bins"] for item in cfo_results],
        [item["ser"] for item in cfo_results],
        marker="o",
    )
    plt.grid(True, alpha=0.35)
    plt.xlabel("CFO, FFT-bin spacing")
    plt.ylabel("Symbol error rate")
    plt.title(
        f"Lab 8.21 - CSS CFO sensitivity at SNR={cfg.cfo_snr_db:.0f} dB"
    )
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab821_css_ser_vs_cfo.png", dpi=180)
    plt.close()

    plt.figure(figsize=(7.8, 4.4))
    plt.plot(
        np.arange(cfg.chips_per_symbol),
        20.0 * np.log10(np.maximum(np.abs(example_spectrum), 1e-12)),
    )
    plt.grid(True, alpha=0.35)
    plt.xlabel("FFT bin")
    plt.ylabel("Magnitude, dB")
    plt.title(
        "Lab 8.21 - Example dechirped FFT: "
        f"TX={example_symbol}, RX={int(example_detected[0])}"
    )
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab821_css_example_fft.png", dpi=180)
    plt.close()

    payload = {
        "config": asdict(cfg),
        "metrics": asdict(metrics),
        "symbol_to_peak_bin": peak_bins.tolist(),
        "snr_sweep": snr_results,
        "cfo_sweep": cfo_results,
    }
    (ASSET_DIR / "lab821_css_detector_metrics.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )

    print(json.dumps(asdict(metrics), indent=2))


if __name__ == "__main__":
    main()
