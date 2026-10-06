#!/usr/bin/env python3
"""Bit-exact model of ofdm_cfo_corrector.v (Block 8 OFDM, time-domain CFO correction).

The block works on 80-sample CP16 symbols, before CP removal, and corrects each
symbol with an estimate that includes that symbol:

1. CP correlation: P_sym = sum_{n=0..15} x[n] * conj(x[n+64]). For a carrier
   offset eps (cycles/sample) x[n+64] = x[n] * exp(j*2*pi*eps*64), so
   angle(P) = -2*pi*64*eps. P is accumulated over every symbol since reset.
2. P_acc is shifted right (floor) until max(|re|, |im|) < 2^22, and a 20-step
   vectoring CORDIC gives theta = angle(P_acc), 2*pi = 2^24.
3. NCO: delta = theta * 4 per sample in a 32-bit phase (2*pi = 2^32), i.e.
   theta / 64 per sample. The phase phi runs across symbols from 0 at reset.
4. Each sample is rotated by a = phi >> 8 (2*pi = 2^24) with a 16-step rotation
   CORDIC on (re, im) << 2, then scaled by 19898 / 2^15 (1 / CORDIC gain) and
   rounded (half away from zero) back to Q1.15 with saturation.

The correction exp(j*theta*k/64) = exp(-j*2*pi*eps*k) removes the offset; the
constant phase left over is the pilot tracker's job.
"""

from __future__ import annotations

import math

SYMBOL = 80
CP = 16
FFT = 64
NORM_BITS = 22
VEC_ITERS = 20
ROT_ITERS = 16
ANGLE_BITS = 24
FRAC = 2
KINV = 19898   # round(2^15 / prod_{i<16} sqrt(1 + 2^-2i))

ATAN = [round(math.atan(2.0 ** -i) * (1 << ANGLE_BITS) / (2 * math.pi)) for i in range(VEC_ITERS)]
HALF_PI = 1 << (ANGLE_BITS - 2)


def _wrap(value: int, bits: int) -> int:
    value &= (1 << bits) - 1
    return value - (1 << bits) if value >> (bits - 1) else value


def cp_correlation(frame: list[tuple[int, int]]) -> tuple[int, int]:
    pr = pi = 0
    for n in range(CP):
        ar, ai = frame[n]
        br, bi = frame[n + FFT]
        pr += ar * br + ai * bi
        pi += ai * br - ar * bi
    return pr, pi


def vector_angle(pr: int, pi: int) -> int:
    """angle(pr + j*pi) in 2^24 units per turn, signed 24-bit."""
    m = max(abs(pr), abs(pi))
    if m == 0:
        return 0
    s = max(0, m.bit_length() - NORM_BITS)
    x, y = pr >> s, pi >> s
    z = 0
    if x < 0:
        if y >= 0:
            x, y, z = y, -x, HALF_PI
        else:
            x, y, z = -y, x, -HALF_PI
    for i in range(VEC_ITERS):
        if y >= 0:
            x, y, z = x + (y >> i), y - (x >> i), z + ATAN[i]
        else:
            x, y, z = x - (y >> i), y + (x >> i), z - ATAN[i]
    return _wrap(z, ANGLE_BITS)


def _round_shift(value: int, shift: int) -> int:
    half = 1 << (shift - 1)
    return (value + half) >> shift if value >= 0 else -((-value + half) >> shift)


def _sat16(value: int) -> int:
    return max(-32768, min(32767, value))


def rotate(sample: tuple[int, int], angle: int) -> tuple[int, int]:
    """Rotate a Q1.15 sample by angle (2^24 per turn, signed)."""
    x, y = sample[0] << FRAC, sample[1] << FRAC
    a = angle
    if a > HALF_PI:
        x, y, a = -y, x, a - HALF_PI
    elif a < -HALF_PI:
        x, y, a = y, -x, a + HALF_PI
    for i in range(ROT_ITERS):
        if a >= 0:
            x, y, a = x - (y >> i), y + (x >> i), a - ATAN[i]
        else:
            x, y, a = x + (y >> i), y - (x >> i), a + ATAN[i]
    return (_sat16(_round_shift(x * KINV, 15 + FRAC)), _sat16(_round_shift(y * KINV, 15 + FRAC)))


class CfoCorrector:
    """State across symbols: accumulated correlation and the NCO phase."""

    def __init__(self) -> None:
        self.acc = (0, 0)
        self.phase = 0
        self.theta = 0

    def correct(self, frame: list[tuple[int, int]]) -> list[tuple[int, int]]:
        assert len(frame) == SYMBOL
        pr, pi = cp_correlation(frame)
        self.acc = (self.acc[0] + pr, self.acc[1] + pi)
        self.theta = vector_angle(*self.acc)
        delta = (self.theta * 4) & 0xFFFFFFFF
        out = []
        for sample in frame:
            out.append(rotate(sample, _wrap(self.phase >> 8, ANGLE_BITS)))
            self.phase = (self.phase + delta) & 0xFFFFFFFF
        return out
