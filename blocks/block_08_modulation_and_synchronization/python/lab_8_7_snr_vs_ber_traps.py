#!/usr/bin/env python3
"""Lab 8.7 — SNR is not enough: BER/EVM traps.

This deterministic QPSK experiment demonstrates a common SDR measurement
mistake: accepting a digital link from SNR alone. Several scenarios keep the
channel SNR high while BER becomes poor because the receiver has not solved
carrier, timing, phase or frame-alignment problems.
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
class LabConfig:
    symbol_count: int = 4096
    samples_per_symbol: int = 8
    sample_rate_hz: float = 3.84e6
    rrc_alpha: float = 0.35
    rrc_span_symbols: int = 8
    seed: int = 8701


@dataclass(frozen=True)
class Scenario:
    name: str
    snr_db: float
    cfo_hz: float = 0.0
    phase_deg: float = 0.0
    timing_offset_samples: int = 0
    clip_limit: float | None = None
    frame_slip_symbols: int = 0
    conclusion: str = ""


@dataclass(frozen=True)
class ScenarioMetrics:
    scenario: str
    snr_db: float
    evm_percent: float
    evm_db: float
    ber: float
    bit_errors: int
    compared_bits: int
    cfo_hz: float
    phase_deg: float
    timing_offset_samples: int
    frame_slip_symbols: int
    conclusion: str


def rrc_taps(alpha: float, span_symbols: int, sps: int) -> np.ndarray:
    """Generate unit-energy root-raised-cosine taps."""
    half_span = span_symbols * sps // 2
    t = np.arange(-half_span, half_span + 1, dtype=np.float64) / sps
    taps = np.empty_like(t)

    for idx, tau in enumerate(t):
        if abs(tau) < 1e-12:
            taps[idx] = 1.0 + alpha * (4.0 / np.pi - 1.0)
        elif alpha > 0.0 and abs(abs(tau) - 1.0 / (4.0 * alpha)) < 1e-12:
            taps[idx] = (alpha / np.sqrt(2.0)) * (
                (1.0 + 2.0 / np.pi) * np.sin(np.pi / (4.0 * alpha))
                + (1.0 - 2.0 / np.pi) * np.cos(np.pi / (4.0 * alpha))
            )
        else:
            numerator = (
                np.sin(np.pi * tau * (1.0 - alpha))
                + 4.0 * alpha * tau * np.cos(np.pi * tau * (1.0 + alpha))
            )
            denominator = np.pi * tau * (1.0 - (4.0 * alpha * tau) ** 2)
            taps[idx] = numerator / denominator

    taps /= np.sqrt(np.sum(taps**2))
    return taps


def bits_to_qpsk(bits: np.ndarray) -> np.ndarray:
    pairs = bits.reshape(-1, 2)
    i = np.where(pairs[:, 0] == 0, 1.0, -1.0)
    q = np.where(pairs[:, 1] == 0, 1.0, -1.0)
    return (i + 1j * q) / np.sqrt(2.0)


def qpsk_to_bits(symbols: np.ndarray) -> np.ndarray:
    bits = np.empty(2 * len(symbols), dtype=np.uint8)
    bits[0::2] = np.where(np.real(symbols) >= 0.0, 0, 1)
    bits[1::2] = np.where(np.imag(symbols) >= 0.0, 0, 1)
    return bits


def pulse_shape(symbols: np.ndarray, taps: np.ndarray, sps: int) -> np.ndarray:
    x = np.zeros(len(symbols) * sps, dtype=np.complex128)
    x[::sps] = symbols
    return np.convolve(x, taps, mode="full")


def add_awgn(x: np.ndarray, snr_db: float, rng: np.random.Generator) -> np.ndarray:
    signal_power = float(np.mean(np.abs(x) ** 2))
    noise_power = signal_power / (10.0 ** (snr_db / 10.0))
    noise = np.sqrt(noise_power / 2.0) * (
        rng.standard_normal(len(x)) + 1j * rng.standard_normal(len(x))
    )
    return x + noise


def apply_clip(x: np.ndarray, limit: float | None) -> np.ndarray:
    if limit is None:
        return x
    return np.clip(np.real(x), -limit, limit) + 1j * np.clip(np.imag(x), -limit, limit)


def scalar_aligned_evm(tx_symbols: np.ndarray, rx_symbols: np.ndarray) -> tuple[float, float]:
    n = min(len(tx_symbols), len(rx_symbols))
    tx = tx_symbols[:n]
    rx = rx_symbols[:n]
    gain = np.vdot(tx, rx) / max(float(np.vdot(tx, tx).real), 1e-15)
    rx_aligned = rx / gain if abs(gain) > 1e-15 else rx
    err = rx_aligned - tx
    evm_rms = np.sqrt(np.mean(np.abs(err) ** 2)) / max(
        np.sqrt(np.mean(np.abs(tx) ** 2)),
        1e-15,
    )
    evm_percent = float(100.0 * evm_rms)
    evm_db = float(20.0 * np.log10(max(evm_rms, 1e-15)))
    return evm_percent, evm_db


def run_scenario(
    cfg: LabConfig,
    scenario: Scenario,
    tx_bits: np.ndarray,
    tx_symbols: np.ndarray,
    taps: np.ndarray,
    rng: np.random.Generator,
) -> tuple[ScenarioMetrics, np.ndarray]:
    tx_samples = pulse_shape(tx_symbols, taps, cfg.samples_per_symbol)
    n = len(tx_samples)
    time = np.arange(n) / cfg.sample_rate_hz

    rx = tx_samples * np.exp(1j * (2.0 * np.pi * scenario.cfo_hz * time + np.deg2rad(scenario.phase_deg)))
    rx = add_awgn(rx, scenario.snr_db, rng)
    rx = apply_clip(rx, scenario.clip_limit)

    matched = np.convolve(rx, taps, mode="full")
    nominal_delay = len(taps) - 1
    start = nominal_delay + scenario.timing_offset_samples
    rx_symbols = matched[start : start + cfg.symbol_count * cfg.samples_per_symbol : cfg.samples_per_symbol]

    if scenario.frame_slip_symbols:
        rx_symbols_for_decision = rx_symbols[scenario.frame_slip_symbols :]
    else:
        rx_symbols_for_decision = rx_symbols

    n_sym = min(len(tx_symbols), len(rx_symbols_for_decision))
    tx_cmp_symbols = tx_symbols[:n_sym]
    rx_cmp_symbols = rx_symbols_for_decision[:n_sym]
    rx_bits = qpsk_to_bits(rx_cmp_symbols)
    tx_cmp_bits = tx_bits[: len(rx_bits)]

    bit_errors = int(np.sum(tx_cmp_bits != rx_bits))
    compared_bits = int(len(tx_cmp_bits))
    ber = float(bit_errors / max(compared_bits, 1))
    evm_percent, evm_db = scalar_aligned_evm(tx_cmp_symbols, rx_cmp_symbols)

    metrics = ScenarioMetrics(
        scenario=scenario.name,
        snr_db=scenario.snr_db,
        evm_percent=evm_percent,
        evm_db=evm_db,
        ber=ber,
        bit_errors=bit_errors,
        compared_bits=compared_bits,
        cfo_hz=scenario.cfo_hz,
        phase_deg=scenario.phase_deg,
        timing_offset_samples=scenario.timing_offset_samples,
        frame_slip_symbols=scenario.frame_slip_symbols,
        conclusion=scenario.conclusion,
    )
    return metrics, rx_cmp_symbols


def save_summary_plot(metrics: list[ScenarioMetrics]) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    labels = [m.scenario.replace("_", "\n") for m in metrics]
    snr = np.array([m.snr_db for m in metrics])
    ber = np.array([max(m.ber, 1.0 / max(m.compared_bits, 1)) for m in metrics])

    x = np.arange(len(metrics))
    fig, ax1 = plt.subplots(figsize=(9.0, 4.8))
    ax2 = ax1.twinx()
    ax1.bar(x, snr, width=0.55, alpha=0.55, label="SNR")
    ax2.plot(x, ber, marker="o", linewidth=2.0, label="BER")

    ax1.set_ylabel("SNR, dB")
    ax2.set_ylabel("BER")
    ax2.set_yscale("log")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=25, ha="right")
    ax1.set_title("Lab 8.7 — high SNR does not guarantee low BER")
    ax1.grid(True, axis="y", alpha=0.35)
    fig.tight_layout()
    fig.savefig(ASSET_DIR / "lab87_snr_vs_ber_summary.png", dpi=180)
    plt.close(fig)


def save_constellation(path: Path, symbols: np.ndarray, title: str) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    shown = symbols[:2500]
    plt.figure(figsize=(5.2, 5.0))
    plt.scatter(np.real(shown), np.imag(shown), s=5, alpha=0.45)
    plt.grid(True, alpha=0.35)
    plt.xlabel("In-phase")
    plt.ylabel("Quadrature")
    plt.title(title)
    plt.axis("equal")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def main() -> None:
    cfg = LabConfig()
    rng = np.random.default_rng(cfg.seed)
    taps = rrc_taps(cfg.rrc_alpha, cfg.rrc_span_symbols, cfg.samples_per_symbol)

    tx_bits = rng.integers(0, 2, size=2 * cfg.symbol_count, dtype=np.uint8)
    tx_symbols = bits_to_qpsk(tx_bits)

    scenarios = [
        Scenario(
            name="awgn_reference",
            snr_db=18.0,
            conclusion="Baseline: with only AWGN, SNR and BER are consistent.",
        ),
        Scenario(
            name="high_snr_cfo",
            snr_db=25.0,
            cfo_hz=25_000.0,
            conclusion="Carrier-frequency offset rotates the constellation; SNR alone misses this failure.",
        ),
        Scenario(
            name="timing_error",
            snr_db=25.0,
            timing_offset_samples=3,
            conclusion="The signal is strong, but symbol decisions are made away from the best sampling instant.",
        ),
        Scenario(
            name="qpsk_90deg_ambiguity",
            snr_db=25.0,
            phase_deg=90.0,
            conclusion="QPSK needs preamble-based quadrant resolution or differential coding before BER is trusted.",
        ),
        Scenario(
            name="clipping_overload",
            snr_db=25.0,
            clip_limit=0.18,
            conclusion="Overload is a nonlinear impairment; it is not captured by a simple noise-only SNR view.",
        ),
        Scenario(
            name="wrong_frame_alignment",
            snr_db=25.0,
            frame_slip_symbols=1,
            conclusion="A clean packet is useless when the receiver compares the wrong symbol boundary or frame.",
        ),
    ]

    all_metrics: list[ScenarioMetrics] = []
    constellation_examples: dict[str, np.ndarray] = {}

    for scenario in scenarios:
        metrics, rx_symbols = run_scenario(cfg, scenario, tx_bits, tx_symbols, taps, rng)
        all_metrics.append(metrics)
        constellation_examples[scenario.name] = rx_symbols

    save_summary_plot(all_metrics)
    save_constellation(
        ASSET_DIR / "lab87_constellation_cfo.png",
        constellation_examples["high_snr_cfo"],
        "Lab 8.7 — high SNR with uncorrected CFO",
    )
    save_constellation(
        ASSET_DIR / "lab87_constellation_timing_error.png",
        constellation_examples["timing_error"],
        "Lab 8.7 — high SNR with timing error",
    )
    save_constellation(
        ASSET_DIR / "lab87_constellation_qpsk_phase_ambiguity.png",
        constellation_examples["qpsk_90deg_ambiguity"],
        "Lab 8.7 — high SNR with unresolved QPSK phase ambiguity",
    )

    metrics_path = ASSET_DIR / "lab87_snr_vs_ber_metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "config": asdict(cfg),
                "metrics": [asdict(item) for item in all_metrics],
                "acceptance_rule": "For digital links, SNR alone is not sufficient; report BER/FER and compared bit/frame count.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("Lab 8.7 — SNR is not enough")
    for item in all_metrics:
        print(
            f"{item.scenario:24s} "
            f"SNR={item.snr_db:5.1f} dB  "
            f"EVM={item.evm_percent:7.2f}%  "
            f"BER={item.ber:.6e} ({item.bit_errors}/{item.compared_bits})"
        )
    print(f"Metrics JSON: {metrics_path}")


if __name__ == "__main__":
    main()
