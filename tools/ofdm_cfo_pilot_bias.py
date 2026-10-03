#!/usr/bin/env python3
"""Float model of the Block 8 OFDM pilot phase estimate under a carrier frequency offset.

Builds the same OFDM symbols as tb_ofdm_tx_rx_pilot_corrected_loopback.sv (Lab 8.5
subcarrier layout, pilots +1, +1, +1, -1 at k = -21, -7, +7, +21, the testbench's
data pattern), rotates them by angle + 2*pi*CFO*n and forms the tracker's pilot sum
P = sum(sign(pilot_ref) * Y[k]) on the last symbol. It prints the phase of P next to
the mean channel phase over that symbol's 64 useful samples.

The difference is not noise: with a CFO the subcarriers are no longer orthogonal
and the data carriers leak into the pilot bins (inter-carrier interference). With
the data carriers left empty the difference is zero.

Phases are in the tracker's units, pi = 2^15.
"""

from __future__ import annotations

import argparse

import numpy as np

N_FFT = 64
N_CP = 16
SYMBOL_SAMPLES = N_FFT + N_CP
PILOT_REF = {43: 1.0, 57: 1.0, 7: 1.0, 21: -1.0}   # natural FFT bin -> reference
NULL_BINS = {0, *range(27, 38)}
UNITS_PER_RAD = 32768.0 / np.pi


def data_index_for_bin(natural_bin: int) -> int:
    """Same mapping as ofdm_subcarrier_allocator.v."""
    if 1 <= natural_bin <= 6:
        return natural_bin + 23
    if 8 <= natural_bin <= 20:
        return natural_bin + 22
    if 22 <= natural_bin <= 26:
        return natural_bin + 21
    if 38 <= natural_bin <= 42:
        return natural_bin - 38
    if 44 <= natural_bin <= 56:
        return natural_bin - 39
    return natural_bin - 40


def testbench_bits(pair_index: int) -> tuple[int, int]:
    """The testbench's (I bit, Q bit) for data pair pair_index."""
    i_bit = pair_index & 1
    q_bit = ((pair_index >> 1) ^ pair_index ^ (pair_index >> 6)) & 1
    return i_bit, q_bit


def ofdm_symbol(symbol: int, with_data: bool = True) -> np.ndarray:
    bins = np.zeros(N_FFT, complex)
    for b in range(N_FFT):
        if b in PILOT_REF:
            bins[b] = PILOT_REF[b]
        elif b in NULL_BINS or not with_data:
            continue
        else:
            i_bit, q_bit = testbench_bits(symbol * 48 + data_index_for_bin(b))
            bins[b] = ((-1.0 if i_bit else 1.0) + 1j * (-1.0 if q_bit else 1.0)) / np.sqrt(2.0)
    x = np.fft.ifft(bins)
    return np.concatenate([x[N_FFT - N_CP:], x])


def wrap_units(rad: float) -> float:
    return float(np.angle(np.exp(1j * rad)) * UNITS_PER_RAD)


def pilot_phase(angle_deg: float, cfo_ppm: float, symbols: int, with_data: bool = True) -> dict[str, float]:
    """Pilot estimate and mean channel phase of the last symbol, in units (pi = 2^15)."""
    tx = np.concatenate([ofdm_symbol(s, with_data) for s in range(symbols)])
    n = np.arange(tx.size)
    cfo = cfo_ppm * 1e-6
    rx = tx * np.exp(1j * (np.deg2rad(angle_deg) + 2 * np.pi * cfo * n))
    start = SYMBOL_SAMPLES * (symbols - 1) + N_CP
    spectrum = np.fft.fft(rx[start:start + N_FFT])
    pilot_sum = sum(np.sign(ref) * spectrum[b] for b, ref in PILOT_REF.items())
    estimate = float(np.angle(pilot_sum))
    mean_phase = np.deg2rad(angle_deg) + 2 * np.pi * cfo * (start + (N_FFT - 1) / 2)
    return {
        "estimate": wrap_units(estimate),
        "mean_phase": wrap_units(mean_phase),
        "bias": wrap_units(estimate - mean_phase),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--angle-deg", type=float, default=30.0)
    parser.add_argument("--symbols", type=int, default=8)
    parser.add_argument("--ppm", type=float, nargs="+", default=[0, 500, 1000, 2000, 4000, 8000])
    args = parser.parse_args()

    print(f"angle {args.angle_deg} deg, {args.symbols} symbols, last symbol measured (pi = 2^15 units)")
    print("   CFO ppm   mean phase   pilot estimate   bias (units, deg)   bias with pilots only")
    for ppm in args.ppm:
        r = pilot_phase(args.angle_deg, ppm, args.symbols)
        r0 = pilot_phase(args.angle_deg, ppm, args.symbols, with_data=False)
        print(f"{ppm:10.0f} {r['mean_phase']:12.1f} {r['estimate']:16.1f} "
              f"{r['bias']:9.1f} {r['bias'] / UNITS_PER_RAD * 180 / np.pi:7.2f} {r0['bias']:21.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
