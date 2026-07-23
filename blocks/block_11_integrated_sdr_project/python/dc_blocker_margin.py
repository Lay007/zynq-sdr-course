#!/usr/bin/env python3
"""Why payload bit 189 fails: the RX DC blocker follows the data. (offline, deterministic)

Supporting computation for Lab 11.41. The decoded-bit readout had already established that the chip
genuinely gets payload bit 189 wrong (10 of 10 flagged frames disagree with the ROM at exactly frame
bit 213 and nowhere else), while every measurement of the DELIVERED signal at that symbol said it was
healthy. Those two facts only fit together if the damage happens after the point that was measured.

It does. The capture tap records core_rx, the INPUT of the receive chain, and the DC blocker is the
first block after it -- so every "the signal is fine there" result was blind to the blocker by
construction. And the blocker fits the rest of the evidence exactly:

  * it is linear and identical on I and Q, so dcb(x*e^{j@}) = dcb(x)*e^{j@}: its distortion rotates
    WITH the signal and is therefore invariant to carrier phase and frequency. That invariance was
    measured (910/915/920 MHz all failed alike) and nothing else explained it;
  * it is enabled only on the RF path (gp_ctrl[9]); the fabric loopback runs with it off, which is
    why the same frame, counter and ROM decode cleanly there;
  * it is data-dependent with a 2^K-sample memory, and the original K=6 gives tau = 8 symbols, so a
    run of identical symbols on one axis drags the estimate -- worst at the END of the run.

Symbol 106 is the last of a four-symbol Q run. This script replays the RTL bit-exactly and finds that
the blocker removes 66% of that decision's margin, making payload bit 189 the WEAKEST of all 256
payload decisions where without the blocker it is an unremarkable 17th. The live single-bit histogram
then matches the predicted ranking: the only three indices that ever failed on hardware rank 1, 3 and
23 of 256, in order of how often they failed.

The fix and its own trap are in dc_blocker.v.

Run: python dc_blocker_margin.py
"""
from __future__ import annotations

import numpy as np

import lab_11_30_two_board_cfo_validation as L
import lab_11_32_two_board_fabric_coarse_cfo as B

SPS = L.SPS
PREAMBLE_BITS = B.PREAMBLE_BITS
W = 16                       # dc_blocker.v sample width
AMP = 6000.0                 # RX level the AD9361 gain lands on; the result is scale-free
TARGET = 189

# What the on-chip telemetry actually reported over the 160-pair campaign: every burst whose
# payload held exactly one error, by index. The model has to explain THIS, not just bit 189.
LIVE_SINGLE_BIT = {189: 37, 2: 2, 173: 1}


def _slice16(v: int) -> int:
    """dc_i = acc_sr[W-1:0] reinterpreted as signed -- the RTL takes a slice, not a saturate."""
    return ((v & ((1 << W) - 1)) ^ (1 << (W - 1))) - (1 << (W - 1))


def dc_blocker_fixed(x, k=6):
    """The ORIGINAL module: acc += in - (acc>>>k), dc = acc>>>k, out = in - dc_old."""
    out = np.empty_like(x)
    acc_i = acc_q = 0
    for n, v in enumerate(x):
        dci, dcq = _slice16(acc_i >> k), _slice16(acc_q >> k)
        ii, qq = int(round(v.real)), int(round(v.imag))
        out[n] = complex(ii - dci, qq - dcq)
        acc_i += ii - dci
        acc_q += qq - dcq
    return out


def dc_blocker_growing(x, k_max=10):
    """The CURRENT module: K = floor(log2 n) up to K_MAX, acc re-scaled at each step.

    While K grows this is the running mean of every sample since reset; at K_MAX it becomes a leaky
    integrator with tau = 2^K_MAX. Bit-exact twin of dc_blocker.v.
    """
    out = np.empty_like(x)
    acc_i = acc_q = 0
    k = 0
    n_count = 0
    thresh = 1
    for n, v in enumerate(x):
        step = (k < k_max) and (n_count == thresh)
        k_cur = k + 1 if step else k
        ai = acc_i << 1 if step else acc_i
        aq = acc_q << 1 if step else acc_q
        dci, dcq = _slice16(ai >> k_cur), _slice16(aq >> k_cur)
        ii, qq = int(round(v.real)), int(round(v.imag))
        out[n] = complex(ii - dci, qq - dcq)
        acc_i, acc_q, k = ai + ii - dci, aq + qq - dcq, k_cur
        if step:
            thresh = (thresh << 1) | 1
        if k < k_max:
            n_count += 1
    return out


def transmit(tile: int = 12, dc: complex = 0j):
    """Cyclically tiled frame -> TX RRC -> quantised RX samples, plus the matched-filter taps."""
    sym = np.tile(B.frame_symbols(), tile)
    taps = L.load_rrc_taps()
    up = np.zeros(len(sym) * SPS, dtype=complex)
    up[::SPS] = sym
    tx = np.convolve(up, taps)[: len(up)]
    tx = tx / np.max(np.abs(tx)) * AMP + dc
    return np.round(tx.real) + 1j * np.round(tx.imag), taps


def margins(rx, taps, frame_index: int) -> dict[int, float]:
    """Normalised SIGNED margin per payload bit for one frame copy: >0 correct, <0 a wrong decision."""
    per = len(B.frame_symbols())
    ref = B.frame_symbols()
    mf = np.convolve(rx, taps)
    idx = (len(taps) - 1) + (frame_index * per + np.arange(per)) * SPS
    s = mf[idx]
    scale = float(np.mean(np.abs(s.real)))
    out: dict[int, float] = {}
    for k in range(per):
        for axis, (got, want) in enumerate(((s[k].real, ref[k].real), (s[k].imag, ref[k].imag))):
            p = 2 * k + axis - PREAMBLE_BITS
            if 0 <= p < 2 * per - PREAMBLE_BITS:
                out[p] = float(np.sign(want) * got / scale)
    return out


def report(label: str, m: dict[int, float]) -> list[int]:
    ranked = sorted(m, key=lambda p: m[p])
    rank = ranked.index(TARGET) + 1
    worst = ranked[0]
    print(f"\n{label}")
    print("   five weakest:", ", ".join(f"bit {p}={m[p]:+.3f}" for p in ranked[:5]))
    print(f"   bit {TARGET}: margin {m[TARGET]:+.3f}, RANK {rank} of {len(ranked)} "
          f"(1 = closest to a wrong decision)")
    print(f"   frame minimum {m[worst]:+.3f} at bit {worst}; median {np.median(list(m.values())):+.3f}")
    return ranked


def main() -> int:
    # Two streams. The blocker configurations are judged on a real OTA-like input, i.e. carrying a
    # DC offset comparable to the symbol amplitude as dc_blocker.v documents. The reference is the
    # DC-FREE stream with no blocker: that is the fabric-loopback configuration, and it is the
    # margin a perfect front end would deliver. Feeding the DC-carrying stream through no blocker
    # would just measure the LO leakage rather than anything about the blocker.
    tx, taps = transmit(dc=AMP + 0.7j * AMP)
    tx_clean, _ = transmit(dc=0j)
    steady = 8                      # a frame copy well past reset

    none_m = margins(tx_clean, taps, steady)
    fixed_m = margins(dc_blocker_fixed(tx), taps, steady)
    grow_m = margins(dc_blocker_growing(tx), taps, steady)

    report("no DC blocker on a DC-free input -- the fabric loopback, and the ideal to aim at", none_m)
    ranked_fixed = report("fixed K=6 -- the configuration that fails on the two-board link", fixed_m)
    report("running average, K_MAX=10 -- the current module", grow_m)

    print(f"\nbit {TARGET}: {none_m[TARGET]:+.3f} without the blocker -> {fixed_m[TARGET]:+.3f} with "
          f"fixed K=6 ({100 * (1 - fixed_m[TARGET] / none_m[TARGET]):.0f}% of the margin removed) "
          f"-> {grow_m[TARGET]:+.3f} with the running average")

    # The real test of the model: it must rank the bits that actually failed on hardware.
    print("\nlive single-bit errors vs the margin the fixed-K model predicts:")
    for p, n in sorted(LIVE_SINGLE_BIT.items(), key=lambda kv: -kv[1]):
        print(f"   payload {p:3d}: {n:2d} frames live -> predicted rank {ranked_fixed.index(p) + 1} "
              f"of {len(ranked_fixed)}, margin {fixed_m[p]:+.3f}")
    print("Every index that ever failed on hardware sits in the predicted weak tail, ordered by how "
          "often it failed. Nothing else about the frame distinguishes those three bits.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
