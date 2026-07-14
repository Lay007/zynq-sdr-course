#!/usr/bin/env python3
"""Lab 8.10 - OFDM PAPR, clipping, EVM, BER, and out-of-band energy."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"


@dataclass(frozen=True)
class OfdmPaprConfig:
    fft_size: int = 64
    oversampling: int = 4
    ccdf_symbols: int = 4000
    measurement_symbols: int = 300
    snr_db: float = 24.0
    clipping_ratios: tuple[float, ...] = (
        3.0,
        2.0,
        1.6,
        1.3,
        1.1,
        0.9,
        0.7,
    )
    seed: int = 810


@dataclass(frozen=True)
class OfdmPaprMetrics:
    median_papr_db: float
    papr_99_percent_db: float
    unclipped_evm_percent: float
    strongest_clipping_evm_percent: float
    unclipped_ber: float
    strongest_clipping_ber: float
    strongest_clipping_oob_db: float
    strongest_clipping_papr_db: float
    compared_bits_per_point: int


def qpsk_from_bits(bits: np.ndarray) -> np.ndarray:
    pairs = bits.reshape(-1, 2)
    i = np.where(pairs[:, 0] == 0, 1.0, -1.0)
    q = np.where(pairs[:, 1] == 0, 1.0, -1.0)
    return (i + 1j * q) / np.sqrt(2.0)


def bits_from_qpsk(symbols: np.ndarray) -> np.ndarray:
    bits = np.empty(2 * len(symbols), dtype=np.uint8)
    bits[0::2] = np.where(np.real(symbols) >= 0.0, 0, 1)
    bits[1::2] = np.where(np.imag(symbols) >= 0.0, 0, 1)
    return bits


def occupied_subcarriers() -> np.ndarray:
    return np.concatenate([np.arange(-26, 0), np.arange(1, 27)])


def map_oversampled(symbols: np.ndarray, cfg: OfdmPaprConfig) -> np.ndarray:
    nfft_os = cfg.fft_size * cfg.oversampling
    fd = np.zeros((len(symbols), nfft_os), dtype=np.complex128)
    k = occupied_subcarriers()
    fd[:, np.mod(k, nfft_os)] = symbols
    return np.fft.ifft(fd, axis=1) * np.sqrt(nfft_os)


def papr_db(waveforms: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(waveforms) ** 2, axis=1)
    mean = np.mean(np.abs(waveforms) ** 2, axis=1)
    return 10.0 * np.log10(
        np.maximum(peak / np.maximum(mean, 1e-15), 1e-15)
    )


def clip_magnitude(x: np.ndarray, ratio: float) -> np.ndarray:
    rms = np.sqrt(np.mean(np.abs(x) ** 2, axis=1, keepdims=True))
    threshold = ratio * rms
    magnitude = np.abs(x)
    scale = np.minimum(1.0, threshold / np.maximum(magnitude, 1e-15))
    return x * scale


def add_awgn(
    x: np.ndarray, snr_db: float, rng: np.random.Generator
) -> np.ndarray:
    signal_power = np.mean(np.abs(x) ** 2)
    noise_power = signal_power / (10.0 ** (snr_db / 10.0))
    noise = np.sqrt(noise_power / 2.0) * (
        rng.standard_normal(x.shape) + 1j * rng.standard_normal(x.shape)
    )
    return x + noise


def evaluate_waveform(
    tx_time: np.ndarray,
    tx_symbols: np.ndarray,
    tx_bits: np.ndarray,
    cfg: OfdmPaprConfig,
    rng: np.random.Generator,
) -> dict[str, float]:
    rx_time = add_awgn(tx_time, cfg.snr_db, rng)
    fd = np.fft.fft(rx_time / np.sqrt(tx_time.shape[1]), axis=1)
    k = occupied_subcarriers()
    rx_symbols = fd[:, np.mod(k, tx_time.shape[1])]

    ref = tx_symbols.reshape(-1)
    rx = rx_symbols.reshape(-1)
    gain = np.vdot(ref, rx) / max(np.vdot(ref, ref), 1e-15)
    aligned = rx / gain
    error = aligned - ref
    evm_rms = np.sqrt(np.mean(np.abs(error) ** 2))
    evm_percent = 100.0 * evm_rms

    rx_bits = bits_from_qpsk(aligned)
    bit_errors = int(np.sum(rx_bits != tx_bits))
    ber = bit_errors / len(tx_bits)

    spectrum_power = np.mean(np.abs(fd) ** 2, axis=0)
    occupied_mask = np.zeros(tx_time.shape[1], dtype=bool)
    occupied_mask[np.mod(k, tx_time.shape[1])] = True
    inband = float(np.sum(spectrum_power[occupied_mask]))
    outband = float(np.sum(spectrum_power[~occupied_mask]))
    oob_db = 10.0 * np.log10(
        max(outband, 1e-15) / max(inband, 1e-15)
    )

    return {
        "papr_db": float(np.mean(papr_db(tx_time))),
        "evm_percent": float(evm_percent),
        "ber": float(ber),
        "bit_errors": bit_errors,
        "compared_bits": int(len(tx_bits)),
        "out_of_band_to_in_band_db": float(oob_db),
    }


def main() -> None:
    cfg = OfdmPaprConfig()
    rng = np.random.default_rng(cfg.seed)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    n_used = len(occupied_subcarriers())
    ccdf_bits = rng.integers(
        0,
        2,
        size=cfg.ccdf_symbols * n_used * 2,
        dtype=np.uint8,
    )
    ccdf_symbols = qpsk_from_bits(ccdf_bits).reshape(
        cfg.ccdf_symbols, n_used
    )
    ccdf_waveforms = map_oversampled(ccdf_symbols, cfg)
    papr_values = papr_db(ccdf_waveforms)

    measurement_bits = rng.integers(
        0,
        2,
        size=cfg.measurement_symbols * n_used * 2,
        dtype=np.uint8,
    )
    measurement_symbols = qpsk_from_bits(measurement_bits).reshape(
        cfg.measurement_symbols, n_used
    )
    base_waveforms = map_oversampled(measurement_symbols, cfg)

    sweep = [
        {
            "clipping_ratio": None,
            **evaluate_waveform(
                base_waveforms,
                measurement_symbols,
                measurement_bits,
                cfg,
                np.random.default_rng(cfg.seed + 1),
            ),
        }
    ]
    for index, ratio in enumerate(cfg.clipping_ratios):
        clipped = clip_magnitude(base_waveforms, ratio)
        sweep.append(
            {
                "clipping_ratio": float(ratio),
                **evaluate_waveform(
                    clipped,
                    measurement_symbols,
                    measurement_bits,
                    cfg,
                    np.random.default_rng(cfg.seed + 10 + index),
                ),
            }
        )

    unclipped = sweep[0]
    strongest = sweep[-1]
    metrics = OfdmPaprMetrics(
        median_papr_db=float(np.median(papr_values)),
        papr_99_percent_db=float(np.quantile(papr_values, 0.99)),
        unclipped_evm_percent=unclipped["evm_percent"],
        strongest_clipping_evm_percent=strongest["evm_percent"],
        unclipped_ber=unclipped["ber"],
        strongest_clipping_ber=strongest["ber"],
        strongest_clipping_oob_db=strongest[
            "out_of_band_to_in_band_db"
        ],
        strongest_clipping_papr_db=strongest["papr_db"],
        compared_bits_per_point=unclipped["compared_bits"],
    )

    thresholds = np.linspace(3.0, 13.0, 81)
    ccdf = np.array(
        [np.mean(papr_values > threshold) for threshold in thresholds]
    )
    plt.figure(figsize=(7.8, 4.4))
    plt.semilogy(
        thresholds,
        np.maximum(ccdf, 1.0 / cfg.ccdf_symbols),
    )
    plt.grid(True, which="both", alpha=0.35)
    plt.xlabel("PAPR threshold, dB")
    plt.ylabel("Pr(PAPR > threshold)")
    plt.title("Lab 8.10 - OFDM PAPR CCDF")
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab810_ofdm_papr_ccdf.png", dpi=180)
    plt.close()

    labels = ["none"] + [f"{ratio:.1f}" for ratio in cfg.clipping_ratios]
    evm = [item["evm_percent"] for item in sweep]
    papr = [item["papr_db"] for item in sweep]
    x = np.arange(len(labels))
    plt.figure(figsize=(7.8, 4.4))
    plt.plot(x, evm, marker="o", label="EVM, %")
    plt.plot(x, papr, marker="s", label="mean PAPR, dB")
    plt.xticks(x, labels)
    plt.grid(True, alpha=0.35)
    plt.xlabel("Clipping ratio A/RMS")
    plt.ylabel("Metric value")
    plt.title("Lab 8.10 - OFDM clipping trade-off")
    plt.legend()
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab810_ofdm_clipping_tradeoff.png", dpi=180)
    plt.close()

    plt.figure(figsize=(7.8, 4.4))
    plt.plot(
        x,
        [item["out_of_band_to_in_band_db"] for item in sweep],
        marker="o",
    )
    plt.xticks(x, labels)
    plt.grid(True, alpha=0.35)
    plt.xlabel("Clipping ratio A/RMS")
    plt.ylabel("Out-of-band / in-band power, dB")
    plt.title("Lab 8.10 - Spectral regrowth from clipping")
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab810_ofdm_spectral_regrowth.png", dpi=180)
    plt.close()

    payload = {
        "config": asdict(cfg),
        "metrics": asdict(metrics),
        "clipping_sweep": sweep,
    }
    (ASSET_DIR / "lab810_ofdm_papr_metrics.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    print(json.dumps(asdict(metrics), indent=2))


if __name__ == "__main__":
    main()
