#!/usr/bin/env python3
"""Bit-exact model of ofdm_channel_equalizer.v (Block 8 OFDM, per-subcarrier channel equalization).

Training symbol: for every used natural FFT bin k the block stores
    G[k] = Y[k] * conj(sign(X[k]))
with X the known training symbol (data carriers: the train_bits() QPSK pattern,
pilots: +1, +1, +1, -1 at bins 7, 43, 57 and 21). Data symbols leave as
    Z[k] = round(Y[k] * conj(G[k]) / 2^SHIFT), saturated to Q1.15,
rounding to nearest with halves away from zero. Null and guard bins give 0.

With normalize=True (the RTL's NORMALIZE = 1) every used bin also gets
1/|G[k]|^2 from a linear-mode CORDIC division (see inverse()), and data bins
leave as round((Y * conj(G)) * z / 2^sh) = 2^14 * Y / G, saturated.
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


CORDIC_ITERS = 17


def inverse(energy: int) -> tuple[int, int]:
    """CORDIC 1/|G|^2 as the RTL computes it: (z, sh) with 2^14/energy ~ z / 2^sh.

    energy is shifted left by s so that its top bit is bit 35; then
    y = 2^35, z = 0 and for i = 0..16: y -/+= x >> i, z +/-= 2^(16-i)
    (subtract while y >= 0). z ~ 2^16 * 2^35 / (energy << s), sh = 37 - s.
    """
    if energy == 0:
        return 0, 37
    s = 35 - (energy.bit_length() - 1)
    x = energy << s
    y = 1 << 35
    z = 0
    for i in range(CORDIC_ITERS):
        if y >= 0:
            y -= x >> i
            z += 1 << (16 - i)
        else:
            y += x >> i
            z -= 1 << (16 - i)
    return z & 0x1FFFF, 37 - s


def equalize_normalized(y: tuple[int, int], g: tuple[int, int], inv: tuple[int, int]) -> tuple[tuple[int, int], int]:
    """Z = round((Y * conj(G)) * z / 2^sh), saturated: 2^14 * Y / G."""
    yr, yi = y
    gr, gi = g
    m, sh = inv
    zr, sr = _saturate(_round_shift((yr * gr + yi * gi) * m, sh))
    zi, si = _saturate(_round_shift((yi * gr - yr * gi) * m, sh))
    return (zr, zi), int(sr) + int(si)


def equalize_frame(
    training: list[tuple[int, int]],
    data_symbols: list[list[tuple[int, int]]],
    shift: int = DEFAULT_SHIFT,
    normalize: bool = False,
) -> tuple[list[list[tuple[int, int]]], list[list[int]]]:
    """Train on one 64-bin symbol, then equalize each 64-bin data symbol."""
    g = [estimate(k, training[k]) for k in range(64)]
    inv = [inverse(gr * gr + gi * gi) for gr, gi in g]
    out: list[list[tuple[int, int]]] = []
    sats: list[list[int]] = []
    for symbol in data_symbols:
        row, row_sat = [], []
        for k in range(64):
            if normalize:
                z, s = equalize_normalized(symbol[k], g[k], inv[k])
            else:
                z, s = equalize(symbol[k], g[k], shift)
            row.append(z)
            row_sat.append(s)
        out.append(row)
        sats.append(row_sat)
    return out, sats
