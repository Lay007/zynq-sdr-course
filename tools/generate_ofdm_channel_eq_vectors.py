#!/usr/bin/env python3
"""Generate shared test vectors for ofdm_channel_equalizer.v.

The file holds frames; each frame is one training symbol followed by data
symbols, 64 natural-order bins per symbol, one bin per line, in decimal:

    frame symbol bin y_re y_im exp_re exp_im exp_sat

symbol 0 is the training symbol (exp_* are 0 and not checked). A second file,
block08_ofdm_channel_eq_norm_vectors.txt, holds the same frames with the
expected outputs of the NORMALIZE = 1 (zero-forcing, CORDIC 1/|G|^2) mode. Expected values
come from the bit-exact model in tools/ofdm_channel_equalizer_fixed.py. The
Verilog testbench resets the block before every frame. pytest checks that the
committed file matches the model.

Bins are built as the chain delivers them: X/64 (both transforms are scaled by
1/N), times a per-frame channel, plus optional noise, rounded to integers.
"""

from __future__ import annotations

import argparse
import cmath
import math
import random
from pathlib import Path

from tools.ofdm_channel_equalizer_fixed import (
    data_index_for_bin,
    equalize_frame,
    is_null,
    train_reference,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "verification" / "vectors" / "block08_ofdm_channel_eq_vectors.txt"
NORMALIZED_OUT = ROOT / "verification" / "vectors" / "block08_ofdm_channel_eq_norm_vectors.txt"
QPSK = 23170
PILOT = 32767
SCALE = 1.0 / 64.0


def _clip16(value: float) -> int:
    return max(-32768, min(32767, round(value)))


def _symbol_values(bits_for_data) -> list[complex]:
    """Transmitted 64-bin symbol (natural order) for a data-bit function."""
    values = []
    for k in range(64):
        if is_null(k):
            values.append(0j)
        elif k in (7, 21, 43, 57):
            values.append(complex(train_reference(k)[0] * PILOT, 0))
        else:
            i_bit, q_bit = bits_for_data(data_index_for_bin(k))
            values.append(complex(-QPSK if i_bit else QPSK, -QPSK if q_bit else QPSK))
    return values


def _training_values() -> list[complex]:
    out = []
    for k in range(64):
        ref = train_reference(k)
        if ref is None:
            out.append(0j)
        elif k in (7, 21, 43, 57):
            out.append(complex(ref[0] * PILOT, 0))
        else:
            out.append(complex(ref[0] * QPSK, ref[1] * QPSK))
    return out


def _channel(taps: list[tuple[float, float, int]]):
    def response(k: int) -> complex:
        return sum(a * cmath.exp(1j * phi) * cmath.exp(-2j * math.pi * k * d / 64) for a, phi, d in taps)
    return response


def _receive(values: list[complex], response, gain: float, noise: float, rng: random.Random) -> list[tuple[int, int]]:
    bins = []
    for k, x in enumerate(values):
        y = x * SCALE * gain * response(k)
        if noise:
            y += complex(rng.gauss(0, noise), rng.gauss(0, noise))
        bins.append((_clip16(y.real), _clip16(y.imag)))
    return bins


def build_frames() -> list[tuple[list[tuple[int, int]], list[list[tuple[int, int]]]]]:
    rng = random.Random(4848)
    flat = _channel([(1.0, 0.0, 0)])
    lab85 = _channel([(1.0, 0.0, 0), (0.28, 0.35, 2), (0.12, -0.8, 4)])
    strong = _channel([(0.5, 0.0, 0), (0.25, 1.2, 3), (0.15, -2.0, 7)])
    fade = _channel([(0.5, 0.0, 0), (0.48, math.pi, 1)])
    cases = [
        (flat, 1.0, 0.0),            # identity channel
        (lab85, 1.0, 0.0),           # Lab 8.5 multipath
        (strong, 1.0, 2.0),          # strong multipath with noise
        (fade, 1.0, 0.0),            # near-null around DC (deep fade)
        (flat, 2.0, 0.0),            # |H|^2 = 4: equalizer saturation
        (lab85, 60.0, 0.0),          # bins near Q1.15 full scale
        (flat, 0.1, 0.0, 3.0),       # channel 3x stronger after training: zero-forcing saturates
    ]
    frames = []
    for response, gain, noise, *data_gain in cases:
        training = _receive(_training_values(), response, gain, noise, rng)
        data_scale = gain * data_gain[0] if data_gain else gain
        data = []
        for _ in range(2):
            bits = {d: (rng.randrange(2), rng.randrange(2)) for d in range(48)}
            data.append(_receive(_symbol_values(lambda d, b=bits: b[d]), response, data_scale, noise, rng))
        frames.append((training, data))
    return frames


def render(frames, normalize: bool = False) -> str:
    lines = []
    for f, (training, data) in enumerate(frames):
        for k, (yr, yi) in enumerate(training):
            lines.append(f"{f} 0 {k} {yr} {yi} 0 0 0")
        outputs, sats = equalize_frame(training, data, normalize=normalize)
        for s, symbol in enumerate(data, start=1):
            for k, (yr, yi) in enumerate(symbol):
                zr, zi = outputs[s - 1][k]
                lines.append(f"{f} {s} {k} {yr} {yi} {zr} {zi} {sats[s - 1][k]}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--normalized-out", type=Path, default=NORMALIZED_OUT)
    args = parser.parse_args()
    frames = build_frames()
    for path, normalize in ((args.out, False), (args.normalized_out, True)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render(frames, normalize), encoding="utf-8", newline="\n")
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
