#!/usr/bin/env python3
"""Bit-exact reference for the educational SF7 CSS detector (issue #46).

This module is the single source of truth for the fixed-point contract that the
RTL in ``blocks/block_05_fpga_hdl_flow/rtl/css_*.v`` must reproduce sample-for-
sample. It carries three layers:

* a floating-point CSS detector (the same maths as Lab 8.21), used only to prove
  the fixed-point path recovers the correct symbol-to-bin permutation;
* fixed-point coefficient tables (conjugate reference chirp and the shared
  twiddle table), quantised to Q1.15;
* an integer pipeline (``dechirp_fixed`` + ``dft_peak_fixed``) written with the
  exact truncating shifts, Q1.15 saturation and strict peak/second-peak comparator
  used by the Block 8 Verilog.

This is deliberately an educational SF7 baseline with one complex DFT MAC per
cycle. The production-oriented SF5..SF12 two-FFT correlator, packet PHY and ToA
path live in the companion ``zynq-lora-phy-positioning`` repository.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# ---- Fixed format -----------------------------------------------------------
SF = 7
N = 1 << SF  # 128 chips / FFT bins per symbol
SCALE = 32767  # Q1.15 unit magnitude
SHIFT = 15  # arithmetic right shift after every Q1.15 multiply
SAMPLE_AMP = 10000  # test-symbol amplitude, leaves S16 headroom
IQ_W = 16  # input / coefficient / dechirp word width (signed)


def _sat(value: int, width: int) -> int:
    lo = -(1 << (width - 1))
    hi = (1 << (width - 1)) - 1
    return max(lo, min(hi, value))


# ---- Chirp / twiddle maths --------------------------------------------------
def upchirp_phase_cycles(n_index: int) -> float:
    """Phase (in cycles) of the SF7 base up-chirp at chip ``n_index``."""
    return 0.5 * n_index * n_index / N - 0.5 * n_index


def conj_reference_fixed() -> tuple[list[int], list[int]]:
    """Q1.15 conjugate of the reference up-chirp, one entry per chip."""
    ref_i, ref_q = [], []
    for n_index in range(N):
        ang = 2.0 * math.pi * upchirp_phase_cycles(n_index)
        ref_i.append(_sat(round(math.cos(ang) * SCALE), IQ_W))
        ref_q.append(_sat(round(-math.sin(ang) * SCALE), IQ_W))
    return ref_i, ref_q


def twiddle_fixed() -> tuple[list[int], list[int]]:
    """Q1.15 table W[m] = exp(-j 2 pi m / N); DFT bin (k,n) reads index (k*n) mod N."""
    tw_i, tw_q = [], []
    for m_index in range(N):
        ang = 2.0 * math.pi * m_index / N
        tw_i.append(_sat(round(math.cos(ang) * SCALE), IQ_W))
        tw_q.append(_sat(round(-math.sin(ang) * SCALE), IQ_W))
    return tw_i, tw_q


def symbol_samples_fixed(
    symbol: int, amp: int = SAMPLE_AMP, cfo_bins: float = 0.0
) -> tuple[list[int], list[int]]:
    """Fixed-point RX samples for a transmitted CSS ``symbol`` (SF7).

    ``symbol`` selects the cyclic shift of the base up-chirp; ``cfo_bins`` adds a
    fractional carrier offset in FFT-bin units for the impaired vector tests.
    """
    rx_i, rx_q = [], []
    for n_index in range(N):
        shifted = (n_index + symbol) % N
        ang = 2.0 * math.pi * upchirp_phase_cycles(shifted)
        ang += 2.0 * math.pi * cfo_bins * n_index / N
        rx_i.append(_sat(round(math.cos(ang) * amp), IQ_W))
        rx_q.append(_sat(round(math.sin(ang) * amp), IQ_W))
    return rx_i, rx_q


# ---- Fixed-point pipeline (mirrors the RTL exactly) -------------------------
def dechirp_fixed(
    rx_i: list[int],
    rx_q: list[int],
    ref_i: list[int],
    ref_q: list[int],
) -> tuple[list[int], list[int], int]:
    """Complex multiply, truncate to Q1.15, saturate, and count overflows."""
    d_i, d_q = [], []
    overflow_count = 0
    for n_index in range(N):
        pi = (rx_i[n_index] * ref_i[n_index] - rx_q[n_index] * ref_q[n_index]) >> SHIFT
        pq = (rx_i[n_index] * ref_q[n_index] + rx_q[n_index] * ref_i[n_index]) >> SHIFT
        sat_i = _sat(pi, IQ_W)
        sat_q = _sat(pq, IQ_W)
        overflow_count += int(sat_i != pi or sat_q != pq)
        d_i.append(sat_i)
        d_q.append(sat_q)
    return d_i, d_q, overflow_count


@dataclass(frozen=True)
class PeakResult:
    peak_bin: int
    second_bin: int
    peak_mag2: int
    second_mag2: int
    overflow_count: int = 0


@dataclass(frozen=True)
class DftBin:
    index: int
    value_i: int
    value_q: int
    magnitude_squared: int


def dft_bins_fixed(
    d_i: list[int],
    d_q: list[int],
    tw_i: list[int],
    tw_q: list[int],
) -> list[DftBin]:
    """Return every sequential fixed-point DFT bin produced by the RTL core."""
    bins = []
    for k in range(N):
        acc_i = 0
        acc_q = 0
        for n_index in range(N):
            idx = (k * n_index) % N
            acc_i += (d_i[n_index] * tw_i[idx] - d_q[n_index] * tw_q[idx]) >> SHIFT
            acc_q += (d_i[n_index] * tw_q[idx] + d_q[n_index] * tw_i[idx]) >> SHIFT
        bins.append(DftBin(k, acc_i, acc_q, acc_i * acc_i + acc_q * acc_q))
    return bins


def dft_peak_fixed(
    d_i: list[int],
    d_q: list[int],
    tw_i: list[int],
    tw_q: list[int],
) -> PeakResult:
    """Sequential N-point DFT magnitude with a streaming peak/second-peak search.

    The per-MAC ``>> 15`` and the strict ``>`` comparator (first occurrence wins)
    match the Verilog byte-for-byte, so RTL and reference never disagree.
    """
    peak_mag2, peak_bin = -1, 0
    second_mag2, second_bin = -1, 0
    for dft_bin in dft_bins_fixed(d_i, d_q, tw_i, tw_q):
        if dft_bin.magnitude_squared > peak_mag2:
            second_mag2, second_bin = peak_mag2, peak_bin
            peak_mag2, peak_bin = dft_bin.magnitude_squared, dft_bin.index
        elif dft_bin.magnitude_squared > second_mag2:
            second_mag2, second_bin = dft_bin.magnitude_squared, dft_bin.index
    return PeakResult(peak_bin, second_bin, peak_mag2, max(second_mag2, 0))


def detect_fixed(
    rx_i: list[int],
    rx_q: list[int],
    ref_i: list[int],
    ref_q: list[int],
    tw_i: list[int],
    tw_q: list[int],
) -> PeakResult:
    d_i, d_q, overflow_count = dechirp_fixed(rx_i, rx_q, ref_i, ref_q)
    result = dft_peak_fixed(d_i, d_q, tw_i, tw_q)
    return PeakResult(
        result.peak_bin,
        result.second_bin,
        result.peak_mag2,
        result.second_mag2,
        overflow_count,
    )


# ---- Floating-point cross-check --------------------------------------------
def detect_peak_float(symbol: int, cfo_bins: float = 0.0) -> int:
    """Ideal FFT peak bin, used only to validate the fixed-point permutation."""
    n_index = [i for i in range(N)]
    ref = [
        complex(math.cos(2 * math.pi * upchirp_phase_cycles(i)), math.sin(2 * math.pi * upchirp_phase_cycles(i)))
        for i in n_index
    ]
    rx = []
    for i in n_index:
        ang = 2 * math.pi * upchirp_phase_cycles((i + symbol) % N)
        ang += 2 * math.pi * cfo_bins * i / N
        rx.append(complex(math.cos(ang), math.sin(ang)))
    dech = [rx[i] * ref[i].conjugate() for i in n_index]
    mags = []
    for k in range(N):
        acc = 0j
        for i in n_index:
            acc += dech[i] * complex(math.cos(-2 * math.pi * k * i / N), math.sin(-2 * math.pi * k * i / N))
        mags.append(abs(acc))
    return max(range(N), key=lambda k: mags[k])


def symbol_to_bin_permutation() -> list[int]:
    """Fixed-point peak bin for each transmitted noiseless symbol (a permutation)."""
    ref_i, ref_q = conj_reference_fixed()
    tw_i, tw_q = twiddle_fixed()
    bins = []
    for symbol in range(N):
        rx_i, rx_q = symbol_samples_fixed(symbol)
        bins.append(detect_fixed(rx_i, rx_q, ref_i, ref_q, tw_i, tw_q).peak_bin)
    return bins
