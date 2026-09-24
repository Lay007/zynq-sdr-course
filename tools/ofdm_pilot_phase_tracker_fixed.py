#!/usr/bin/env python3
"""Fixed-point pilot phase tracker reference for the Block 8 OFDM RX RTL.

Bit-exact model of ``ofdm_pilot_phase_tracker.v``. Per OFDM symbol the four
pilots from ``ofdm_subcarrier_extractor`` are combined with their real +-1
references (``pilot_ref_re`` is +32767 or -32768, only its sign is used):

    P = sum(sign(ref) * pilot)                  (exact, no multipliers)

A vectoring CORDIC measures the angle of P, and a rotation CORDIC turns it into
the correction coefficient ``W = 16384 * exp(-j * angle(P))`` in signed Q2.14,
the format ``ofdm_one_tap_equalizer`` expects. This is the fixed-point form of
Lab 8.5's ``pilot_phase = angle(vdot(pilot_ref, y[pilots]))``.

Angles are 16-bit two's-complement with pi = 2**15, so they wrap exactly like
the RTL register. All shifts are arithmetic (floor), matching Verilog ``>>>``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

ITERATIONS = 14
ANGLE_PI = 1 << 15
COEFF_ONE = 1 << 14  # Q2.14 unity

# atan(2^-i) in units of pi = 2^15, rounded to nearest.
ATAN_TABLE = tuple(round(math.atan(2.0**-i) / math.pi * ANGLE_PI) for i in range(ITERATIONS))
CORDIC_GAIN = math.prod(math.sqrt(1.0 + 2.0 ** (-2 * i)) for i in range(ITERATIONS))
# Rotation start value: the CORDIC gain brings it back to ~unity (16384).
ROTATION_X0 = round(COEFF_ONE / CORDIC_GAIN)


def wrap16(value: int) -> int:
    """Wrap to a 16-bit two's-complement angle."""
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


@dataclass(frozen=True)
class TrackerResult:
    correlation: tuple[int, int]
    phase: int  # angle(P), pi = 2^15
    coefficient: tuple[int, int]  # Q2.14, ~16384 * exp(-j * phase)
    zero_energy: bool


def accumulate(pilots: list[tuple[int, int]], refs: list[int]) -> tuple[int, int]:
    acc_re = 0
    acc_im = 0
    for (re, im), ref in zip(pilots, refs, strict=True):
        if ref >= 0:
            acc_re += re
            acc_im += im
        else:
            acc_re -= re
            acc_im -= im
    return acc_re, acc_im


def cordic_vector_angle(x: int, y: int) -> int:
    """Angle of (x, y) with pi = 2^15 (vectoring mode)."""
    z = 0
    if x < 0:  # pre-rotate by pi into the right half-plane
        x, y, z = -x, -y, -ANGLE_PI
    for i in range(ITERATIONS):
        if y >= 0:
            x, y, z = x + (y >> i), y - (x >> i), wrap16(z + ATAN_TABLE[i])
        else:
            x, y, z = x - (y >> i), y + (x >> i), wrap16(z - ATAN_TABLE[i])
    return wrap16(z)


def cordic_rotate_unit(angle: int) -> tuple[int, int]:
    """(16384 cos a, 16384 sin a) for a 16-bit angle a (rotation mode)."""
    x, y, z = ROTATION_X0, 0, wrap16(angle)
    if z > ANGLE_PI // 2 or z < -ANGLE_PI // 2:  # rotate by pi first
        x, z = -x, wrap16(z - ANGLE_PI)
    for i in range(ITERATIONS):
        if z >= 0:
            x, y, z = x - (y >> i), y + (x >> i), z - ATAN_TABLE[i]
        else:
            x, y, z = x + (y >> i), y - (x >> i), z + ATAN_TABLE[i]
    return x, y


def track_symbol(pilots: list[tuple[int, int]], refs: list[int]) -> TrackerResult:
    """Correction coefficient for one OFDM symbol's four pilots."""
    if len(pilots) != 4 or len(refs) != 4:
        raise ValueError("an OFDM symbol carries exactly four pilots")
    acc = accumulate(pilots, refs)
    if acc == (0, 0):
        return TrackerResult(acc, 0, (COEFF_ONE, 0), True)
    phase = cordic_vector_angle(*acc)
    coefficient = cordic_rotate_unit(wrap16(-phase))
    return TrackerResult(acc, phase, coefficient, False)


def angle_to_radians(angle: int) -> float:
    return angle * math.pi / ANGLE_PI
