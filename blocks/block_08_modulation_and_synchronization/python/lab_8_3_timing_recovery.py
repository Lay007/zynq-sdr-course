#!/usr/bin/env python3
"""Lab 8.3 — Symbol timing offset and recovery.

Synthetic QPSK example with oversampling, rectangular pulse shaping, a fractional
sample timing offset, noise and a simple timing-phase search. The lab estimates
which sampling phase gives the lowest EVM and compares BER/EVM before and after
symbol timing recovery.
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
class TimingConfig:
    symbol_count: int = 4096
    samples_per_symbol: int = 8
    timing_offset_samples: int = 3
    noise_rms: float = 0.045
    seed: int = 83


@dataclass(frozen=True)
class TimingMetrics:
    true_timing_offset_samples: int
    estimated_best_phase_samples: int
    evm_before_percent: float
    evm_after_percent: float
    evm_before_db: float
    evm_after_db: float
    ber_before: float
    ber_after: float
    bit_errors_before: int
    bit_errors_after: int
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
    # Delay the signal by offset_samples. This creates wrong sampling phase when
    # the receiver still samples at phase 0.
    return np.concatenate([np.zeros(offset_samples, dtype=np.complex128), x])[: len(x)]


def sample_symbols(x: np.ndarray, sps: int, phase: int, symbol_count: int) -> np.ndarray:
    samples = x[phase::sps]
    return samples[:symbol_count]


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


def timing_phase_search(ref_symbols: np.ndarray, x: np.ndarray, sps: int) -> tuple[int, list[float]]:
    evm_by_phase: list[float] = []
    for phase in range(sps):
        rx = sample_symbols(x, sps, phase, len(ref_symbols))
        rx_aligned = scalar_align(ref_symbols, rx)
        evm_percent, _ = evm(ref_symbols, rx_aligned)
        evm_by_phase.append(evm_percent)
    return int(np.argmin(evm_by_phase)), evm_by_phase


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


def save_timing_metric(path: Path, evm_by_phase: list[float]) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    phases = np.arange(len(evm_by_phase))
    plt.figure(figsize=(7.2, 4.3))
    plt.plot(phases, evm_by_phase, marker="o")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Sampling phase, samples")
    plt.ylabel("EVM, %")
    plt.title("Lab 8.3 — Timing phase search")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def save_eye_preview(path: Path, x: np.ndarray, sps: int) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    traces = min(120, len(x) // sps - 1)
    plt.figure(figsize=(7.2, 4.3))
    for k in range(traces):
        seg = np.real(x[k * sps : (k + 2) * sps])
        if len(seg) == 2 * sps:
            plt.plot(np.arange(2 * sps), seg, alpha=0.15)
    plt.grid(True, alpha=0.35)
    plt.xlabel("Sample index within 2-symbol window")
    plt.ylabel("I amplitude")
    plt.title("Lab 8.3 — Educational eye preview")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def main() -> None:
    cfg = TimingConfig()
    rng = np.random.default_rng(cfg.seed)
    bits = rng.integers(0, 2, size=2 * cfg.symbol_count, dtype=np.uint8)
    tx_symbols = bits_to_qpsk(bits)

    tx_samples = rectangular_pulse_train(tx_symbols, cfg.samples_per_symbol)
    rx_samples = apply_integer_timing_offset(tx_samples, cfg.timing_offset_samples)
    rx_samples += cfg.noise_rms * (
        rng.standard_normal(len(rx_samples)) + 1j * rng.standard_normal(len(rx_samples))
    )

    wrong_phase = 0
    rx_wrong = sample_symbols(rx_samples, cfg.samples_per_symbol, wrong_phase, cfg.symbol_count)
    rx_wrong_aligned = scalar_align(tx_symbols, rx_wrong)

    best_phase, evm_by_phase = timing_phase_search(tx_symbols, rx_samples, cfg.samples_per_symbol)
    rx_best = sample_symbols(rx_samples, cfg.samples_per_symbol, best_phase, cfg.symbol_count)
    rx_best_aligned = scalar_align(tx_symbols, rx_best)

    evm_before_percent, evm_before_db = evm(tx_symbols, rx_wrong_aligned)
    evm_after_percent, evm_after_db = evm(tx_symbols, rx_best_aligned)
    ber_before, err_before, compared = ber(bits, rx_wrong_aligned)
    ber_after, err_after, _ = ber(bits, rx_best_aligned)

    metrics = TimingMetrics(
        true_timing_offset_samples=cfg.timing_offset_samples,
        estimated_best_phase_samples=best_phase,
        evm_before_percent=evm_before_percent,
        evm_after_percent=evm_after_percent,
        evm_before_db=evm_before_db,
        evm_after_db=evm_after_db,
        ber_before=ber_before,
        ber_after=ber_after,
        bit_errors_before=err_before,
        bit_errors_after=err_after,
        compared_bits=compared,
    )

    save_constellation(ASSET_DIR / "lab83_timing_constellation_wrong_phase.png", rx_wrong_aligned, "Lab 8.3 — Wrong sampling phase")
    save_constellation(ASSET_DIR / "lab83_timing_constellation_recovered.png", rx_best_aligned, "Lab 8.3 — Recovered timing phase")
    save_timing_metric(ASSET_DIR / "lab83_timing_phase_search.png", evm_by_phase)
    save_eye_preview(ASSET_DIR / "lab83_timing_eye_preview.png", rx_samples, cfg.samples_per_symbol)

    metrics_path = ASSET_DIR / "lab83_timing_metrics.json"
    metrics_path.write_text(
        json.dumps({"config": asdict(cfg), "metrics": asdict(metrics), "evm_by_phase_percent": evm_by_phase}, indent=2),
        encoding="utf-8",
    )

    print("Lab 8.3 — Timing recovery")
    print(f"True timing offset: {metrics.true_timing_offset_samples} samples")
    print(f"Estimated best phase: {metrics.estimated_best_phase_samples} samples")
    print(f"EVM before: {metrics.evm_before_percent:.3f} % ({metrics.evm_before_db:.2f} dB)")
    print(f"EVM after: {metrics.evm_after_percent:.3f} % ({metrics.evm_after_db:.2f} dB)")
    print(f"BER before: {metrics.ber_before:.6e} ({metrics.bit_errors_before}/{metrics.compared_bits})")
    print(f"BER after: {metrics.ber_after:.6e} ({metrics.bit_errors_after}/{metrics.compared_bits})")
    print(f"Metrics JSON: {metrics_path}")


if __name__ == "__main__":
    main()
