#!/usr/bin/env python3
"""Lab 8.4 — End-to-end synchronization chain.

Synthetic QPSK link with combined impairments:
  timing offset + carrier frequency offset + phase offset + noise.

The receiver applies a staged educational synchronization chain:
  timing phase search -> CFO estimation/correction -> phase correction -> decisions.

This closes the first Block 8 synchronization arc and produces constellation,
EVM/BER and stage-by-stage metric artifacts.
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
class SyncChainConfig:
    symbol_count: int = 4096
    samples_per_symbol: int = 8
    sample_rate_hz: float = 1.0e6
    timing_offset_samples: int = 3
    cfo_hz: float = 1350.0
    phase_offset_rad: float = 0.55
    noise_rms: float = 0.035
    seed: int = 84


@dataclass(frozen=True)
class SyncChainMetrics:
    true_timing_offset_samples: int
    estimated_timing_phase_samples: int
    true_cfo_hz: float
    estimated_cfo_hz: float
    cfo_error_hz: float
    true_phase_offset_rad: float
    estimated_phase_rad: float
    phase_error_rad: float
    evm_raw_percent: float
    evm_after_timing_percent: float
    evm_after_cfo_percent: float
    evm_final_percent: float
    ber_raw: float
    ber_final: float
    bit_errors_raw: int
    bit_errors_final: int
    compared_bits: int


def bits_to_qpsk(bits: np.ndarray) -> np.ndarray:
    pairs = bits.reshape(-1, 2)
    i = np.where(pairs[:, 0] == 0, 1.0, -1.0)
    q = np.where(pairs[:, 1] == 0, 1.0, -1.0)
    return (i + 1j * q) / np.sqrt(2.0)


def qpsk_to_bits(symbols: np.ndarray) -> np.ndarray:
    bits = np.empty(2 * len(symbols), dtype=np.uint8)
    bits[0::2] = np.where(np.real(symbols) >= 0, 0, 1)
    bits[1::2] = np.where(np.imag(symbols) >= 0, 0, 1)
    return bits


def rectangular_pulse_train(symbols: np.ndarray, sps: int) -> np.ndarray:
    return np.repeat(symbols, sps).astype(np.complex128)


def apply_integer_timing_offset(x: np.ndarray, offset_samples: int) -> np.ndarray:
    return np.concatenate([np.zeros(offset_samples, dtype=np.complex128), x])[: len(x)]


def complex_osc(freq_hz: float, fs_hz: float, n: int) -> np.ndarray:
    t = np.arange(n) / fs_hz
    return np.exp(1j * 2.0 * np.pi * freq_hz * t)


def sample_symbols(x: np.ndarray, sps: int, phase: int, symbol_count: int) -> np.ndarray:
    return x[phase::sps][:symbol_count]


def scalar_align(ref: np.ndarray, rx: np.ndarray) -> np.ndarray:
    n = min(len(ref), len(rx))
    ref_n = ref[:n]
    rx_n = rx[:n]
    gain = np.vdot(ref_n, rx_n) / max(np.vdot(ref_n, ref_n), 1e-15)
    return rx_n / gain


def evm(ref: np.ndarray, rx: np.ndarray) -> tuple[float, float]:
    n = min(len(ref), len(rx))
    ref_n = ref[:n]
    rx_n = rx[:n]
    err = rx_n - ref_n
    evm_rms = np.sqrt(np.mean(np.abs(err) ** 2)) / max(np.sqrt(np.mean(np.abs(ref_n) ** 2)), 1e-15)
    return float(100.0 * evm_rms), float(20.0 * np.log10(max(evm_rms, 1e-15)))


def ber(ref_bits: np.ndarray, rx_symbols: np.ndarray) -> tuple[float, int, int]:
    rx_bits = qpsk_to_bits(rx_symbols)
    compared = min(len(ref_bits), len(rx_bits))
    errors = int(np.sum(ref_bits[:compared] != rx_bits[:compared]))
    return float(errors / max(compared, 1)), errors, int(compared)


def estimate_timing_phase(ref_symbols: np.ndarray, rx_samples: np.ndarray, sps: int) -> tuple[int, list[float]]:
    evm_by_phase: list[float] = []
    for phase in range(sps):
        candidate = sample_symbols(rx_samples, sps, phase, len(ref_symbols))
        candidate_aligned = scalar_align(ref_symbols, candidate)
        evm_percent, _ = evm(ref_symbols, candidate_aligned)
        evm_by_phase.append(evm_percent)
    return int(np.argmin(evm_by_phase)), evm_by_phase


def estimate_cfo_known_symbols(ref: np.ndarray, rx: np.ndarray, symbol_rate_hz: float) -> float:
    n = min(len(ref), len(rx))
    mixed = rx[:n] * np.conj(ref[:n])
    phase = np.unwrap(np.angle(mixed))
    idx = np.arange(n, dtype=np.float64)
    slope, _ = np.polyfit(idx, phase, 1)
    return float((slope / (2.0 * np.pi)) * symbol_rate_hz)


def estimate_phase_known_symbols(ref: np.ndarray, rx: np.ndarray) -> float:
    n = min(len(ref), len(rx))
    return float(np.angle(np.vdot(ref[:n], rx[:n])))


def wrap_pi(x: float) -> float:
    return float((x + np.pi) % (2.0 * np.pi) - np.pi)


def save_constellation(path: Path, symbols: np.ndarray, title: str) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    shown = symbols[:2500]
    plt.figure(figsize=(5.2, 5.0))
    plt.scatter(np.real(shown), np.imag(shown), s=5, alpha=0.45)
    plt.grid(True, alpha=0.35)
    plt.xlabel("In-phase")
    plt.ylabel("Quadrature")
    plt.axis("equal")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def save_stage_bars(path: Path, labels: list[str], values: list[float], ylabel: str, title: str) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7.4, 4.3))
    plt.bar(labels, values)
    plt.grid(True, axis="y", alpha=0.35)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.xticks(rotation=15)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def save_timing_search(path: Path, evm_by_phase: list[float]) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    phases = np.arange(len(evm_by_phase))
    plt.figure(figsize=(7.2, 4.3))
    plt.plot(phases, evm_by_phase, marker="o")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Sampling phase, samples")
    plt.ylabel("EVM, %")
    plt.title("Lab 8.4 — Timing search inside full sync chain")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def main() -> None:
    cfg = SyncChainConfig()
    rng = np.random.default_rng(cfg.seed)

    bits = rng.integers(0, 2, size=2 * cfg.symbol_count, dtype=np.uint8)
    tx_symbols = bits_to_qpsk(bits)
    tx_samples = rectangular_pulse_train(tx_symbols, cfg.samples_per_symbol)

    rx_samples = apply_integer_timing_offset(tx_samples, cfg.timing_offset_samples)
    rx_samples = rx_samples * complex_osc(cfg.cfo_hz, cfg.sample_rate_hz, len(rx_samples))
    rx_samples = rx_samples * np.exp(1j * cfg.phase_offset_rad)
    rx_samples += cfg.noise_rms * (
        rng.standard_normal(len(rx_samples)) + 1j * rng.standard_normal(len(rx_samples))
    )

    # Raw receiver intentionally uses phase 0 and no synchronization.
    raw_symbols = sample_symbols(rx_samples, cfg.samples_per_symbol, 0, cfg.symbol_count)
    raw_aligned = scalar_align(tx_symbols, raw_symbols)
    evm_raw_percent, _ = evm(tx_symbols, raw_aligned)
    ber_raw, err_raw, compared = ber(bits, raw_aligned)

    best_phase, evm_by_phase = estimate_timing_phase(tx_symbols, rx_samples, cfg.samples_per_symbol)
    timing_symbols = sample_symbols(rx_samples, cfg.samples_per_symbol, best_phase, cfg.symbol_count)
    timing_aligned = scalar_align(tx_symbols, timing_symbols)
    evm_after_timing_percent, _ = evm(tx_symbols, timing_aligned)

    symbol_rate_hz = cfg.sample_rate_hz / cfg.samples_per_symbol
    estimated_cfo_hz = estimate_cfo_known_symbols(tx_symbols, timing_symbols, symbol_rate_hz)
    n = np.arange(len(timing_symbols))
    cfo_corrected = timing_symbols * np.exp(-1j * 2.0 * np.pi * estimated_cfo_hz * n / symbol_rate_hz)
    cfo_aligned = scalar_align(tx_symbols, cfo_corrected)
    evm_after_cfo_percent, _ = evm(tx_symbols, cfo_aligned)

    estimated_phase = estimate_phase_known_symbols(tx_symbols, cfo_corrected)
    final_symbols = cfo_corrected * np.exp(-1j * estimated_phase)
    final_aligned = scalar_align(tx_symbols, final_symbols)
    evm_final_percent, _ = evm(tx_symbols, final_aligned)
    ber_final, err_final, _ = ber(bits, final_aligned)

    metrics = SyncChainMetrics(
        true_timing_offset_samples=cfg.timing_offset_samples,
        estimated_timing_phase_samples=best_phase,
        true_cfo_hz=cfg.cfo_hz,
        estimated_cfo_hz=estimated_cfo_hz,
        cfo_error_hz=estimated_cfo_hz - cfg.cfo_hz,
        true_phase_offset_rad=cfg.phase_offset_rad,
        estimated_phase_rad=estimated_phase,
        phase_error_rad=wrap_pi(estimated_phase - cfg.phase_offset_rad),
        evm_raw_percent=evm_raw_percent,
        evm_after_timing_percent=evm_after_timing_percent,
        evm_after_cfo_percent=evm_after_cfo_percent,
        evm_final_percent=evm_final_percent,
        ber_raw=ber_raw,
        ber_final=ber_final,
        bit_errors_raw=err_raw,
        bit_errors_final=err_final,
        compared_bits=compared,
    )

    save_constellation(ASSET_DIR / "lab84_sync_constellation_raw.png", raw_aligned, "Lab 8.4 — Raw constellation")
    save_constellation(ASSET_DIR / "lab84_sync_constellation_after_timing.png", timing_aligned, "Lab 8.4 — After timing selection")
    save_constellation(ASSET_DIR / "lab84_sync_constellation_final.png", final_aligned, "Lab 8.4 — Final synchronized constellation")
    save_timing_search(ASSET_DIR / "lab84_sync_timing_search.png", evm_by_phase)
    save_stage_bars(
        ASSET_DIR / "lab84_sync_evm_stages.png",
        ["raw", "timing", "CFO", "final"],
        [evm_raw_percent, evm_after_timing_percent, evm_after_cfo_percent, evm_final_percent],
        "EVM, %",
        "Lab 8.4 — EVM after each synchronization stage",
    )
    save_stage_bars(
        ASSET_DIR / "lab84_sync_ber_summary.png",
        ["raw", "final"],
        [ber_raw, ber_final],
        "BER",
        "Lab 8.4 — BER before and after synchronization",
    )

    metrics_path = ASSET_DIR / "lab84_sync_chain_metrics.json"
    metrics_path.write_text(
        json.dumps({"config": asdict(cfg), "metrics": asdict(metrics), "evm_by_phase_percent": evm_by_phase}, indent=2),
        encoding="utf-8",
    )

    print("Lab 8.4 — End-to-end synchronization chain")
    print(f"Timing offset true/estimated: {metrics.true_timing_offset_samples}/{metrics.estimated_timing_phase_samples} samples")
    print(f"CFO true/estimated/error: {metrics.true_cfo_hz:.3f}/{metrics.estimated_cfo_hz:.3f}/{metrics.cfo_error_hz:.3f} Hz")
    print(f"Phase true/estimated/error: {metrics.true_phase_offset_rad:.6f}/{metrics.estimated_phase_rad:.6f}/{metrics.phase_error_rad:.6f} rad")
    print(f"EVM raw/timing/CFO/final: {metrics.evm_raw_percent:.3f}/{metrics.evm_after_timing_percent:.3f}/{metrics.evm_after_cfo_percent:.3f}/{metrics.evm_final_percent:.3f} %")
    print(f"BER raw/final: {metrics.ber_raw:.6e}/{metrics.ber_final:.6e}")
    print(f"Metrics JSON: {metrics_path}")


if __name__ == "__main__":
    main()
