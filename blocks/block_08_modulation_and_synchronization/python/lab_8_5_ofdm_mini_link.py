#!/usr/bin/env python3
"""Lab 8.5 - OFDM mini link with synchronization and equalization."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"


@dataclass(frozen=True)
class OfdmConfig:
    fft_size: int = 64
    cp_len: int = 16
    ofdm_symbols: int = 24
    sample_rate_hz: float = 1.0e6
    cfo_hz: float = 1250.0
    snr_db: float = 20.0
    start_padding: int = 420
    seed: int = 85


@dataclass(frozen=True)
class OfdmMetrics:
    estimated_start_sample: int
    estimated_cfo_hz: float
    cfo_error_hz: float
    ber: float
    bit_errors: int
    compared_bits: int
    evm_percent: float
    evm_db: float


def k_to_idx(k: np.ndarray, nfft: int) -> np.ndarray:
    return np.mod(k, nfft).astype(np.int64)


def qpsk_from_bits(bits: np.ndarray) -> np.ndarray:
    pairs = bits.reshape(-1, 2)
    i = np.where(pairs[:, 0] == 0, 1.0, -1.0)
    q = np.where(pairs[:, 1] == 0, 1.0, -1.0)
    return (i + 1j * q) / np.sqrt(2.0)


def bits_from_qpsk(symbols: np.ndarray) -> np.ndarray:
    bits = np.empty(2 * len(symbols), dtype=np.uint8)
    bits[0::2] = np.where(np.real(symbols) >= 0, 0, 1)
    bits[1::2] = np.where(np.imag(symbols) >= 0, 0, 1)
    return bits


def add_cp(x: np.ndarray, cp_len: int) -> np.ndarray:
    return np.concatenate([x[-cp_len:], x])


def schmidl_metric(x: np.ndarray, l_half: int) -> tuple[np.ndarray, np.ndarray]:
    n = len(x) - 2 * l_half
    metric = np.zeros(max(n, 1), dtype=np.float64)
    p_vals = np.zeros(max(n, 1), dtype=np.complex128)
    if n <= 0:
        return metric, p_vals
    for d in range(n):
        a = x[d : d + l_half]
        b = x[d + l_half : d + 2 * l_half]
        p = np.sum(np.conj(a) * b)
        r = np.sum(np.abs(b) ** 2)
        p_vals[d] = p
        metric[d] = (np.abs(p) ** 2) / max(r * r, 1e-15)
    return metric, p_vals


def build_preamble(cfg: OfdmConfig, rng: np.random.Generator, used_k: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x_fd = np.zeros(cfg.fft_size, dtype=np.complex128)
    even_used = used_k[np.mod(np.abs(used_k), 2) == 0]
    bpsk = 2 * rng.integers(0, 2, size=len(even_used)) - 1
    x_fd[k_to_idx(even_used, cfg.fft_size)] = bpsk.astype(np.float64)
    x_td = np.fft.ifft(x_fd)
    return add_cp(x_td, cfg.cp_len), x_fd


def interpolate_channel(used_k: np.ndarray, x_pre_used: np.ndarray, y_pre_used: np.ndarray) -> np.ndarray:
    known = np.where(np.abs(x_pre_used) > 1e-12)[0]
    if len(known) == 0:
        return np.ones(len(used_k), dtype=np.complex128)
    h_known = y_pre_used[known] / x_pre_used[known]
    pos = np.arange(len(used_k))
    h_real = np.interp(pos, known, np.real(h_known))
    h_imag = np.interp(pos, known, np.imag(h_known))
    return h_real + 1j * h_imag


def main() -> None:
    cfg = OfdmConfig()
    rng = np.random.default_rng(cfg.seed)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    used_k = np.concatenate([np.arange(-26, 0), np.arange(1, 27)])
    pilot_k = np.array([-21, -7, 7, 21])
    data_k = np.array([k for k in used_k if k not in set(pilot_k)])
    used_idx = k_to_idx(used_k, cfg.fft_size)
    pilot_idx_local = np.array([np.where(used_k == k)[0][0] for k in pilot_k], dtype=np.int64)
    data_idx_local = np.array([np.where(used_k == k)[0][0] for k in data_k], dtype=np.int64)

    preamble_cp, preamble_fd = build_preamble(cfg, rng, used_k)

    bits_per_symbol = 2 * len(data_k)
    tx_bits = rng.integers(0, 2, size=cfg.ofdm_symbols * bits_per_symbol, dtype=np.uint8)
    tx_syms_all = qpsk_from_bits(tx_bits).reshape(cfg.ofdm_symbols, len(data_k))

    tx_wave = [np.zeros(cfg.start_padding, dtype=np.complex128), preamble_cp]
    pilot_ref = np.array([1.0, 1.0, 1.0, -1.0], dtype=np.complex128)

    for s in range(cfg.ofdm_symbols):
        x_fd = np.zeros(cfg.fft_size, dtype=np.complex128)
        x_fd[k_to_idx(pilot_k, cfg.fft_size)] = pilot_ref
        x_fd[k_to_idx(data_k, cfg.fft_size)] = tx_syms_all[s]
        tx_wave.append(add_cp(np.fft.ifft(x_fd), cfg.cp_len))
    tx = np.concatenate(tx_wave)

    taps = np.array([1.0 + 0j, 0.28 * np.exp(1j * 0.35), 0.12 * np.exp(-1j * 0.8)], dtype=np.complex128)
    delays = np.array([0, 2, 4], dtype=np.int64)
    h = np.zeros(delays[-1] + 1, dtype=np.complex128)
    h[delays] = taps
    ch = np.convolve(tx, h, mode="full")[: len(tx)]

    n = np.arange(len(ch), dtype=np.float64)
    cfo = np.exp(1j * 2.0 * np.pi * cfg.cfo_hz * n / cfg.sample_rate_hz)
    rx_noisy = ch * cfo
    sig_pow = np.mean(np.abs(rx_noisy) ** 2)
    noise_pow = sig_pow / (10.0 ** (cfg.snr_db / 10.0))
    noise = np.sqrt(noise_pow / 2.0) * (rng.standard_normal(len(ch)) + 1j * rng.standard_normal(len(ch)))
    rx = rx_noisy + noise

    l_half = cfg.fft_size // 2
    metric, p_vals = schmidl_metric(rx, l_half)
    d_peak = int(np.argmax(metric))
    start_est = max(d_peak - cfg.cp_len, 0)
    cfo_est = float(np.angle(p_vals[d_peak]) * cfg.sample_rate_hz / (2.0 * np.pi * l_half))

    n_full = np.arange(len(rx), dtype=np.float64)
    rx_cfo = rx * np.exp(-1j * 2.0 * np.pi * cfo_est * n_full / cfg.sample_rate_hz)

    pre_start = start_est + cfg.cp_len
    pre_end = pre_start + cfg.fft_size
    if pre_end > len(rx_cfo):
        raise RuntimeError("Not enough samples for preamble extraction.")
    pre_rx_fd = np.fft.fft(rx_cfo[pre_start:pre_end])

    x_pre_used = preamble_fd[used_idx]
    y_pre_used = pre_rx_fd[used_idx]
    h_used = interpolate_channel(used_k, x_pre_used, y_pre_used)

    rx_bits = []
    eq_symbols = []
    ref_symbols = []
    sym_len = cfg.fft_size + cfg.cp_len
    payload_start = start_est + len(preamble_cp)

    for s in range(cfg.ofdm_symbols):
        st = payload_start + s * sym_len + cfg.cp_len
        en = st + cfg.fft_size
        if en > len(rx_cfo):
            break
        y_fd = np.fft.fft(rx_cfo[st:en])[used_idx]
        y_eq = y_fd / np.where(np.abs(h_used) > 1e-12, h_used, 1.0 + 0j)

        pilot_phase = np.angle(np.vdot(pilot_ref, y_eq[pilot_idx_local]))
        y_eq = y_eq * np.exp(-1j * pilot_phase)

        data_eq = y_eq[data_idx_local]
        rx_bits.append(bits_from_qpsk(data_eq))
        eq_symbols.append(data_eq)
        ref_symbols.append(tx_syms_all[s])

    if not rx_bits:
        raise RuntimeError("No OFDM payload symbols decoded.")

    rx_bits_flat = np.concatenate(rx_bits)
    ref_bits_flat = tx_bits[: len(rx_bits_flat)]
    bit_errors = int(np.sum(rx_bits_flat != ref_bits_flat))
    ber = float(bit_errors / max(len(ref_bits_flat), 1))

    eq_flat = np.concatenate(eq_symbols)
    ref_flat = np.concatenate(ref_symbols)
    n_cmp = min(len(eq_flat), len(ref_flat))
    gain = np.vdot(ref_flat[:n_cmp], eq_flat[:n_cmp]) / max(np.vdot(ref_flat[:n_cmp], ref_flat[:n_cmp]), 1e-15)
    eq_aligned = eq_flat[:n_cmp] / gain
    err = eq_aligned - ref_flat[:n_cmp]
    evm_rms = np.sqrt(np.mean(np.abs(err) ** 2)) / max(np.sqrt(np.mean(np.abs(ref_flat[:n_cmp]) ** 2)), 1e-15)
    evm_percent = float(100.0 * evm_rms)
    evm_db = float(20.0 * np.log10(max(evm_rms, 1e-15)))

    metrics = OfdmMetrics(
        estimated_start_sample=start_est,
        estimated_cfo_hz=cfo_est,
        cfo_error_hz=float(cfo_est - cfg.cfo_hz),
        ber=ber,
        bit_errors=bit_errors,
        compared_bits=int(len(ref_bits_flat)),
        evm_percent=evm_percent,
        evm_db=evm_db,
    )

    metric_path = ASSET_DIR / "lab85_ofdm_sync_metric.png"
    const_path = ASSET_DIR / "lab85_ofdm_equalized_constellation.png"
    ch_path = ASSET_DIR / "lab85_ofdm_channel_estimate.png"
    metrics_path = ASSET_DIR / "lab85_ofdm_metrics.json"

    plt.figure(figsize=(7.8, 4.3))
    plt.plot(metric, linewidth=1.1)
    plt.axvline(d_peak, linestyle="--", color="tab:red", label="metric peak")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Sample index")
    plt.ylabel("Schmidl metric")
    plt.title("Lab 8.5 - OFDM coarse frame synchronization")
    plt.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(metric_path, dpi=180)
    plt.close()

    plt.figure(figsize=(5.1, 5.1))
    shown = min(3500, len(eq_aligned))
    plt.scatter(np.real(eq_aligned[:shown]), np.imag(eq_aligned[:shown]), s=5, alpha=0.45)
    plt.grid(True, alpha=0.35)
    plt.xlabel("I")
    plt.ylabel("Q")
    plt.axis("equal")
    plt.title("Lab 8.5 - Equalized OFDM data constellation")
    plt.tight_layout()
    plt.savefig(const_path, dpi=180)
    plt.close()

    plt.figure(figsize=(7.5, 4.3))
    plt.plot(used_k, 20.0 * np.log10(np.maximum(np.abs(h_used), 1e-12)))
    plt.grid(True, alpha=0.35)
    plt.xlabel("Subcarrier index")
    plt.ylabel("|H|, dB")
    plt.title("Lab 8.5 - Channel estimate from OFDM preamble")
    plt.tight_layout()
    plt.savefig(ch_path, dpi=180)
    plt.close()

    metrics_path.write_text(
        json.dumps(
            {
                "config": asdict(cfg),
                "metrics": asdict(metrics),
                "data_subcarriers": data_k.tolist(),
                "pilot_subcarriers": pilot_k.tolist(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("Lab 8.5 - OFDM mini link")
    print(f"CFO true/estimated/error: {cfg.cfo_hz:.3f} / {metrics.estimated_cfo_hz:.3f} / {metrics.cfo_error_hz:.3f} Hz")
    print(f"BER: {metrics.ber:.6e} ({metrics.bit_errors}/{metrics.compared_bits})")
    print(f"EVM: {metrics.evm_percent:.3f}% ({metrics.evm_db:.2f} dB)")
    print(f"Metrics JSON: {metrics_path}")


if __name__ == "__main__":
    main()
