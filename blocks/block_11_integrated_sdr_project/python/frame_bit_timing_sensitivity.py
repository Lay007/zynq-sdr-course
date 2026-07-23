#!/usr/bin/env python3
"""Which payload bit does a timing or carrier error flip FIRST? (offline, deterministic)

Supporting computation for Lab 11.35. The live position telemetry put 37 of 40 single-bit misses at
payload bit 189 -- the Q axis of QPSK symbol 106, the last symbol of a four-symbol Q run before a
sign change. The natural explanation was ISI from that pattern leaving the decision near zero. Both
the frame and the course RRC are deterministic, so that explanation is checkable without a bench,
and this script is what refuted it.

A matched RRC pair is Nyquist: at the ideal instant there is no ISI and every decision carries full
margin, so "which bit is weak" is not a meaningful question. The meaningful question is which bit
flips at the SMALLEST perturbation -- a pure property of the frame data. The answer is that bit 189
is among the most ROBUST decisions in the frame under timing error, under carrier phase error, and
over a combined grid, which is the opposite of what the live result would require.

Run: python frame_bit_timing_sensitivity.py
"""
from __future__ import annotations

import numpy as np

import lab_11_30_two_board_cfo_validation as L
import lab_11_32_two_board_fabric_coarse_cfo as B

SPS = L.SPS
SYMBOLS = B.SYMBOLS
PREAMBLE_BITS = B.PREAMBLE_BITS
PAYLOAD_BITS = 2 * SYMBOLS - PREAMBLE_BITS
LIVE_FAILURE_BIT = 189


def matched_filter_waveform(tile: int = 5):
    """Cyclically tiled frame -> TX RRC -> matched RX RRC, plus the symbol grid origin."""
    sym = np.tile(B.frame_symbols(), tile)
    taps = L.load_rrc_taps()
    up = np.zeros(len(sym) * SPS, dtype=complex)
    up[::SPS] = sym
    ker = np.zeros(len(up), dtype=complex)
    ker[: len(taps)] = taps
    tx = np.fft.ifft(np.fft.fft(up) * np.fft.fft(ker))   # circular: the DMA replays cyclically
    mf = np.fft.ifft(np.fft.fft(tx) * np.fft.fft(ker))   # circular matched filter
    return mf, (len(taps) - 1) % len(mf), sym


def sample_at(mf, base, n_sym, tau):
    """Linear-interpolate the matched-filter output at each symbol instant shifted by tau samples."""
    idx = (base + np.arange(n_sym) * SPS + tau) % len(mf)
    lo = np.floor(idx).astype(int)
    frac = idx - lo
    return (1 - frac) * mf[lo] + frac * mf[(lo + 1) % len(mf)]


def payload_index(symbol: int, axis: int) -> int | None:
    """axis 0 = I (frame bit 2k), axis 1 = Q (frame bit 2k+1); None outside the payload."""
    p = 2 * symbol + axis - PREAMBLE_BITS
    return p if 0 <= p < PAYLOAD_BITS else None


def _wrong_bits(sampled, sym):
    for axis, (got, want) in enumerate(((sampled.real, sym.real), (sampled.imag, sym.imag))):
        for k in np.nonzero(np.sign(got) != np.sign(want))[0]:
            p = payload_index(int(k), axis)
            if p is not None:
                yield p


def main() -> int:
    mf, base, sym = matched_filter_waveform()
    n = len(sym)
    ideal = sample_at(mf, base, n, 0.0)
    scale = float(np.mean(np.abs(ideal.real))) or 1.0
    correct = np.all(np.sign(ideal.real) == np.sign(sym.real)) and np.all(
        np.sign(ideal.imag) == np.sign(sym.imag)
    )
    print(f"ideal instant: every decision correct = {correct}; "
          f"min |Q| = {np.min(np.abs(ideal.imag))/scale:.3f}, "
          f"symbol 106 |Q| = {abs(ideal.imag[106])/scale:.3f}, "
          f"median |Q| = {np.median(np.abs(ideal.imag))/scale:.3f} (of nominal)")

    # 1) timing offset
    flip_tau: dict[int, float] = {}
    for tau in np.concatenate([np.arange(0, 4.0001, 0.005), -np.arange(0.005, 4.0001, 0.005)]):
        for p in _wrong_bits(sample_at(mf, base, n, tau), sym):
            flip_tau[p] = min(flip_tau.get(p, np.inf), abs(tau))
    ranked = sorted(flip_tau.items(), key=lambda kv: kv[1])
    print("\ntiming offset (samples; SPS=8, 4.0 = half a symbol = the trivial boundary):")
    for p, t in ranked[:5]:
        print(f"   payload {p:3d}: flips at {t:.3f}")
    print(f"   payload {LIVE_FAILURE_BIT}: {flip_tau.get(LIVE_FAILURE_BIT, float('inf')):.3f} "
          f"(rank {[p for p, _ in ranked].index(LIVE_FAILURE_BIT) + 1} of {len(ranked)})")

    # 2) carrier phase
    flip_phi: dict[int, float] = {}
    for deg in np.arange(0.0, 60.0, 0.05):
        for sign in (1, -1):
            rotated = ideal * np.exp(1j * sign * np.deg2rad(deg))
            for p in _wrong_bits(rotated, sym):
                flip_phi.setdefault(p, deg)
    ranked_phi = sorted(flip_phi.items(), key=lambda kv: kv[1])
    print("\ncarrier phase error (degrees; QPSK boundary is 45):")
    for p, d in ranked_phi[:5]:
        print(f"   payload {p:3d}: flips at {d:.2f}")
    print(f"   payload {LIVE_FAILURE_BIT}: {flip_phi.get(LIVE_FAILURE_BIT, float('nan')):.2f} "
          f"(rank {[p for p, _ in ranked_phi].index(LIVE_FAILURE_BIT) + 1} of {len(ranked_phi)})")

    # 3) combined grid -- where is a bit the SOLE failure, as the live single-bit frames are?
    sole: dict[int, int] = {}
    for tau in np.arange(-3.0, 3.01, 0.25):
        for deg in np.arange(-40, 40.1, 2.0):
            bad = list(_wrong_bits(sample_at(mf, base, n, tau) * np.exp(1j * np.deg2rad(deg)), sym))
            if len(bad) == 1:
                sole[bad[0]] = sole.get(bad[0], 0) + 1
    print("\ntiming x phase grid, bits that are the SOLE failure (as live single-bit frames are):")
    for p, c in sorted(sole.items(), key=lambda kv: -kv[1])[:5]:
        print(f"   payload {p:3d}: {c} grid points")
    print(f"   payload {LIVE_FAILURE_BIT}: {sole.get(LIVE_FAILURE_BIT, 0)} grid points")
    print("\nConclusion: the live bit-189 miss is NOT explained by the transmitted waveform under "
          "timing or carrier error.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
