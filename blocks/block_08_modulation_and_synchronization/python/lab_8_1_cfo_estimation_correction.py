#!/usr/bin/env python3
"""Lab 8.1 — Carrier frequency offset estimation and correction.

Synthetic QPSK example with carrier frequency offset (CFO). The script estimates
CFO using the 4th-power method, corrects the received signal, compensates a
constant phase offset and reports EVM/BER before and after synchronization.
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
class CfoConfig:
    symbol_count: int = 4096
    sample_rate_hz: float = 1.0e6
    cfo_hz: float = 2750.0
    phase_offset_rad: float = 0.65
    noise_rms: float = 0.035
    seed: int = 81


@dataclass(frozen=True)
class CfoMetrics:
    true_cfo_hz: float
    estimated_cfo_hz: float
    cfo_error_hz: float
    evm_before_percent: float
    evm_after_percent: float
    evm_before_db: float
    evm_after_db: float
    ber_before: float
    ber_after: float
    bit_errors_before: int
    bit_errors_after: int
    compared_bits: int
    residual_phase_rad: float


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


def estimate_cfo_4th_power(rx: np.ndarray, fs_hz: float) -> float:
    z = rx**4
    phase = np.unwrap(np.angle(z))
    n = np.arange(len(z), dtype=np.float64)
    slope, _ = np.polyfit(n, phase, 1)
    return float((slope / (2.0 * np.pi)) * fs_hz / 4.0)


def estimate_phase_qpsk(rx: np.ndarray) -> float:
    # After CFO correction, QPSK phase can be estimated from the 4th-power mean.
    return float(np.angle(np.mean(rx**4)) / 4.0)


def scalar_align(ref: np.ndarray, rx: np.ndarray) -> np.ndarray:
    gain = np.vdot(ref, rx) / max(np.vdot(ref, ref), 1e-15)
    return rx / gain


def evm(ref: np.ndarray, rx: np.ndarray) -> tuple[float, float]:
    err = rx - ref
    evm_rms = np.sqrt(np.mean(np.abs(err) ** 2)) / max(np.sqrt(np.mean(np.abs(ref) ** 2)), 1e-15)
    evm_percent = float(100.0 * evm_rms)
    evm_db = float(20.0 * np.log10(max(evm_rms, 1e-15)))
    return evm_percent, evm_db


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


def save_phase_plot(path: Path, rx: np.ndarray, corrected: np.ndarray) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    n = min(800, len(rx))
    plt.figure(figsize=(7.2, 4.3))
    plt.plot(np.unwrap(np.angle(rx[:n])), label="before CFO correction")
    plt.plot(np.unwrap(np.angle(corrected[:n])), label="after CFO correction")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Symbol index")
    plt.ylabel("Unwrapped phase, rad")
    plt.title("Lab 8.1 — Phase evolution before/after CFO correction")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def main() -> None:
    cfg = CfoConfig()
    rng = np.random.default_rng(cfg.seed)
    bits = rng.integers(0, 2, size=2 * cfg.symbol_count, dtype=np.uint8)
    tx = bits_to_qpsk(bits)

    n = np.arange(cfg.symbol_count)
    cfo_phase = 2.0 * np.pi * cfg.cfo_hz * n / cfg.sample_rate_hz
    rx = tx * np.exp(1j * (cfo_phase + cfg.phase_offset_rad))
    rx += cfg.noise_rms * (rng.standard_normal(cfg.symbol_count) + 1j * rng.standard_normal(cfg.symbol_count))

    estimated_cfo_hz = estimate_cfo_4th_power(rx, cfg.sample_rate_hz)
    corrected_cfo = rx * np.exp(-1j * 2.0 * np.pi * estimated_cfo_hz * n / cfg.sample_rate_hz)
    residual_phase = estimate_phase_qpsk(corrected_cfo)
    corrected = corrected_cfo * np.exp(-1j * residual_phase)

    before_aligned = scalar_align(tx, rx)
    after_aligned = scalar_align(tx, corrected)

    evm_before_percent, evm_before_db = evm(tx, before_aligned)
    evm_after_percent, evm_after_db = evm(tx, after_aligned)
    ber_before, bit_errors_before, compared_bits = ber(bits, before_aligned)
    ber_after, bit_errors_after, _ = ber(bits, after_aligned)

    metrics = CfoMetrics(
        true_cfo_hz=cfg.cfo_hz,
        estimated_cfo_hz=estimated_cfo_hz,
        cfo_error_hz=estimated_cfo_hz - cfg.cfo_hz,
        evm_before_percent=evm_before_percent,
        evm_after_percent=evm_after_percent,
        evm_before_db=evm_before_db,
        evm_after_db=evm_after_db,
        ber_before=ber_before,
        ber_after=ber_after,
        bit_errors_before=bit_errors_before,
        bit_errors_after=bit_errors_after,
        compared_bits=compared_bits,
        residual_phase_rad=residual_phase,
    )

    save_constellation(ASSET_DIR / "lab81_cfo_constellation_before.png", rx, "Lab 8.1 — Constellation before CFO correction")
    save_constellation(ASSET_DIR / "lab81_cfo_constellation_after.png", after_aligned, "Lab 8.1 — Constellation after CFO correction")
    save_phase_plot(ASSET_DIR / "lab81_cfo_phase_evolution.png", rx, corrected)

    metrics_path = ASSET_DIR / "lab81_cfo_metrics.json"
    metrics_path.write_text(
        json.dumps({"config": asdict(cfg), "metrics": asdict(metrics)}, indent=2),
        encoding="utf-8",
    )

    print("Lab 8.1 — CFO estimation and correction")
    print(f"True CFO: {metrics.true_cfo_hz:.3f} Hz")
    print(f"Estimated CFO: {metrics.estimated_cfo_hz:.3f} Hz")
    print(f"CFO error: {metrics.cfo_error_hz:.3f} Hz")
    print(f"EVM before: {metrics.evm_before_percent:.3f} % ({metrics.evm_before_db:.2f} dB)")
    print(f"EVM after: {metrics.evm_after_percent:.3f} % ({metrics.evm_after_db:.2f} dB)")
    print(f"BER before: {metrics.ber_before:.6e} ({metrics.bit_errors_before}/{metrics.compared_bits})")
    print(f"BER after: {metrics.ber_after:.6e} ({metrics.bit_errors_after}/{metrics.compared_bits})")
    print(f"Residual phase estimate: {metrics.residual_phase_rad:.6f} rad")
    print(f"Metrics JSON: {metrics_path}")


if __name__ == "__main__":
    main()
