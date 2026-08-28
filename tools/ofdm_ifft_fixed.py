#!/usr/bin/env python3
"""Fixed-point 64-point IFFT reference for the Block 8 OFDM RTL path.

The arithmetic is intentionally explicit so RTL butterflies can be compared
against the same rounding, scaling, twiddle and saturation rules.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

FFT_SIZE = 64
FFT_STAGES = 6
Q_BITS = 15
Q_SCALE = 1 << Q_BITS
Q_MIN = -(1 << Q_BITS)
Q_MAX = (1 << Q_BITS) - 1

ComplexQ15 = tuple[int, int]


@dataclass(frozen=True)
class Ifft64Result:
    """Natural-order Q1.15 IFFT output plus per-stage saturation counts."""

    samples: tuple[ComplexQ15, ...]
    stage_saturations: tuple[int, ...]

    @property
    def total_saturations(self) -> int:
        return sum(self.stage_saturations)


def _round_shift_away_from_zero(value: int, shift: int) -> int:
    """Signed round-to-nearest shift; half-LSB ties round away from zero."""
    if shift < 0:
        raise ValueError("shift must be non-negative")
    if shift == 0:
        return value
    bias = 1 << (shift - 1)
    if value >= 0:
        return (value + bias) >> shift
    return -(((-value) + bias) >> shift)


def _saturate_q15(value: int) -> tuple[int, bool]:
    if value > Q_MAX:
        return Q_MAX, True
    if value < Q_MIN:
        return Q_MIN, True
    return value, False


def quantize_q15(value: float) -> int:
    """Quantize a real scalar to signed Q1.15 with endpoint saturation."""
    scaled = value * Q_SCALE
    if scaled >= 0.0:
        rounded = math.floor(scaled + 0.5)
    else:
        rounded = -math.floor(-scaled + 0.5)
    return _saturate_q15(rounded)[0]


def q15_to_float(value: int) -> float:
    return value / Q_SCALE


def _bit_reverse(index: int) -> int:
    result = 0
    value = index
    for _ in range(FFT_STAGES):
        result = (result << 1) | (value & 1)
        value >>= 1
    return result


def _ifft_twiddle_q15(j: int, span: int) -> ComplexQ15:
    angle = 2.0 * math.pi * j / span
    return quantize_q15(math.cos(angle)), quantize_q15(math.sin(angle))


def _complex_multiply_q15_extended(a: ComplexQ15, b: ComplexQ15) -> ComplexQ15:
    """Q15 x Q15 complex multiply with widened, unclipped Q15-scaled output."""
    a_re, a_im = a
    b_re, b_im = b
    real_q30 = a_re * b_re - a_im * b_im
    imag_q30 = a_re * b_im + a_im * b_re
    return (
        _round_shift_away_from_zero(real_q30, Q_BITS),
        _round_shift_away_from_zero(imag_q30, Q_BITS),
    )


def _scaled_butterfly(a: ComplexQ15, b_twiddled: ComplexQ15) -> tuple[
    ComplexQ15,
    ComplexQ15,
    int,
]:
    """Compute (a +/- b_twiddled)/2, then saturate each Q1.15 component."""
    raw = (
        _round_shift_away_from_zero(a[0] + b_twiddled[0], 1),
        _round_shift_away_from_zero(a[1] + b_twiddled[1], 1),
        _round_shift_away_from_zero(a[0] - b_twiddled[0], 1),
        _round_shift_away_from_zero(a[1] - b_twiddled[1], 1),
    )
    clipped = [_saturate_q15(value) for value in raw]
    saturation_count = sum(1 for _, saturated in clipped if saturated)
    return (
        (clipped[0][0], clipped[1][0]),
        (clipped[2][0], clipped[3][0]),
        saturation_count,
    )


def ifft64_q15(freq_bins: Sequence[ComplexQ15]) -> Ifft64Result:
    """Run a 64-point radix-2 DIT IFFT with distributed 1/64 scaling.

    Input and output are both natural-order complex Q1.15 samples. Internally,
    natural-order input bins are copied in bit-reversed order before the six
    DIT stages. Every butterfly divides by two, so the total scale factor is
    1/64 and matches NumPy's normalized ``ifft`` convention.
    """
    if len(freq_bins) != FFT_SIZE:
        raise ValueError("ifft64_q15 requires exactly 64 frequency bins")

    work: list[ComplexQ15] = []
    for natural_index in range(FFT_SIZE):
        sample = freq_bins[_bit_reverse(natural_index)]
        if not (Q_MIN <= sample[0] <= Q_MAX and Q_MIN <= sample[1] <= Q_MAX):
            raise ValueError("input frequency bins must be signed Q1.15 integers")
        work.append((int(sample[0]), int(sample[1])))

    stage_saturations: list[int] = []
    span = 2
    while span <= FFT_SIZE:
        half = span // 2
        saturations = 0
        for base in range(0, FFT_SIZE, span):
            for j in range(half):
                upper_index = base + j
                lower_index = upper_index + half
                twiddle = _ifft_twiddle_q15(j, span)
                lower_twiddled = _complex_multiply_q15_extended(
                    work[lower_index], twiddle
                )
                upper, lower, clipped = _scaled_butterfly(
                    work[upper_index], lower_twiddled
                )
                work[upper_index] = upper
                work[lower_index] = lower
                saturations += clipped
        stage_saturations.append(saturations)
        span *= 2

    return Ifft64Result(tuple(work), tuple(stage_saturations))
