#!/usr/bin/env python3
"""Bit-exact model of ofdm_qam16_mapper.v and ofdm_qam16_demapper.v (Block 8 OFDM, Gray 16-QAM).

Four bits per carrier: bits[3:2] -> I, bits[1:0] -> Q. Per axis the first bit is
the sign (0 -> positive) and the second the magnitude (0 -> outer 3/sqrt(10),
1 -> inner 1/sqrt(10)): 00 -> +3, 01 -> +1, 11 -> -1, 10 -> -3.

The slicer threshold follows from the chain: the 16-QAM training symbol uses the
outer points, so the zero-forcing equalizer maps the outer level to 2^14 / 2 and
the inner level to a third of that; halfway between is 2^14 / 3.
"""

from __future__ import annotations

LEVEL_INNER = 10362   # round(32767 / sqrt(10))
LEVEL_OUTER = 31086   # round(3 * 32767 / sqrt(10))
THRESHOLD = (1 << 14) // 3   # 5461


def axis_level(sign_bit: int, inner_bit: int) -> int:
    magnitude = LEVEL_INNER if inner_bit else LEVEL_OUTER
    return -magnitude if sign_bit else magnitude


def map_bits(bits: int) -> tuple[int, int]:
    """4-bit value -> (I, Q) in Q1.15."""
    return axis_level((bits >> 3) & 1, (bits >> 2) & 1), axis_level((bits >> 1) & 1, bits & 1)


def slice_axis(value: int, threshold: int = THRESHOLD) -> tuple[int, int]:
    return int(value < 0), int(-threshold < value < threshold)


def demap(re: int, im: int, threshold: int = THRESHOLD) -> int:
    """(I, Q) after the zero-forcing equalizer -> 4-bit value."""
    s_i, n_i = slice_axis(re, threshold)
    s_q, n_q = slice_axis(im, threshold)
    return (s_i << 3) | (n_i << 2) | (s_q << 1) | n_q


def training_bits(i_bit: int, q_bit: int) -> int:
    """16-QAM training carrier: the QPSK training signs on the outer points."""
    return (i_bit << 3) | (q_bit << 1)
