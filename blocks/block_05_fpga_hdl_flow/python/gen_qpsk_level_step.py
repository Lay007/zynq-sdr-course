#!/usr/bin/env python3
"""Input vectors for tb_qpsk_level_step.v (written to tmp/level_step/): the Lab 11.45 differential frame with a level step.

Each case is noise, then the 152-symbol long-preamble frame repeated (as board A transmits it),
with a two-level envelope: 'none' (strong throughout), 'low' (20 dB weaker throughout), 'down'
(strong until symbol --step-symbol of the first frame, then weak) and 'up' (the reverse). A small
carrier offset and white noise are added. One {I,Q} 16+16-bit hex word per sample.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "blocks" / "block_11_integrated_sdr_project" / "python"))
import lab_11_30_two_board_cfo_validation as L  # noqa: E402
import lab_11_32_two_board_fabric_coarse_cfo as B  # noqa: E402

FS = 3.84e6
OUT_DIR = ROOT / "tmp" / "level_step"


def make_case(case: str, *, peak: float, step_db: float, step_symbol: int, lead: int, n_total: int,
              cfo_hz: float, noise_rms: float, seed: int, prev: int = 0) -> np.ndarray:
    iq = B.make_long_preamble_frame(4, differential=True).astype(float)
    wave = (iq[0::2] + 1j * iq[1::2]) / (0.70 * 32767) * peak      # peak of the strong signal
    wave = np.tile(wave, int(np.ceil(n_total / len(wave))) + 1)
    delay = (len(L.load_rrc_taps()) - 1) // 2                     # RRC lag, 4 symbols
    frame = B.LONG_FRAME_SYMBOLS * L.SPS
    # prev > 0: start `prev` samples before a frame boundary, inside the preceding (strong) frame,
    # the way the board's receiver starts at a random point of board A's cyclic stream.
    sig = np.concatenate([np.zeros(lead, complex), wave[frame - prev:]])[:n_total]
    lead = lead + prev
    n = np.arange(n_total)
    step_at = lead + delay + step_symbol * L.SPS
    low = 10 ** (-step_db / 20)
    env = {"none": np.ones(n_total), "low": np.full(n_total, low),
           "down": np.where(n < step_at, 1.0, low), "up": np.where(n < step_at, low, 1.0)}[case]
    rng = np.random.default_rng(seed)
    x = sig * env * np.exp(2j * np.pi * cfo_hz / FS * n)
    x += noise_rms / np.sqrt(2) * (rng.standard_normal(n_total) + 1j * rng.standard_normal(n_total))
    return np.round(x).astype(complex)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--peak", type=float, default=400.0, help="peak ADC counts of the strong signal")
    ap.add_argument("--step-db", type=float, default=20.0)
    ap.add_argument("--step-symbol", type=int, default=60)
    ap.add_argument("--lead", type=int, default=300, help="noise samples before the first frame")
    ap.add_argument("--samples", type=int, default=6000)
    ap.add_argument("--cfo-hz", type=float, default=500.0)
    ap.add_argument("--noise-rms", type=float, default=2.0)
    ap.add_argument("--seed", type=int, default=58)
    ap.add_argument("--prev", type=int, default=0, help="samples of the preceding frame before the first full one")
    ap.add_argument("--cases", nargs="+", default=["none", "low", "down", "up"])
    args = ap.parse_args()
    for case in args.cases:
        x = make_case(case, peak=args.peak, step_db=args.step_db, step_symbol=args.step_symbol,
                      lead=args.lead, n_total=args.samples, cfo_hz=args.cfo_hz,
                      noise_rms=args.noise_rms, seed=args.seed, prev=args.prev)
        i = np.clip(x.real, -2048, 2047).astype(np.int64) & 0xFFFF
        q = np.clip(x.imag, -2048, 2047).astype(np.int64) & 0xFFFF
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUT_DIR / f"qpsk_level_step_{case}.mem"
        path.write_text("".join(f"{a:04x}{b:04x}\n" for a, b in zip(i, q)), encoding="ascii")
        print(path.name, len(x))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
