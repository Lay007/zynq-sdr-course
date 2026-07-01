#!/usr/bin/env python3
"""Educational hardware figure: real BPSK spectrum + constellation + measured SNR/EVM,
captured on the Zynq-7020 + AD9361 board, comparing the on-chip PL receiver (AD9361
digital loopback) with an independent RTL-SDR over the air.

- Board side: the raw ADC samples the PL RX actually sees (`capture_in_i`), read back
  from the in-fabric debug tap during a burst (Block 11).
- RTL-SDR side: the same PL BPSK transmission received over the air, demodulated by the
  Lab 11.20 reader (which searches carrier offset, resamples and matched-filters).

Run: python hardware_bpsk_spectrum_constellation.py --board <symcap.npz> [--out <png>]
The board `.npz` holds `i`/`q` = capture_in_i/q (signed ADC counts, SPS=8).
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
RRC_MEM = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "rtl" / "bpsk_rrc_tx_fir_taps.mem"
SPS = 8


def load_rrc_taps() -> np.ndarray:
    taps = []
    for line in RRC_MEM.read_text().splitlines():
        line = line.strip()
        if line:
            v = int(line, 16)
            taps.append(v - 65536 if v >= 32768 else v)
    return np.array(taps, dtype=np.float64)


def matched_filter_symbols(rx_i: np.ndarray, rx_q: np.ndarray, taps: np.ndarray):
    """Matched-filter, pick the eye-centre phase (max mean |symbol|), return I/Q symbols."""
    mf_i = np.convolve(rx_i.astype(float), taps, mode="full")
    mf_q = np.convolve(rx_q.astype(float), taps, mode="full")
    nz = np.nonzero(np.abs(mf_i) > 0.05 * np.max(np.abs(mf_i)))[0]
    lo, hi = (nz[0], nz[-1]) if len(nz) else (0, len(mf_i) - 1)
    best_ph, best_e = 0, -1.0
    for ph in range(SPS):
        idx = np.arange(lo + ph, hi, SPS)
        e = np.mean(np.abs(mf_i[idx])) if len(idx) else 0.0
        if e > best_e:
            best_e, best_ph = e, ph
    idx = np.arange(lo + best_ph, hi, SPS)
    si, sq = mf_i[idx], mf_q[idx]
    # Drop the RRC ramp-up/down symbols at the two burst edges (near-zero, not data).
    keep = np.abs(si) > 0.35 * np.mean(np.abs(si))
    return si[keep], sq[keep]


def measure_snr_evm(sym_i: np.ndarray, sym_q: np.ndarray):
    """BPSK: ideal = A*sign(I) on the I axis. EVM from the residual, SNR = -20log10(EVM)."""
    s = sym_i / (np.std(sym_i) + 1e-12)
    a = np.mean(np.abs(s))
    ideal_i = a * np.sign(s)
    err = np.sqrt((s - ideal_i) ** 2 + (sym_q / (np.std(sym_i) + 1e-12)) ** 2)
    evm = np.sqrt(np.mean(err ** 2)) / (a + 1e-12)
    snr_db = -20.0 * np.log10(evm + 1e-12)
    return snr_db, 100.0 * evm


def power_spectrum(x: np.ndarray, fs_hz: float):
    x = x.astype(float) - np.mean(x)
    n = 1 << int(np.floor(np.log2(max(256, len(x)))))
    x = x[:n] * np.hanning(n)
    X = np.fft.fftshift(np.fft.fft(x))
    psd = 20 * np.log10(np.abs(X) / (np.max(np.abs(X)) + 1e-12) + 1e-12)
    f = np.fft.fftshift(np.fft.fftfreq(n, 1.0 / fs_hz)) / 1e3  # kHz
    return f, psd


def plot_side(ax_spec, ax_const, rx_i, rx_q, taps, fs_hz, title):
    f, psd = power_spectrum(rx_i, fs_hz)
    ax_spec.plot(f, psd, lw=0.7, color="#1f77b4")
    ax_spec.set_xlim(-fs_hz / 2e3, fs_hz / 2e3)
    ax_spec.set_ylim(-70, 3)
    ax_spec.set_xlabel("Frequency, kHz")
    ax_spec.set_ylabel("Power, dB (norm.)")
    ax_spec.set_title(f"{title} — spectrum")
    ax_spec.grid(alpha=0.3)

    si, sq = matched_filter_symbols(rx_i, rx_q, taps)
    scale = np.std(si) + 1e-12
    snr, evm = measure_snr_evm(si, sq)
    ax_const.scatter(si / scale, sq / scale, s=6, alpha=0.35, color="#d62728")
    lim = 1.0 + 3 * np.max(np.abs(sq / scale)) if np.std(sq) > 0 else 2.2
    lim = max(2.2, lim)
    ax_const.set_xlim(-lim, lim)
    ax_const.set_ylim(-lim, lim)
    ax_const.axhline(0, color="k", lw=0.4)
    ax_const.axvline(0, color="k", lw=0.4)
    ax_const.set_xlabel("In-phase (I)")
    ax_const.set_ylabel("Quadrature (Q)")
    ax_const.set_title(f"{title} — constellation\nSNR ≈ {snr:.1f} dB,  EVM ≈ {evm:.1f} %")
    ax_const.grid(alpha=0.3)
    ax_const.set_aspect("equal")
    return snr, evm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", type=Path, required=True, help="board capture .npz (i/q)")
    ap.add_argument("--board-fs-hz", type=float, default=3_840_000.0)
    ap.add_argument("--rtl-i", type=Path, default=None, help="optional RTL-SDR baseband I .npy")
    ap.add_argument("--rtl-q", type=Path, default=None)
    ap.add_argument("--rtl-fs-hz", type=float, default=3_840_000.0)
    ap.add_argument("--out", type=Path,
                    default=ROOT / "docs" / "assets" / "hw_bpsk_board_spectrum_constellation.png")
    args = ap.parse_args()
    taps = load_rrc_taps()

    d = np.load(args.board)
    have_rtl = args.rtl_i is not None and args.rtl_i.exists()
    nrows = 2 if have_rtl else 1
    fig, axes = plt.subplots(nrows, 2, figsize=(10, 4.2 * nrows))
    axes = np.atleast_2d(axes)
    b_snr, b_evm = plot_side(axes[0, 0], axes[0, 1], d["i"], d["q"], taps,
                             args.board_fs_hz, "Board PL RX (AD9361 digital loopback)")
    print(f"BOARD: SNR={b_snr:.1f} dB  EVM={b_evm:.1f} %")
    if have_rtl:
        ri = np.load(args.rtl_i); rq = np.load(args.rtl_q)
        r_snr, r_evm = plot_side(axes[1, 0], axes[1, 1], ri, rq, taps,
                                 args.rtl_fs_hz, "RTL-SDR (over the air)")
        print(f"RTL-SDR: SNR={r_snr:.1f} dB  EVM={r_evm:.1f} %")
    fig.suptitle("Real BPSK on Zynq-7020 + AD9361 — spectrum & constellation", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=130)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
