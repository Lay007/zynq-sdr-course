#!/usr/bin/env python3
"""Lab 7.3 — TX/RX loopback metrics.

Synthetic QPSK TX/RX loopback experiment:
  bits -> QPSK symbols -> TX pulse shaping placeholder -> frequency offset/noise
  -> DDC correction -> symbol decisions -> EVM/SNR/BER and figures.

The model is intentionally compact and deterministic. It is designed to teach
metric flow before moving to real RF captures and synchronization algorithms.
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
class LoopbackConfig:
    symbol_count: int = 4096
    samples_per_symbol: int = 4
    sample_rate_hz: float = 2.4e6
    tx_offset_hz: float = 100e3
    ddc_shift_hz: float = -100e3
    noise_rms: float = 0.045
    amplitude: float = 0.75
    seed: int = 123


@dataclass(frozen=True)
class LoopbackMetrics:
    evm_percent: float
    evm_db: float
    snr_estimate_db: float
    ber: float
    bit_errors: int
    compared_bits: int
    rx_peak_before_ddc_hz: float
    rx_peak_after_ddc_hz: float
    residual_frequency_error_hz: float


def bits_to_qpsk(bits: np.ndarray) -> np.ndarray:
    pairs = bits.reshape(-1, 2)
    # Gray-coded QPSK: 00 -> +1+j, 01 -> -1+j, 11 -> -1-j, 10 -> +1-j
    i = np.where(pairs[:, 0] == 0, 1.0, -1.0)
    q = np.where(pairs[:, 1] == 0, 1.0, -1.0)
    return (i + 1j * q) / np.sqrt(2.0)


def qpsk_to_bits(symbols: np.ndarray) -> np.ndarray:
    bits = np.empty(2 * len(symbols), dtype=np.uint8)
    bits[0::2] = np.where(np.real(symbols) >= 0, 0, 1)
    bits[1::2] = np.where(np.imag(symbols) >= 0, 0, 1)
    return bits


def upsample_symbols(symbols: np.ndarray, sps: int) -> np.ndarray:
    x = np.zeros(len(symbols) * sps, dtype=np.complex128)
    x[::sps] = symbols
    # Compact educational pulse shape: rectangular hold.
    return np.repeat(symbols, sps).astype(np.complex128)


def downsample_symbols(x: np.ndarray, sps: int) -> np.ndarray:
    # For the rectangular hold model and no timing offset, take the center sample.
    return x[sps // 2 :: sps]


def complex_osc(freq_hz: float, fs_hz: float, n: int) -> np.ndarray:
    t = np.arange(n) / fs_hz
    return np.exp(1j * 2 * np.pi * freq_hz * t)


def spectrum_db(x: np.ndarray, fs_hz: float) -> tuple[np.ndarray, np.ndarray]:
    window = np.hanning(len(x))
    coherent_gain = np.sum(window) / len(window)
    spec = np.fft.fftshift(np.fft.fft(x * window)) / (len(x) * coherent_gain)
    freq = np.fft.fftshift(np.fft.fftfreq(len(x), d=1 / fs_hz))
    mag_db = 20 * np.log10(np.maximum(np.abs(spec), 1e-15))
    return freq, mag_db


def estimate_peak_hz(x: np.ndarray, fs_hz: float) -> float:
    freq, mag_db = spectrum_db(x, fs_hz)
    return float(freq[int(np.argmax(mag_db))])


def compute_metrics(cfg: LoopbackConfig, tx_symbols: np.ndarray, rx_symbols: np.ndarray, bits: np.ndarray, rx_bits: np.ndarray, rx_before_ddc: np.ndarray, rx_after_ddc: np.ndarray) -> LoopbackMetrics:
    n = min(len(tx_symbols), len(rx_symbols))
    tx_ref = tx_symbols[:n] * cfg.amplitude
    rx = rx_symbols[:n]

    # Estimate and remove one complex scalar gain/phase before EVM.
    gain = np.vdot(tx_ref, rx) / max(np.vdot(tx_ref, tx_ref), 1e-15)
    rx_aligned = rx / gain
    err = rx_aligned - tx_ref
    evm_rms = np.sqrt(np.mean(np.abs(err) ** 2)) / max(np.sqrt(np.mean(np.abs(tx_ref) ** 2)), 1e-15)
    evm_percent = float(100.0 * evm_rms)
    evm_db = float(20.0 * np.log10(max(evm_rms, 1e-15)))
    snr_estimate_db = float(-20.0 * np.log10(max(evm_rms, 1e-15)))

    compared = min(len(bits), len(rx_bits))
    bit_errors = int(np.sum(bits[:compared] != rx_bits[:compared]))
    ber = float(bit_errors / max(compared, 1))

    peak_before = estimate_peak_hz(rx_before_ddc, cfg.sample_rate_hz)
    peak_after = estimate_peak_hz(rx_after_ddc, cfg.sample_rate_hz)
    residual_error = peak_after - (cfg.tx_offset_hz + cfg.ddc_shift_hz)

    return LoopbackMetrics(
        evm_percent=evm_percent,
        evm_db=evm_db,
        snr_estimate_db=snr_estimate_db,
        ber=ber,
        bit_errors=bit_errors,
        compared_bits=int(compared),
        rx_peak_before_ddc_hz=peak_before,
        rx_peak_after_ddc_hz=peak_after,
        residual_frequency_error_hz=float(residual_error),
    )


def save_constellation(path: Path, symbols: np.ndarray, title: str) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(5.2, 5.0))
    shown = symbols[:3000]
    plt.scatter(np.real(shown), np.imag(shown), s=5, alpha=0.45)
    plt.grid(True, alpha=0.35)
    plt.xlabel("In-phase")
    plt.ylabel("Quadrature")
    plt.title(title)
    plt.axis("equal")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def save_spectrum(path: Path, fs_hz: float, traces: list[tuple[str, np.ndarray]], title: str) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7.2, 4.3))
    for label, x in traces:
        freq, mag_db = spectrum_db(x, fs_hz)
        plt.plot(freq / 1e3, mag_db, label=label)
    plt.grid(True, alpha=0.35)
    plt.xlabel("Frequency, kHz")
    plt.ylabel("Magnitude, dBFS")
    plt.title(title)
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def main() -> None:
    cfg = LoopbackConfig()
    rng = np.random.default_rng(cfg.seed)

    bits = rng.integers(0, 2, size=2 * cfg.symbol_count, dtype=np.uint8)
    tx_symbols = bits_to_qpsk(bits)
    tx_samples = cfg.amplitude * upsample_symbols(tx_symbols, cfg.samples_per_symbol)

    tx_shifted = tx_samples * complex_osc(cfg.tx_offset_hz, cfg.sample_rate_hz, len(tx_samples))
    rx_before_ddc = tx_shifted + cfg.noise_rms * (
        rng.standard_normal(len(tx_shifted)) + 1j * rng.standard_normal(len(tx_shifted))
    )
    rx_after_ddc = rx_before_ddc * complex_osc(cfg.ddc_shift_hz, cfg.sample_rate_hz, len(rx_before_ddc))
    rx_symbols = downsample_symbols(rx_after_ddc, cfg.samples_per_symbol)

    # Hard decisions after scalar alignment for robust metric comparison.
    tx_ref = tx_symbols[: len(rx_symbols)] * cfg.amplitude
    gain = np.vdot(tx_ref, rx_symbols) / max(np.vdot(tx_ref, tx_ref), 1e-15)
    rx_aligned = rx_symbols / gain
    rx_bits = qpsk_to_bits(rx_aligned)

    metrics = compute_metrics(cfg, tx_symbols, rx_symbols, bits, rx_bits, rx_before_ddc, rx_after_ddc)

    save_spectrum(
        ASSET_DIR / "lab73_tx_rx_loopback_spectrum.png",
        cfg.sample_rate_hz,
        [("RX before DDC", rx_before_ddc), ("RX after DDC", rx_after_ddc)],
        "Lab 7.3 — TX/RX loopback spectrum",
    )
    save_constellation(
        ASSET_DIR / "lab73_tx_constellation.png",
        tx_symbols * cfg.amplitude,
        "Lab 7.3 — TX reference constellation",
    )
    save_constellation(
        ASSET_DIR / "lab73_rx_constellation_after_ddc.png",
        rx_aligned,
        "Lab 7.3 — RX constellation after DDC and scalar alignment",
    )

    metrics_path = ASSET_DIR / "lab73_tx_rx_loopback_metrics.json"
    metrics_path.write_text(
        json.dumps({"config": asdict(cfg), "metrics": asdict(metrics)}, indent=2),
        encoding="utf-8",
    )

    print("Lab 7.3 — TX/RX loopback metrics")
    print(f"Symbols: {cfg.symbol_count}")
    print(f"Samples per symbol: {cfg.samples_per_symbol}")
    print(f"TX offset: {cfg.tx_offset_hz:.3f} Hz")
    print(f"DDC shift: {cfg.ddc_shift_hz:.3f} Hz")
    print(f"RX peak before DDC: {metrics.rx_peak_before_ddc_hz:.3f} Hz")
    print(f"RX peak after DDC: {metrics.rx_peak_after_ddc_hz:.3f} Hz")
    print(f"Residual frequency error: {metrics.residual_frequency_error_hz:.3f} Hz")
    print(f"EVM: {metrics.evm_percent:.3f} % ({metrics.evm_db:.2f} dB)")
    print(f"SNR estimate: {metrics.snr_estimate_db:.2f} dB")
    print(f"BER: {metrics.ber:.6e} ({metrics.bit_errors}/{metrics.compared_bits})")
    print(f"Metrics JSON: {metrics_path}")


if __name__ == "__main__":
    main()
