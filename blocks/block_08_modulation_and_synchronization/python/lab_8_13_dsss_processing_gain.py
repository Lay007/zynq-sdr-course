#!/usr/bin/env python3
"""Lab 8.13 - DSSS PN spreading, acquisition, and processing gain."""

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
class DsssConfig:
    lfsr_order: int = 7
    bits_per_point: int = 20_000
    ebn0_db_values: tuple[float, ...] = (-6.0, -3.0, 0.0, 3.0, 6.0, 9.0)
    interferer_js_db: float = 10.0
    interferer_frequency_cycles_per_chip: float = 0.073
    acquisition_prefix_chips: int = 73
    acquisition_snr_db: float = -8.0
    seed: int = 813

    @property
    def code_length(self) -> int:
        return (1 << self.lfsr_order) - 1


def m_sequence(order: int = 7) -> np.ndarray:
    if order != 7:
        raise ValueError("This lab uses the primitive x^7 + x^3 + 1 sequence")
    register = np.ones(order, dtype=np.uint8)
    sequence = np.empty((1 << order) - 1, dtype=np.uint8)
    for index in range(sequence.size):
        sequence[index] = register[-1]
        feedback = register[-1] ^ register[-5]
        register[1:] = register[:-1]
        register[0] = feedback
    return 2.0 * sequence.astype(np.float64) - 1.0


def spread(bits: np.ndarray, code: np.ndarray) -> np.ndarray:
    symbols = 2.0 * np.asarray(bits, dtype=np.float64) - 1.0
    return (symbols[:, None] * code[None, :]).reshape(-1)


def despread(chips: np.ndarray, code: np.ndarray) -> np.ndarray:
    blocks = chips.reshape(-1, code.size)
    metrics = np.real(np.sum(blocks * code[None, :], axis=1))
    return (metrics >= 0.0).astype(np.uint8)


def add_channel(
    chips: np.ndarray,
    ebn0_db: float,
    code_length: int,
    cfg: DsssConfig,
    rng: np.random.Generator,
    *,
    interference: bool,
) -> np.ndarray:
    ebn0 = 10.0 ** (ebn0_db / 10.0)
    noise_variance = code_length / ebn0
    noise = np.sqrt(noise_variance / 2.0) * (
        rng.standard_normal(chips.size) + 1j * rng.standard_normal(chips.size)
    )
    rx = chips.astype(np.complex128) + noise
    if interference:
        amplitude = 10.0 ** (cfg.interferer_js_db / 20.0)
        n = np.arange(chips.size)
        phase = rng.uniform(0.0, 2.0 * np.pi)
        rx += amplitude * np.exp(
            1j
            * (
                2.0
                * np.pi
                * cfg.interferer_frequency_cycles_per_chip
                * n
                + phase
            )
        )
    return rx


def ber_sweeps(
    cfg: DsssConfig, code: np.ndarray, rng: np.random.Generator
) -> list[dict[str, float | int]]:
    results: list[dict[str, float | int]] = []
    for ebn0_db in cfg.ebn0_db_values:
        bits = rng.integers(0, 2, cfg.bits_per_point, dtype=np.uint8)
        tx = spread(bits, code)
        awgn_rx = add_channel(
            tx, ebn0_db, code.size, cfg, rng, interference=False
        )
        interfered_rx = add_channel(
            tx, ebn0_db, code.size, cfg, rng, interference=True
        )
        awgn_bits = despread(awgn_rx, code)
        interfered_bits = despread(interfered_rx, code)
        awgn_errors = int(np.count_nonzero(awgn_bits != bits))
        interfered_errors = int(np.count_nonzero(interfered_bits != bits))
        results.append(
            {
                "ebn0_db": float(ebn0_db),
                "compared_bits": int(bits.size),
                "awgn_bit_errors": awgn_errors,
                "awgn_ber": float(awgn_errors / bits.size),
                "narrowband_interference_bit_errors": interfered_errors,
                "narrowband_interference_ber": float(
                    interfered_errors / bits.size
                ),
            }
        )
    return results


def acquisition_example(
    cfg: DsssConfig, code: np.ndarray, rng: np.random.Generator
) -> tuple[np.ndarray, int]:
    prefix = (
        rng.standard_normal(cfg.acquisition_prefix_chips)
        + 1j * rng.standard_normal(cfg.acquisition_prefix_chips)
    )
    preamble = np.tile(code, 3).astype(np.complex128)
    waveform = np.concatenate((prefix, preamble))
    signal_power = 1.0
    noise_power = signal_power / (10.0 ** (cfg.acquisition_snr_db / 10.0))
    noise = np.sqrt(noise_power / 2.0) * (
        rng.standard_normal(waveform.size)
        + 1j * rng.standard_normal(waveform.size)
    )
    rx = waveform + noise
    correlation = np.abs(np.correlate(rx, code, mode="valid"))
    # Fold the three repeated preamble correlations onto one code period.
    # This is both more robust at low SNR and selects the first occurrence
    # instead of whichever repetition happens to contain the largest noise peak.
    folded = np.asarray(
        [np.sum(correlation[offset:: code.size]) for offset in range(code.size)]
    )
    return correlation, int(np.argmax(folded))


def interference_suppression_db(cfg: DsssConfig, code: np.ndarray) -> float:
    n = np.arange(code.size)
    tone = np.exp(
        1j * 2.0 * np.pi * cfg.interferer_frequency_cycles_per_chip * n
    )
    input_rms = np.sqrt(np.mean(np.abs(tone) ** 2))
    despread_amplitude = abs(np.sum(tone * code)) / code.size
    return float(20.0 * np.log10(input_rms / max(despread_amplitude, 1e-15)))


def main() -> None:
    cfg = DsssConfig()
    rng = np.random.default_rng(cfg.seed)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    code = m_sequence(cfg.lfsr_order)
    ber_results = ber_sweeps(cfg, code, rng)
    correlation, detected_start = acquisition_example(cfg, code, rng)

    cyclic_autocorrelation = np.asarray(
        [np.mean(code * np.roll(code, shift)) for shift in range(code.size)]
    )
    processing_gain_db = float(10.0 * np.log10(code.size))
    suppression_db = interference_suppression_db(cfg, code)

    plt.figure(figsize=(7.8, 4.4))
    plt.plot(np.arange(code.size), cyclic_autocorrelation)
    plt.grid(True, alpha=0.35)
    plt.xlabel("Cyclic shift, chips")
    plt.ylabel("Normalized correlation")
    plt.title("Lab 8.13 - PN sequence cyclic autocorrelation")
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab813_dsss_autocorrelation.png", dpi=180)
    plt.close()

    plt.figure(figsize=(7.8, 4.4))
    plt.plot(np.arange(correlation.size), correlation)
    plt.axvline(
        cfg.acquisition_prefix_chips,
        linestyle=":",
        color="tab:green",
        label="true start",
    )
    plt.axvline(
        detected_start,
        linestyle="--",
        color="tab:red",
        label="detected start",
    )
    plt.grid(True, alpha=0.35)
    plt.xlabel("Candidate start, chips")
    plt.ylabel("|correlation|")
    plt.title("Lab 8.13 - DSSS acquisition by correlation")
    plt.legend()
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab813_dsss_acquisition.png", dpi=180)
    plt.close()

    plt.figure(figsize=(7.8, 4.4))
    floor = 0.5 / cfg.bits_per_point
    plt.semilogy(
        [item["ebn0_db"] for item in ber_results],
        [max(float(item["awgn_ber"]), floor) for item in ber_results],
        marker="o",
        label="AWGN",
    )
    plt.semilogy(
        [item["ebn0_db"] for item in ber_results],
        [
            max(float(item["narrowband_interference_ber"]), floor)
            for item in ber_results
        ],
        marker="s",
        label=f"AWGN + tone, J/S={cfg.interferer_js_db:.0f} dB",
    )
    plt.grid(True, which="both", alpha=0.35)
    plt.xlabel("Eb/N0, dB")
    plt.ylabel("Bit error rate after despreading")
    plt.title("Lab 8.13 - DSSS BER and narrowband interference")
    plt.legend()
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab813_dsss_ber.png", dpi=180)
    plt.close()

    payload = {
        "config": asdict(cfg),
        "metrics": {
            "code_length": int(code.size),
            "processing_gain_db": processing_gain_db,
            "maximum_off_peak_autocorrelation": float(
                np.max(np.abs(cyclic_autocorrelation[1:]))
            ),
            "true_acquisition_start": cfg.acquisition_prefix_chips,
            "detected_acquisition_start": detected_start,
            "acquisition_error_chips": detected_start
            - cfg.acquisition_prefix_chips,
            "narrowband_interference_suppression_db": suppression_db,
            "compared_bits_per_point": cfg.bits_per_point,
            "ber_at_highest_ebn0_with_interference": ber_results[-1][
                "narrowband_interference_ber"
            ],
        },
        "ber_sweep": ber_results,
    }
    (ASSET_DIR / "lab813_dsss_metrics.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload["metrics"], indent=2))


if __name__ == "__main__":
    main()
