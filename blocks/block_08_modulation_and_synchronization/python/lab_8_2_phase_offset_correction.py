#!/usr/bin/env python3
"""Lab 8.2 — Phase offset estimation and decision-directed correction.

Synthetic QPSK example after CFO correction. The script injects a constant phase
offset and noise, estimates the phase using two methods and compares EVM/BER:
  1) 4th-power blind phase estimate,
  2) decision-directed phase refinement.
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
class PhaseConfig:
    symbol_count: int = 4096
    phase_offset_rad: float = 0.82
    noise_rms: float = 0.055
    seed: int = 82


@dataclass(frozen=True)
class PhaseMetrics:
    true_phase_offset_rad: float
    blind_phase_estimate_rad: float
    decision_directed_phase_estimate_rad: float
    blind_phase_error_rad: float
    decision_directed_phase_error_rad: float
    evm_before_percent: float
    evm_after_blind_percent: float
    evm_after_dd_percent: float
    ber_before: float
    ber_after_blind: float
    ber_after_dd: float
    bit_errors_before: int
    bit_errors_after_blind: int
    bit_errors_after_dd: int
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


def qpsk_slicer(symbols: np.ndarray) -> np.ndarray:
    i = np.where(np.real(symbols) >= 0, 1.0, -1.0)
    q = np.where(np.imag(symbols) >= 0, 1.0, -1.0)
    return (i + 1j * q) / np.sqrt(2.0)


def wrap_pi(x: float) -> float:
    return float((x + np.pi) % (2.0 * np.pi) - np.pi)


def estimate_phase_4th_power(rx: np.ndarray) -> float:
    # QPSK has pi/2 rotational ambiguity. This educational lab uses a phase
    # offset inside the unambiguous interval and then refines with decisions.
    return float(np.angle(np.mean(rx**4)) / 4.0)


def estimate_phase_decision_directed(rx: np.ndarray) -> float:
    decisions = qpsk_slicer(rx)
    return float(np.angle(np.vdot(decisions, rx)))


def evm(ref: np.ndarray, rx: np.ndarray) -> tuple[float, float]:
    err = rx - ref
    evm_rms = np.sqrt(np.mean(np.abs(err) ** 2)) / max(np.sqrt(np.mean(np.abs(ref) ** 2)), 1e-15)
    return float(100.0 * evm_rms), float(20.0 * np.log10(max(evm_rms, 1e-15)))


def ber(ref_bits: np.ndarray, rx_symbols: np.ndarray) -> tuple[float, int, int]:
    rx_bits = qpsk_to_bits(rx_symbols)
    compared = min(len(ref_bits), len(rx_bits))
    errors = int(np.sum(ref_bits[:compared] != rx_bits[:compared]))
    return float(errors / max(compared, 1)), errors, int(compared)


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


def save_metric_bars(path: Path, metrics: PhaseMetrics) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    labels = ["before", "blind", "decision-directed"]
    evm_values = [metrics.evm_before_percent, metrics.evm_after_blind_percent, metrics.evm_after_dd_percent]
    plt.figure(figsize=(7.2, 4.3))
    plt.bar(labels, evm_values)
    plt.grid(True, axis="y", alpha=0.35)
    plt.ylabel("EVM, %")
    plt.title("Lab 8.2 — EVM improvement after phase correction")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def main() -> None:
    cfg = PhaseConfig()
    rng = np.random.default_rng(cfg.seed)
    bits = rng.integers(0, 2, size=2 * cfg.symbol_count, dtype=np.uint8)
    tx = bits_to_qpsk(bits)

    rx = tx * np.exp(1j * cfg.phase_offset_rad)
    rx += cfg.noise_rms * (rng.standard_normal(cfg.symbol_count) + 1j * rng.standard_normal(cfg.symbol_count))

    blind_phase = estimate_phase_4th_power(rx)
    after_blind = rx * np.exp(-1j * blind_phase)

    dd_phase = estimate_phase_decision_directed(after_blind)
    after_dd = after_blind * np.exp(-1j * dd_phase)
    total_dd_phase = blind_phase + dd_phase

    evm_before_percent, _ = evm(tx, rx)
    evm_after_blind_percent, _ = evm(tx, after_blind)
    evm_after_dd_percent, _ = evm(tx, after_dd)

    ber_before, err_before, compared = ber(bits, rx)
    ber_blind, err_blind, _ = ber(bits, after_blind)
    ber_dd, err_dd, _ = ber(bits, after_dd)

    metrics = PhaseMetrics(
        true_phase_offset_rad=cfg.phase_offset_rad,
        blind_phase_estimate_rad=blind_phase,
        decision_directed_phase_estimate_rad=total_dd_phase,
        blind_phase_error_rad=wrap_pi(blind_phase - cfg.phase_offset_rad),
        decision_directed_phase_error_rad=wrap_pi(total_dd_phase - cfg.phase_offset_rad),
        evm_before_percent=evm_before_percent,
        evm_after_blind_percent=evm_after_blind_percent,
        evm_after_dd_percent=evm_after_dd_percent,
        ber_before=ber_before,
        ber_after_blind=ber_blind,
        ber_after_dd=ber_dd,
        bit_errors_before=err_before,
        bit_errors_after_blind=err_blind,
        bit_errors_after_dd=err_dd,
        compared_bits=compared,
    )

    save_constellation(ASSET_DIR / "lab82_phase_constellation_before.png", rx, "Lab 8.2 — Before phase correction")
    save_constellation(ASSET_DIR / "lab82_phase_constellation_after_blind.png", after_blind, "Lab 8.2 — After blind phase correction")
    save_constellation(ASSET_DIR / "lab82_phase_constellation_after_dd.png", after_dd, "Lab 8.2 — After decision-directed refinement")
    save_metric_bars(ASSET_DIR / "lab82_phase_evm_comparison.png", metrics)

    metrics_path = ASSET_DIR / "lab82_phase_metrics.json"
    metrics_path.write_text(
        json.dumps({"config": asdict(cfg), "metrics": asdict(metrics)}, indent=2),
        encoding="utf-8",
    )

    print("Lab 8.2 — Phase offset correction")
    print(f"True phase offset: {metrics.true_phase_offset_rad:.6f} rad")
    print(f"Blind phase estimate: {metrics.blind_phase_estimate_rad:.6f} rad")
    print(f"Decision-directed total estimate: {metrics.decision_directed_phase_estimate_rad:.6f} rad")
    print(f"Blind phase error: {metrics.blind_phase_error_rad:.6f} rad")
    print(f"Decision-directed phase error: {metrics.decision_directed_phase_error_rad:.6f} rad")
    print(f"EVM before: {metrics.evm_before_percent:.3f} %")
    print(f"EVM after blind: {metrics.evm_after_blind_percent:.3f} %")
    print(f"EVM after decision-directed: {metrics.evm_after_dd_percent:.3f} %")
    print(f"BER before: {metrics.ber_before:.6e} ({metrics.bit_errors_before}/{metrics.compared_bits})")
    print(f"BER after blind: {metrics.ber_after_blind:.6e} ({metrics.bit_errors_after_blind}/{metrics.compared_bits})")
    print(f"BER after decision-directed: {metrics.ber_after_dd:.6e} ({metrics.bit_errors_after_dd}/{metrics.compared_bits})")
    print(f"Metrics JSON: {metrics_path}")


if __name__ == "__main__":
    main()
