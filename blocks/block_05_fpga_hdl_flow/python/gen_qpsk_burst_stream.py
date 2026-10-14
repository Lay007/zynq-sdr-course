#!/usr/bin/env python3
"""Input vectors for tb_qpsk_listen.v (written to tmp/listen/): one Lab 11.45 frame, then silence, repeated.

This is board A's transmit buffer of two_board_burst.py: one 152-symbol long-preamble differential
frame followed by --gap frame lengths of silence, cyclic. A carrier offset, a DC offset (the
AD9361 LO leakage that the DC blocker removes) and white noise are added; the noise is present in
the gaps too, as on the board. --gap -1 writes noise and DC only (no transmitter). The file holds
--periods repetitions so the noise does not repeat within one reception. One {I,Q} 16+16-bit hex
word per sample.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "blocks" / "block_11_integrated_sdr_project" / "python"))
from two_board_burst import burst_iq  # noqa: E402

FS = 3.84e6
OUT_DIR = ROOT / "tmp" / "listen"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gap", type=int, required=True, help="silence after each frame, in frame lengths; -1 = no signal")
    ap.add_argument("--periods", type=int, default=4)
    ap.add_argument("--samples", type=int, default=0, help="file length for --gap -1")
    ap.add_argument("--peak", type=float, default=590.0, help="peak ADC counts of the frame (board B, TX -30 dB)")
    ap.add_argument("--cfo-hz", type=float, default=500.0)
    ap.add_argument("--dc", type=float, nargs=2, default=[5.0, -3.0], help="DC offset I Q in ADC counts")
    ap.add_argument("--noise-rms", type=float, default=16.0, help="board B at 71 dB: 16 counts rms")
    ap.add_argument("--seed", type=int, default=68)
    ap.add_argument("--ref", action="store_true", help="reference symbol before each frame (two_board_burst.burst_iq)")
    ap.add_argument("--name", default=None, help="output file name in tmp/listen/ (default from --gap)")
    args = ap.parse_args()

    if args.gap < 0:
        wave = np.zeros(args.samples, complex)
    else:
        iq = burst_iq(args.gap, ref=args.ref).astype(float)
        wave = np.tile((iq[0::2] + 1j * iq[1::2]) / (0.70 * 32767) * args.peak, args.periods)
    n = np.arange(wave.size)
    rng = np.random.default_rng(args.seed)
    x = wave * np.exp(2j * np.pi * args.cfo_hz / FS * n) + complex(*args.dc)
    x += args.noise_rms / np.sqrt(2) * (rng.standard_normal(n.size) + 1j * rng.standard_normal(n.size))
    i = np.clip(np.round(x.real), -2048, 2047).astype(np.int64) & 0xFFFF
    q = np.clip(np.round(x.imag), -2048, 2047).astype(np.int64) & 0xFFFF
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    name = args.name or ("qpsk_noise.mem" if args.gap < 0 else f"qpsk_burst_gap{args.gap}.mem")
    (OUT_DIR / name).write_text("".join(f"{a:04x}{b:04x}\n" for a, b in zip(i, q)), encoding="ascii")
    print(name, n.size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
