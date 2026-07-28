#!/usr/bin/env python3
"""Lab 8.12 - GFSK BT trade-off, constant envelope, discriminator BER."""

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


@dataclass(frozen=True)
class GfskConfig:
    samples_per_symbol: int = 8
    modulation_index: float = 0.5
    bt_values: tuple[float, ...] = (0.3, 0.5, 1.0)
    filter_span_symbols: int = 4
    bandwidth_bits: int = 8000
    ber_bits_per_point: int = 40_000
    ebn0_db_values: tuple[float, ...] = (0.0, 8.0, 16.0, 24.0, 32.0, 40.0)
    seed: int = 812


def gaussian_taps(bt: float, sps: int, span_symbols: int) -> np.ndarray:
    t = np.arange(-span_symbols * sps, span_symbols * sps + 1) / sps
    alpha = np.sqrt(2.0 * np.pi) * bt / np.sqrt(np.log(2.0))
    taps = np.exp(-0.5 * (alpha * t) ** 2)
    return taps / np.sum(taps)


def gfsk_modulate(bits: np.ndarray, cfg: GfskConfig, bt: float) -> np.ndarray:
    symbols = 2.0 * np.asarray(bits, dtype=np.float64) - 1.0
    nrz = np.repeat(symbols, cfg.samples_per_symbol)
    shaped = np.convolve(
        nrz,
        gaussian_taps(bt, cfg.samples_per_symbol, cfg.filter_span_symbols),
        mode="same",
    )
    phase_step = (
        np.pi * cfg.modulation_index * shaped / cfg.samples_per_symbol
    )
    return np.exp(1j * np.cumsum(phase_step))


def discriminator_demodulate(rx: np.ndarray, cfg: GfskConfig) -> np.ndarray:
    phase_difference = np.angle(rx[1:] * np.conj(rx[:-1]))
    padded = np.concatenate(([phase_difference[0]], phase_difference))
    metrics = padded.reshape(-1, cfg.samples_per_symbol).sum(axis=1)
    return (metrics >= 0.0).astype(np.uint8)


def add_awgn(
    waveform: np.ndarray,
    ebn0_db: float,
    cfg: GfskConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    ebn0 = 10.0 ** (ebn0_db / 10.0)
    noise_variance = cfg.samples_per_symbol / ebn0
    noise = np.sqrt(noise_variance / 2.0) * (
        rng.standard_normal(waveform.size)
        + 1j * rng.standard_normal(waveform.size)
    )
    return waveform + noise


def occupied_bandwidth_fraction(
    waveform: np.ndarray, fraction: float = 0.99
) -> float:
    nfft = 1 << int(np.ceil(np.log2(waveform.size)))
    power = np.abs(np.fft.fftshift(np.fft.fft(waveform, nfft))) ** 2
    frequencies = np.fft.fftshift(np.fft.fftfreq(nfft, d=1.0))
    order = np.argsort(np.abs(frequencies))
    cumulative = np.cumsum(power[order])
    index = int(np.searchsorted(cumulative, fraction * cumulative[-1]))
    return float(2.0 * abs(frequencies[order[index]]))


def bt_sweep(
    cfg: GfskConfig, rng: np.random.Generator
) -> list[dict[str, float]]:
    bits = rng.integers(0, 2, cfg.bandwidth_bits, dtype=np.uint8)
    results: list[dict[str, float]] = []
    for bt in cfg.bt_values:
        waveform = gfsk_modulate(bits, cfg, bt)
        envelope_error = float(np.max(np.abs(np.abs(waveform) - 1.0)))
        papr = float(
            10.0
            * np.log10(
                np.max(np.abs(waveform) ** 2)
                / np.mean(np.abs(waveform) ** 2)
            )
        )
        results.append(
            {
                "bt": float(bt),
                "occupied_bandwidth_99_normalized": occupied_bandwidth_fraction(
                    waveform
                ),
                "constant_envelope_error": envelope_error,
                "papr_db": papr,
            }
        )
    return results


def ber_sweep(
    cfg: GfskConfig, rng: np.random.Generator
) -> list[dict[str, float | int]]:
    results: list[dict[str, float | int]] = []
    for ebn0_db in cfg.ebn0_db_values:
        bits = rng.integers(
            0, 2, cfg.ber_bits_per_point, dtype=np.uint8
        )
        tx = gfsk_modulate(bits, cfg, bt=0.5)
        rx = add_awgn(tx, ebn0_db, cfg, rng)
        recovered = discriminator_demodulate(rx, cfg)
        guard = cfg.filter_span_symbols
        compared_tx = bits[guard:-guard]
        compared_rx = recovered[guard:-guard]
        errors = int(np.count_nonzero(compared_tx != compared_rx))
        results.append(
            {
                "ebn0_db": float(ebn0_db),
                "compared_bits": int(compared_tx.size),
                "bit_errors": errors,
                "ber": float(errors / compared_tx.size),
            }
        )
    return results


def main() -> None:
    cfg = GfskConfig()
    rng = np.random.default_rng(cfg.seed)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    bt_results = bt_sweep(cfg, rng)
    ber_results = ber_sweep(cfg, rng)

    preview_bits = rng.integers(0, 2, 80, dtype=np.uint8)
    plt.figure(figsize=(7.8, 4.4))
    for bt in cfg.bt_values:
        taps = gaussian_taps(
            bt, cfg.samples_per_symbol, cfg.filter_span_symbols
        )
        nrz = np.repeat(
            2.0 * preview_bits.astype(np.float64) - 1.0,
            cfg.samples_per_symbol,
        )
        shaped = np.convolve(nrz, taps, mode="same")
        plt.plot(
            np.arange(160) / cfg.samples_per_symbol,
            shaped[:160],
            label=f"BT={bt}",
        )
    plt.grid(True, alpha=0.35)
    plt.xlabel("Time, symbols")
    plt.ylabel("Gaussian-shaped NRZ")
    plt.title("Lab 8.12 - GFSK BT pulse-shaping trade-off")
    plt.legend()
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab812_gfsk_bt_waveforms.png", dpi=180)
    plt.close()

    plt.figure(figsize=(7.8, 4.4))
    plt.plot(
        [item["bt"] for item in bt_results],
        [item["occupied_bandwidth_99_normalized"] for item in bt_results],
        marker="o",
    )
    plt.grid(True, alpha=0.35)
    plt.xlabel("Gaussian filter BT")
    plt.ylabel("99% occupied bandwidth / sample rate")
    plt.title("Lab 8.12 - GFSK occupied bandwidth")
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab812_gfsk_bandwidth.png", dpi=180)
    plt.close()

    plt.figure(figsize=(7.8, 4.4))
    plt.semilogy(
        [item["ebn0_db"] for item in ber_results],
        [
            max(float(item["ber"]), 0.5 / int(item["compared_bits"]))
            for item in ber_results
        ],
        marker="o",
    )
    plt.grid(True, which="both", alpha=0.35)
    plt.xlabel("Eb/N0, dB")
    plt.ylabel("Bit error rate")
    plt.title("Lab 8.12 - GFSK discriminator receiver, BT=0.5")
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab812_gfsk_ber.png", dpi=180)
    plt.close()

    payload = {
        "config": asdict(cfg),
        "metrics": {
            "compared_bits_per_point": ber_results[0]["compared_bits"],
            "ber_at_lowest_ebn0": ber_results[0]["ber"],
            "ber_at_highest_ebn0": ber_results[-1]["ber"],
            "maximum_constant_envelope_error": max(
                item["constant_envelope_error"] for item in bt_results
            ),
            "maximum_papr_db": max(item["papr_db"] for item in bt_results),
            "narrowest_bt": min(
                bt_results,
                key=lambda item: item["occupied_bandwidth_99_normalized"],
            )["bt"],
            "ofdm_comparison": "GFSK has approximately 0 dB PAPR; OFDM requires peak back-off.",
            "css_comparison": "GFSK trades bandwidth through BT; CSS trades symbol duration for processing gain.",
        },
        "bt_sweep": bt_results,
        "ber_sweep": ber_results,
    }
    (ASSET_DIR / "lab812_gfsk_metrics.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload["metrics"], indent=2))


if __name__ == "__main__":
    main()
