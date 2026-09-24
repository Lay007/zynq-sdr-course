#!/usr/bin/env python3
"""QPSK carrier recovery (decision-directed Costas loop): de-rotate the CFO ring of
Lab 8.8 back into four points. Feed-forward-free streaming loop that matches the
structure of a hardware carrier-recovery block (NCO phase accumulator + PI loop +
decision-directed phase-error detector), so it ports to RTL the same way the
Gardner timing loop did.

Generates docs/assets/qpsk_carrier_recovery.png: the received CFO ring, the loop's
phase trajectory locking, the recovered constellation, and BER vs CFO with/without
the loop.
"""
from __future__ import annotations
import argparse
from math import pi, sqrt
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "docs" / "assets"
RNG = np.random.default_rng(20260701)


def qpsk_gray_mod(dibits):
    i = np.where(dibits[:, 0] == 0, 1.0, -1.0)
    q = np.where(dibits[:, 1] == 0, 1.0, -1.0)
    return (i + 1j * q) / sqrt(2.0)


def add_cfo_awgn(sym, cfo_cycles_per_sym, ebn0_db):
    n0 = 1.0 / (2.0 * 10 ** (ebn0_db / 10.0))
    noise = sqrt(n0 / 2.0) * (RNG.standard_normal(sym.shape) + 1j * RNG.standard_normal(sym.shape))
    rot = np.exp(1j * 2 * pi * cfo_cycles_per_sym * np.arange(len(sym)))
    return sym * rot + noise


def costas_qpsk(rx, kp=0.02, ki=0.002):
    """Decision-directed QPSK Costas loop. Returns de-rotated symbols and the NCO phase."""
    out = np.empty_like(rx)
    phase = np.empty(len(rx))
    theta, freq = 0.0, 0.0
    for n, s in enumerate(rx):
        y = s * np.exp(-1j * theta)          # de-rotate by NCO phase
        out[n] = y
        phase[n] = theta
        # decision-directed QPSK phase error: e = sgn(I)*Q - sgn(Q)*I
        e = np.sign(y.real) * y.imag - np.sign(y.imag) * y.real
        freq += ki * e
        theta += freq + kp * e
    return out, phase


def demod(sym):
    return np.column_stack([(sym.real < 0).astype(int), (sym.imag < 0).astype(int)])


PREAMBLE_SYMBOLS = 32


def resolve_90deg_ambiguity(y, ref_dibits, preamble_symbols=PREAMBLE_SYMBOLS):
    """A QPSK Costas loop locks to one of four k*90-deg rotations. The first
    `preamble_symbols` known symbols (the preamble / unique word) pick the rotation;
    the BER is then scored on the remaining symbols only, i.e. what a real framed
    link does. Choosing the rotation by the lowest BER over the whole frame would use
    the payload as a reference (genie alignment)."""
    pre = slice(0, preamble_symbols)
    k = min(range(4), key=lambda k: np.sum(demod(y[pre] * np.exp(-1j * pi / 2 * k)) != ref_dibits[pre]))
    rot = y[preamble_symbols:] * np.exp(-1j * pi / 2 * k)
    return rot, float(np.mean(demod(rot) != ref_dibits[preamble_symbols:]))


def acquisition_symbols(y, ref_dibits):
    """Index just after the last symbol error under the best rotation: how long the
    loop needed to pull in. A measurement against the known data, not a receiver step."""
    last = -1
    best = None
    for k in range(4):
        wrong = np.nonzero((demod(y * np.exp(-1j * pi / 2 * k)) != ref_dibits).any(axis=1))[0]
        if best is None or len(wrong) < best:
            best = len(wrong)
            last = int(wrong[-1]) if len(wrong) else -1
    return last + 1


def ber_vs_cfo(n_sym=20000, ebn0_db=12.0):
    cfos = np.linspace(0, 0.02, 11)
    dibits = RNG.integers(0, 2, size=(n_sym, 2))
    tx = qpsk_gray_mod(dibits)
    raw, rec = [], []
    for c in cfos:
        rx = add_cfo_awgn(tx, c, ebn0_db)
        raw.append(np.mean(demod(rx) != dibits))
        y, _ = costas_qpsk(rx)
        # The loop needs time to pull in, and that time grows steeply with the CFO.
        # Skip the first 1000 symbols, resolve the 90-deg ambiguity on the next
        # preamble, then measure BER over the rest.
        _, ber = resolve_90deg_ambiguity(y[1000:], dibits[1000:])
        rec.append(ber)
        print(f"CFO {c:.3f} cycles/symbol: pull-in {acquisition_symbols(y, dibits):4d} symbols, "
              f"raw BER {raw[-1]:.4f}, recovered BER {ber:.2e} over {2 * (n_sym - 1000 - PREAMBLE_SYMBOLS)} bits")
    return cfos, np.array(raw), np.array(rec)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ASSETS / "qpsk_carrier_recovery.png")
    args = ap.parse_args()

    n = 4000
    cfo = 0.01
    dibits = RNG.integers(0, 2, size=(n, 2))
    tx = qpsk_gray_mod(dibits)
    rx = add_cfo_awgn(tx, cfo, 12.0)
    y, phase = costas_qpsk(rx)
    y_locked, _ = resolve_90deg_ambiguity(y[500:], dibits[500:])

    cfos, raw, rec = ber_vs_cfo()

    fig, ax = plt.subplots(2, 2, figsize=(9.2, 8.6))
    ax[0, 0].scatter(rx.real, rx.imag, s=4, alpha=0.25, color="#d62728")
    ax[0, 0].set_title("Received: QPSK + CFO (ring)")
    ax[0, 1].scatter(y_locked.real, y_locked.imag, s=4, alpha=0.25, color="#1f77b4")
    ax[0, 1].set_title("After Costas + preamble de-rotation")
    for a in (ax[0, 0], ax[0, 1]):
        a.set_xlim(-1.6, 1.6)
        a.set_ylim(-1.6, 1.6)
        a.set_aspect("equal")
        a.axhline(0, color="k", lw=0.4)
        a.axvline(0, color="k", lw=0.4)
        a.set_xlabel("I")
        a.set_ylabel("Q")
        a.grid(alpha=0.3)

    ax[1, 0].plot(np.unwrap(phase), color="#2ca02c", lw=0.8)
    ax[1, 0].set_title("NCO phase locking onto the CFO ramp")
    ax[1, 0].set_xlabel("symbol")
    ax[1, 0].set_ylabel("phase, rad")
    ax[1, 0].grid(alpha=0.3)

    ax[1, 1].semilogy(cfos, np.maximum(raw, 1e-5), "o-", color="#d62728", label="no recovery")
    ax[1, 1].semilogy(cfos, np.maximum(rec, 1e-5), "s-", color="#1f77b4", label="Costas + preamble")
    ax[1, 1].set_title("BER vs CFO (Eb/N0 = 12 dB)")
    ax[1, 1].set_xlabel("CFO, cycles/symbol")
    ax[1, 1].set_ylabel("BER")
    ax[1, 1].set_ylim(1e-5, 1)
    ax[1, 1].grid(True, which="both", alpha=0.3)
    ax[1, 1].legend()

    fig.suptitle("QPSK carrier recovery (decision-directed Costas loop)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=120)
    _, rec_ber = resolve_90deg_ambiguity(y[500:], dibits[500:])
    print("wrote", args.out)
    print("raw BER @ CFO=0.01:", round(float(np.mean(demod(rx) != dibits)), 4),
          "| recovered:", round(float(rec_ber), 4))


if __name__ == "__main__":
    main()
