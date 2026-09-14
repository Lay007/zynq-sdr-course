#!/usr/bin/env python3
"""Fixed-point one-tap equalizer reference for the Block 8 OFDM RX RTL.

Samples use signed Q1.15. Equalizer coefficients use signed Q2.14 so the
correction coefficient can represent gain above unity. Arithmetic matches
``ofdm_one_tap_equalizer.v``: widened complex multiply, round-to-nearest with
half-LSB away from zero, then explicit Q1.15 saturation.
"""

from __future__ import annotations

from dataclasses import dataclass

Q15_MIN = -(1 << 15)
Q15_MAX = (1 << 15) - 1
Q14_COEFF_MIN = -(1 << 15)
Q14_COEFF_MAX = (1 << 15) - 1

ComplexQ15 = tuple[int, int]
ComplexQ14 = tuple[int, int]


@dataclass(frozen=True)
class EqualizerResult:
    """One equalized Q1.15 sample and the number of clipped components."""

    sample: ComplexQ15
    saturation_count: int


def _validate_pair(value: tuple[int, int], minimum: int, maximum: int) -> None:
    if not all(minimum <= component <= maximum for component in value):
        raise ValueError("fixed-point component is outside the signed 16-bit range")


def _round_shift_away_from_zero(value: int, shift: int) -> int:
    if shift <= 0:
        raise ValueError("shift must be positive")
    bias = 1 << (shift - 1)
    if value >= 0:
        return (value + bias) >> shift
    return -(((-value) + bias) >> shift)


def _saturate_q15(value: int) -> tuple[int, bool]:
    if value > Q15_MAX:
        return Q15_MAX, True
    if value < Q15_MIN:
        return Q15_MIN, True
    return value, False


def equalize_q15(sample: ComplexQ15, coefficient: ComplexQ14) -> EqualizerResult:
    """Apply one complex Q2.14 correction coefficient to a Q1.15 sample."""
    _validate_pair(sample, Q15_MIN, Q15_MAX)
    _validate_pair(coefficient, Q14_COEFF_MIN, Q14_COEFF_MAX)

    sample_re, sample_im = sample
    coeff_re, coeff_im = coefficient

    real_q29 = sample_re * coeff_re - sample_im * coeff_im
    imag_q29 = sample_re * coeff_im + sample_im * coeff_re

    real_wide = _round_shift_away_from_zero(real_q29, 14)
    imag_wide = _round_shift_away_from_zero(imag_q29, 14)
    real_q15, real_clipped = _saturate_q15(real_wide)
    imag_q15, imag_clipped = _saturate_q15(imag_wide)

    return EqualizerResult(
        sample=(real_q15, imag_q15),
        saturation_count=int(real_clipped) + int(imag_clipped),
    )
