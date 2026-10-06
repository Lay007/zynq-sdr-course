#!/usr/bin/env python3
"""Generate shared test vectors for ofdm_cfo_corrector.v.

One line per sample, in decimal:

    stream frame sample in_re in_im exp_re exp_im

Each stream starts from reset (the testbench resets the block between streams)
and holds consecutive 80-sample CP16 symbols. Expected samples come from the
bit-exact model in tools/ofdm_cfo_corrector_fixed.py; pytest checks that the
committed file matches the model.
"""

from __future__ import annotations

import argparse
import cmath
import math
import random
from pathlib import Path

from tools.ofdm_cfo_corrector_fixed import CfoCorrector

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "verification" / "vectors" / "block08_ofdm_cfo_vectors.txt"


def _clip16(value: float) -> int:
    return max(-32768, min(32767, round(value)))


def ofdm_frames(rng: random.Random, count: int, cfo: float, amplitude: float, start_phase: float):
    """CP16 OFDM symbols with random QPSK on the 52 used carriers, carrier offset cfo."""
    frames = []
    n = 0
    for _ in range(count):
        bins = [0j] * 64
        for k in list(range(1, 27)) + list(range(38, 64)):
            bins[k] = complex(rng.choice((-1, 1)), rng.choice((-1, 1)))
        time = [sum(bins[k] * cmath.exp(2j * math.pi * k * t / 64) for k in range(64)) / 64 for t in range(64)]
        symbol = time[48:] + time
        frame = []
        for x in symbol:
            y = x * amplitude * cmath.exp(1j * (start_phase + 2 * math.pi * cfo * n))
            frame.append((_clip16(y.real), _clip16(y.imag)))
            n += 1
        frames.append(frame)
    return frames


def build_streams():
    rng = random.Random(4808)
    streams = [
        ofdm_frames(rng, 4, 0.004, 20000.0, 0.3),          # 0.256 subcarrier spacings
        ofdm_frames(rng, 3, -0.006, 12000.0, -2.0),        # 0.384 spacings, negative
        ofdm_frames(rng, 3, 0.0075, 25000.0, 1.0),         # 0.48 spacings, near the limit
        ofdm_frames(rng, 2, 0.0, 15000.0, 0.0),            # no offset
        [[(0, 0)] * 80, [(0, 0)] * 80],                    # zero energy: theta stays 0
        [[(rng.choice((-32768, 32767, -30000, 30000)), rng.choice((-32768, 32767, 29000, -29000)))
          for _ in range(80)] for _ in range(2)],          # full scale: rotation saturates
    ]
    return streams


def render(streams) -> str:
    lines = []
    for s, frames in enumerate(streams):
        model = CfoCorrector()
        for f, frame in enumerate(frames):
            out = model.correct(frame)
            for k, ((xr, xi), (yr, yi)) in enumerate(zip(frame, out, strict=True)):
                lines.append(f"{s} {f} {k} {xr} {xi} {yr} {yi}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(build_streams()), encoding="utf-8", newline="\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
