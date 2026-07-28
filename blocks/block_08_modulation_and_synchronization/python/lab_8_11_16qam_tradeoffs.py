#!/usr/bin/env python3
"""Lab 8.11 - Gray 16-QAM BER/EVM, impairments, fixed-point, and OFDM bridge."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"
GRAY_LEVELS = np.array([-3.0, -1.0, 3.0, 1.0])
NORMALIZATION = np.sqrt(10.0)


@dataclass(frozen=True)
class QamConfig:
    symbols_per_point: int = 50_000
    ebn0_db_values: tuple[float, ...] = (0.0, 4.0, 8.0, 12.0, 16.0)
    imbalance_gain_db: tuple[float, ...] = (-2.0, -1.0, 0.0, 1.0, 2.0)
    imbalance_phase_deg: tuple[float, ...] = (0.0, 2.0, 5.0, 8.0, 12.0)
    fixed_total_bits: tuple[int, ...] = (4, 6, 8, 10)
    ofdm_symbols: int = 1000
    seed: int = 811


def map_16qam(bits: np.ndarray) -> np.ndarray:
    bits = np.asarray(bits, dtype=np.uint8).reshape(-1, 4)
    i_index = bits[:, 0] * 2 + bits[:, 1]
    q_index = bits[:, 2] * 2 + bits[:, 3]
    return (GRAY_LEVELS[i_index] + 1j * GRAY_LEVELS[q_index]) / NORMALIZATION


def demap_axis(values: np.ndarray) -> np.ndarray:
    levels = np.where(
        values < -2.0 / NORMALIZATION,
        0,
        np.where(values < 0.0, 1, np.where(values < 2.0 / NORMALIZATION, 3, 2)),
    )
    return np.column_stack(((levels >> 1) & 1, levels & 1)).astype(np.uint8)


def demap_16qam(symbols: np.ndarray) -> np.ndarray:
    i_bits = demap_axis(np.real(symbols))
    q_bits = demap_axis(np.imag(symbols))
    return np.column_stack((i_bits, q_bits)).reshape(-1)


def add_awgn(
    symbols: np.ndarray, ebn0_db: float, rng: np.random.Generator
) -> np.ndarray:
    esn0 = 10.0 ** ((ebn0_db + 10.0 * np.log10(4.0)) / 10.0)
    noise_sigma = np.sqrt(1.0 / (2.0 * esn0))
    noise = noise_sigma * (
        rng.standard_normal(symbols.size) + 1j * rng.standard_normal(symbols.size)
    )
    return symbols + noise


def evm_percent(reference: np.ndarray, measured: np.ndarray) -> float:
    return float(
        100.0
        * np.sqrt(
            np.mean(np.abs(measured - reference) ** 2)
            / np.mean(np.abs(reference) ** 2)
        )
    )


def ber_evm_sweep(
    cfg: QamConfig, rng: np.random.Generator
) -> list[dict[str, float | int]]:
    results: list[dict[str, float | int]] = []
    for ebn0_db in cfg.ebn0_db_values:
        bits = rng.integers(0, 2, cfg.symbols_per_point * 4, dtype=np.uint8)
        tx = map_16qam(bits)
        rx = add_awgn(tx, ebn0_db, rng)
        recovered = demap_16qam(rx)
        errors = int(np.count_nonzero(recovered != bits))
        results.append(
            {
                "ebn0_db": float(ebn0_db),
                "compared_bits": int(bits.size),
                "bit_errors": errors,
                "ber": float(errors / bits.size),
                "evm_percent": evm_percent(tx, rx),
            }
        )
    return results


def apply_iq_imbalance(
    symbols: np.ndarray, gain_db: float, phase_deg: float
) -> np.ndarray:
    gain = 10.0 ** (gain_db / 20.0)
    phase = np.deg2rad(phase_deg)
    i = np.real(symbols) * gain
    q = np.imag(symbols) / gain
    return i + q * np.exp(1j * (np.pi / 2.0 + phase))


def imbalance_sweep(
    cfg: QamConfig, rng: np.random.Generator
) -> list[dict[str, float | int]]:
    bits = rng.integers(0, 2, cfg.symbols_per_point * 4, dtype=np.uint8)
    tx = map_16qam(bits)
    results: list[dict[str, float | int]] = []
    for gain_db, phase_deg in zip(
        cfg.imbalance_gain_db, cfg.imbalance_phase_deg, strict=True
    ):
        rx = apply_iq_imbalance(tx, gain_db, phase_deg)
        recovered = demap_16qam(rx)
        errors = int(np.count_nonzero(recovered != bits))
        results.append(
            {
                "gain_imbalance_db": float(gain_db),
                "phase_imbalance_deg": float(phase_deg),
                "bit_errors": errors,
                "ber": float(errors / bits.size),
                "evm_percent": evm_percent(tx, rx),
            }
        )
    return results


def quantize_signed(x: np.ndarray, total_bits: int) -> tuple[np.ndarray, int]:
    fractional_bits = total_bits - 2
    scale = 1 << fractional_bits
    minimum = -1.0
    maximum = (scale - 1) / scale
    clipping = int(np.count_nonzero((x < minimum) | (x > maximum)))
    quantized = np.clip(np.round(x * scale) / scale, minimum, maximum)
    return quantized, clipping


def fixed_point_sweep(
    cfg: QamConfig, rng: np.random.Generator
) -> list[dict[str, float | int]]:
    bits = rng.integers(0, 2, cfg.symbols_per_point * 4, dtype=np.uint8)
    tx = map_16qam(bits)
    driven = tx * 1.15
    results: list[dict[str, float | int]] = []
    for total_bits in cfg.fixed_total_bits:
        qi, clip_i = quantize_signed(np.real(driven), total_bits)
        qq, clip_q = quantize_signed(np.imag(driven), total_bits)
        quantized = qi + 1j * qq
        recovered = demap_16qam(quantized / 1.15)
        errors = int(np.count_nonzero(recovered != bits))
        results.append(
            {
                "total_bits": total_bits,
                "fractional_bits": total_bits - 2,
                "saturation_count": clip_i + clip_q,
                "ber": float(errors / bits.size),
                "evm_percent": evm_percent(driven, quantized),
            }
        )
    return results


def papr_db(waveforms: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(waveforms) ** 2, axis=1)
    average = np.mean(np.abs(waveforms) ** 2, axis=1)
    return 10.0 * np.log10(peak / average)


def ofdm_comparison(
    cfg: QamConfig, rng: np.random.Generator
) -> dict[str, float | int]:
    carriers = 52
    qpsk_bits = rng.integers(0, 2, (cfg.ofdm_symbols, carriers, 2))
    qpsk = (
        (1.0 - 2.0 * qpsk_bits[:, :, 0])
        + 1j * (1.0 - 2.0 * qpsk_bits[:, :, 1])
    ) / np.sqrt(2.0)
    qam_bits = rng.integers(0, 2, (cfg.ofdm_symbols, carriers, 4), dtype=np.uint8)
    qam = map_16qam(qam_bits.reshape(-1, 4)).reshape(cfg.ofdm_symbols, carriers)

    def waveform(data: np.ndarray) -> np.ndarray:
        grid = np.zeros((cfg.ofdm_symbols, 64), dtype=np.complex128)
        grid[:, 1:27] = data[:, :26]
        grid[:, -26:] = data[:, 26:]
        return np.fft.ifft(grid, axis=1) * np.sqrt(64.0)

    qpsk_papr = papr_db(waveform(qpsk))
    qam_papr = papr_db(waveform(qam))
    return {
        "active_subcarriers": carriers,
        "qpsk_bits_per_ofdm_symbol": carriers * 2,
        "qam16_bits_per_ofdm_symbol": carriers * 4,
        "spectral_efficiency_ratio": 2.0,
        "qpsk_median_papr_db": float(np.median(qpsk_papr)),
        "qam16_median_papr_db": float(np.median(qam_papr)),
        "qpsk_papr_99_db": float(np.percentile(qpsk_papr, 99.0)),
        "qam16_papr_99_db": float(np.percentile(qam_papr, 99.0)),
    }


def main() -> None:
    cfg = QamConfig()
    rng = np.random.default_rng(cfg.seed)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    ber_results = ber_evm_sweep(cfg, rng)
    imbalance_results = imbalance_sweep(cfg, rng)
    fixed_results = fixed_point_sweep(cfg, rng)
    ofdm = ofdm_comparison(cfg, rng)

    plt.figure(figsize=(7.8, 4.4))
    plt.semilogy(
        [item["ebn0_db"] for item in ber_results],
        [max(float(item["ber"]), 0.5 / int(item["compared_bits"])) for item in ber_results],
        marker="o",
    )
    plt.grid(True, which="both", alpha=0.35)
    plt.xlabel("Eb/N0, dB")
    plt.ylabel("Bit error rate")
    plt.title("Lab 8.11 - Gray 16-QAM BER")
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab811_16qam_ber.png", dpi=180)
    plt.close()

    plt.figure(figsize=(7.8, 4.4))
    plt.plot(
        [item["phase_imbalance_deg"] for item in imbalance_results],
        [item["evm_percent"] for item in imbalance_results],
        marker="o",
        label="IQ imbalance EVM",
    )
    plt.grid(True, alpha=0.35)
    plt.xlabel("Quadrature phase error, degrees")
    plt.ylabel("EVM, %")
    plt.title("Lab 8.11 - 16-QAM gain/phase imbalance sensitivity")
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab811_16qam_imbalance.png", dpi=180)
    plt.close()

    plt.figure(figsize=(7.8, 4.4))
    plt.plot(
        [item["total_bits"] for item in fixed_results],
        [item["evm_percent"] for item in fixed_results],
        marker="o",
        label="quantization EVM",
    )
    plt.grid(True, alpha=0.35)
    plt.xlabel("Signed fixed-point total bits")
    plt.ylabel("EVM, %")
    plt.title("Lab 8.11 - 16-QAM fixed-point quantization")
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab811_16qam_fixed_point.png", dpi=180)
    plt.close()

    payload = {
        "config": asdict(cfg),
        "metrics": {
            "normalization_rms": float(
                np.sqrt(np.mean(np.abs(map_16qam(
                    np.unpackbits(np.arange(16, dtype=np.uint8)[:, None], axis=1)[
                        :, -4:
                    ].reshape(-1)
                )) ** 2))
            ),
            "decision_thresholds_normalized": [
                -2.0 / NORMALIZATION,
                0.0,
                2.0 / NORMALIZATION,
            ],
            "compared_bits_per_ber_point": cfg.symbols_per_point * 4,
            "ber_at_highest_ebn0": ber_results[-1]["ber"],
            "worst_imbalance_evm_percent": max(
                float(item["evm_percent"]) for item in imbalance_results
            ),
            "minimum_fixed_point_evm_percent": min(
                float(item["evm_percent"]) for item in fixed_results
            ),
        },
        "ber_evm_sweep": ber_results,
        "imbalance_sweep": imbalance_results,
        "fixed_point_sweep": fixed_results,
        "ofdm_payload_comparison": ofdm,
    }
    (ASSET_DIR / "lab811_16qam_metrics.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload["metrics"], indent=2))


if __name__ == "__main__":
    main()
