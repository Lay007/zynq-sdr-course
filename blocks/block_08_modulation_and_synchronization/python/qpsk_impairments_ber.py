#!/usr/bin/env python3
"""Educational QPSK impairment study: how AWGN and a carrier frequency offset (CFO)
degrade the Gray-coded QPSK constellation, and the resulting BER-vs-Eb/N0 curve
against theory. The mapping matches the course RTL (qpsk_symbol_mapper): dibit
bit0 -> I, bit1 -> Q; bit=0 -> +, bit=1 -> -.

Generates two figures under docs/assets:
  qpsk_ber_vs_ebn0.png       - simulated Gray-QPSK BER vs theory Q(sqrt(2*Eb/N0))
  qpsk_constellation_impairments.png - constellation at clean / 10 dB / 4 dB / +CFO
"""
from __future__ import annotations
import argparse
from math import erfc, sqrt, pi
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "docs" / "assets"
RNG = np.random.default_rng(20260701)


def qpsk_gray_mod(dibits: np.ndarray) -> np.ndarray:
    """dibit[:,0] -> I, dibit[:,1] -> Q; bit 0 -> +1/sqrt2, bit 1 -> -1/sqrt2."""
    i = np.where(dibits[:, 0] == 0, 1.0, -1.0)
    q = np.where(dibits[:, 1] == 0, 1.0, -1.0)
    return (i + 1j * q) / sqrt(2.0)          # unit symbol energy


def qpsk_gray_demod(sym: np.ndarray) -> np.ndarray:
    di = (sym.real < 0).astype(int)
    dq = (sym.imag < 0).astype(int)
    return np.column_stack([di, dq])


def awgn(sym: np.ndarray, ebn0_db: float) -> np.ndarray:
    ebn0 = 10 ** (ebn0_db / 10.0)
    # Es = 1 (unit), 2 bits/symbol -> Es/N0 = 2*Eb/N0 -> N0 = 1/(2*Eb/N0)
    n0 = 1.0 / (2.0 * ebn0)
    sigma = sqrt(n0 / 2.0)                    # per I and Q component
    return sym + sigma * (RNG.standard_normal(sym.shape) + 1j * RNG.standard_normal(sym.shape))


def qfunc(x: float) -> float:
    return 0.5 * erfc(x / sqrt(2.0))


def ber_curve(n_bits: int = 400_000):
    ebn0_db = np.arange(0, 11)
    n_sym = n_bits // 2
    dibits = RNG.integers(0, 2, size=(n_sym, 2))
    tx = qpsk_gray_mod(dibits)
    sim = []
    for e in ebn0_db:
        rx = awgn(tx, float(e))
        rec = qpsk_gray_demod(rx)
        sim.append(np.mean(rec != dibits))
    theory = [qfunc(sqrt(2 * 10 ** (e / 10.0))) for e in ebn0_db]
    return ebn0_db, np.array(sim), np.array(theory)


def plot_ber(out: Path):
    ebn0, sim, theory = ber_curve()
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    ax.semilogy(ebn0, np.maximum(theory, 1e-7), "k--", label="Theory: Q(√(2·Eb/N0))")
    ax.semilogy(ebn0, np.maximum(sim, 1e-7), "o-", color="#1f77b4", label="Simulated Gray QPSK")
    ax.set_xlabel("Eb/N0, dB")
    ax.set_ylabel("Bit error rate")
    ax.set_title("Gray-coded QPSK BER vs Eb/N0 (AWGN)")
    ax.set_ylim(1e-6, 1)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=130)
    print("wrote", out, "| sim BER:", dict(zip(ebn0.tolist(), np.round(sim, 5).tolist())))


def plot_constellations(out: Path):
    n = 3000
    dibits = RNG.integers(0, 2, size=(n, 2))
    tx = qpsk_gray_mod(dibits)
    cases = [("Ideal (no noise)", tx, 0.0),
             ("AWGN, Eb/N0 = 10 dB", awgn(tx, 10.0), 0.0),
             ("AWGN, Eb/N0 = 4 dB", awgn(tx, 4.0), 0.0),
             ("Eb/N0 = 10 dB + CFO (uncorrected)", awgn(tx, 10.0), 0.02)]
    fig, axes = plt.subplots(2, 2, figsize=(8.4, 8.4))
    for ax, (title, sym, cfo) in zip(axes.flat, cases):
        s = sym
        if cfo != 0.0:
            s = sym * np.exp(1j * 2 * pi * cfo * np.arange(len(sym)))
        ax.scatter(s.real, s.imag, s=5, alpha=0.3, color="#d62728")
        ax.axhline(0, color="k", lw=0.4); ax.axvline(0, color="k", lw=0.4)
        for (px, py) in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
            ax.plot(px / sqrt(2), py / sqrt(2), "kx", ms=8, mew=2)
        ax.set_xlim(-1.8, 1.8); ax.set_ylim(-1.8, 1.8); ax.set_aspect("equal")
        ax.set_xlabel("I"); ax.set_ylabel("Q"); ax.set_title(title); ax.grid(alpha=0.3)
    fig.suptitle("Gray QPSK constellation under impairments", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(out, dpi=120)
    print("wrote", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=ASSETS)
    args = ap.parse_args()
    plot_ber(args.out_dir / "qpsk_ber_vs_ebn0.png")
    plot_constellations(args.out_dir / "qpsk_constellation_impairments.png")


if __name__ == "__main__":
    main()
