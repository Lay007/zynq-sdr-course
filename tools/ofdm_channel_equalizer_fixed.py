#!/usr/bin/env python3
"""Bit-exact model of ofdm_channel_equalizer.v (Block 8 OFDM, per-subcarrier channel equalization).

Training symbol: for every used natural FFT bin k the block stores
    G[k] = Y[k] * conj(sign(X[k]))
with X the known training symbol (data carriers: the train_bits() QPSK pattern,
pilots: +1, +1, +1, -1 at bins 7, 43, 57 and 21). Data symbols leave as
    Z[k] = round(Y[k] * conj(G[k]) / 2^SHIFT), saturated to Q1.15,
rounding to nearest with halves away from zero. Null and guard bins give 0.
"""

from __future__ import annotations

DEFAULT_SHIFT = 4
PILOT_SIGN = {7: 1, 43: 1, 57: 1, 21: -1}


def train_bits(data_index: int) -> tuple[int, int]:
    """(I bit, Q bit) of the training symbol on data carrier data_index (allocator order)."""
    d = data_index
    return ((d ^ (d >> 3)) & 1, ((d >> 1) ^ (d >> 2) ^ (d >> 4)) & 1)


def data_index_for_bin(natural_bin: int) -> int:
    """Same mapping as ofdm_subcarrier_allocator.v."""
    b = natural_bin
    if 1 <= b <= 6:
        return b + 23
    if 8 <= b <= 20:
        return b + 22
    if 22 <= b <= 26:
        return b + 21
    if 38 <= b <= 42:
        return b - 38
    if 44 <= b <= 56:
        return b - 39
    return b - 40


def is_null(natural_bin: int) -> bool:
    return natural_bin == 0 or 27 <= natural_bin <= 37


def train_reference(natural_bin: int) -> tuple[int, int] | None:
    """Signs (xr, xi) of the training symbol on a bin; xi = 0 on pilots; None on null bins."""
    if is_null(natural_bin):
        return None
    if natural_bin in PILOT_SIGN:
        return PILOT_SIGN[natural_bin], 0
    i_bit, q_bit = train_bits(data_index_for_bin(natural_bin))
    return (-1 if i_bit else 1), (-1 if q_bit else 1)


def estimate(natural_bin: int, y: tuple[int, int]) -> tuple[int, int]:
    """G = Y * conj(sign X) for one training bin."""
    ref = train_reference(natural_bin)
    if ref is None:
        return 0, 0
    xr, xi = ref
    yr, yi = y
    return xr * yr + xi * yi, xr * yi - xi * yr


def _round_shift(value: int, shift: int) -> int:
    half = 1 << (shift - 1)
    if value >= 0:
        return (value + half) >> shift
    return -((-value + half) >> shift)


def _saturate(value: int) -> tuple[int, bool]:
    if value > 32767:
        return 32767, True
    if value < -32768:
        return -32768, True
    return value, False


def equalize(y: tuple[int, int], g: tuple[int, int], shift: int = DEFAULT_SHIFT) -> tuple[tuple[int, int], int]:
    """Z = Y * conj(G) >> shift for one data bin; returns (Z, clipped component count)."""
    yr, yi = y
    gr, gi = g
    zr, sr = _saturate(_round_shift(yr * gr + yi * gi, shift))
    zi, si = _saturate(_round_shift(yi * gr - yr * gi, shift))
    return (zr, zi), int(sr) + int(si)


def equalize_frame(
    training: list[tuple[int, int]],
    data_symbols: list[list[tuple[int, int]]],
    shift: int = DEFAULT_SHIFT,
) -> tuple[list[list[tuple[int, int]]], list[list[int]]]:
    """Train on one 64-bin symbol, then equalize each 64-bin data symbol."""
    g = [estimate(k, training[k]) for k in range(64)]
    out: list[list[tuple[int, int]]] = []
    sats: list[list[int]] = []
    for symbol in data_symbols:
        row, row_sat = [], []
        for k in range(64):
            z, s = equalize(symbol[k], g[k], shift)
            row.append(z)
            row_sat.append(s)
        out.append(row)
        sats.append(row_sat)
    return out, sats
