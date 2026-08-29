#!/usr/bin/env python3
"""Offline model of differential QPSK for the course modem, before any RTL.

The BER floor's residual is a whole-burst 90-degree rotation the four-branch frame sync occasionally
mis-resolves. Differential QPSK removes the ambiguity at the source: information rides the phase
DIFFERENCE between consecutive symbols, so a constant rotation of the whole burst cancels.

Phase-index convention (matches qpsk_symbol_mapper.v / qpsk_hard_decision.v):
  dibit (d0=Isign, d1=Qsign): (0,0)=+I+Q=45deg, (1,0)=-I+Q=135, (1,1)=-I-Q=225, (0,1)=+I-Q=315.
  phase index p ordered around the circle: p0=(0,0) p1=(1,0) p2=(1,1) p3=(0,1) -- Gray, so adjacent
  quadrants differ by one bit. A 90-degree CCW rotation is p -> (p+1) mod 4.

Encode (TX): info dibit -> increment dp; transmit phase p[n] = (p[n-1] + dp[n]) mod 4.
Decode (RX): hat p[n] from the hard decision; info dibit = (hat p[n] - hat p[n-1]) mod 4.

This proves: (1) clean BER=0, (2) BER=0 under ALL FOUR rotations (the whole point), (3) the
differential penalty -- one symbol error becomes two info-dibit errors.
"""
from __future__ import annotations

import numpy as np

import lab_11_32_two_board_fabric_coarse_cfo as B

# phase index <-> dibit (d0,d1)
P_TO_DIBIT = {0: (0, 0), 1: (1, 0), 2: (1, 1), 3: (0, 1)}
DIBIT_TO_P = {v: k for k, v in P_TO_DIBIT.items()}


def dibit_of_symbol(s: complex) -> tuple[int, int]:
    return (1 if s.real < 0 else 0, 1 if s.imag < 0 else 0)


def frame_info_dibits() -> list[tuple[int, int]]:
    """Use the real frame's symbols as the INFO dibit stream (what we want to convey)."""
    return [dibit_of_symbol(s) for s in B.frame_symbols()]


def diff_encode(info: list[tuple[int, int]], p0: int = 0) -> list[int]:
    """Info dibits -> transmitted phase indices (running phase accumulation)."""
    p = p0
    out = [p0]                      # a reference symbol at the start
    for d in info:
        p = (p + DIBIT_TO_P[d]) % 4
        out.append(p)
    return out


def diff_decode(phases: list[int]) -> list[tuple[int, int]]:
    """Received phase indices -> recovered info dibits (consecutive differences)."""
    return [P_TO_DIBIT[(phases[n] - phases[n - 1]) % 4] for n in range(1, len(phases))]


def biterrs(a: list[tuple[int, int]], b: list[tuple[int, int]]) -> int:
    return sum((x[0] != y[0]) + (x[1] != y[1]) for x, y in zip(a, b))


def main() -> int:
    info = frame_info_dibits()
    tx_phases = diff_encode(info)

    # (1) clean channel
    rec = diff_decode(tx_phases)
    print(f"clean: {biterrs(info, rec)} bit errors of {2*len(info)}")

    # (2) all four whole-burst rotations -- the property differential encoding buys
    print("rotation invariance:")
    for r in range(4):
        rot = [(p + r) % 4 for p in tx_phases]
        rec_r = diff_decode(rot)
        print(f"   rotate {90*r:3d} deg: {biterrs(info, rec_r)} bit errors")

    # (3) differential penalty: flip one received symbol's phase, count info-bit errors
    print("differential penalty (single received-symbol phase error):")
    penalties = []
    for k in range(1, len(tx_phases) - 1):
        corrupted = list(tx_phases)
        corrupted[k] = (corrupted[k] + 1) % 4          # a 90-degree slip on ONE symbol
        rec_k = diff_decode(corrupted)
        penalties.append(biterrs(info, rec_k))
    print(f"   one symbol wrong -> info bit errors: min {min(penalties)}, "
          f"max {max(penalties)}, mean {np.mean(penalties):.2f} "
          f"(non-differential would be 1-2 for the same slip)")

    # (4) sanity: compare error MULTIPLICATION. A rotation that is CONSTANT costs 0; a rotation that
    # CHANGES mid-burst (a real cycle slip) costs only the two symbols at the step, not the tail.
    slip = list(tx_phases)
    for k in range(len(slip) // 2, len(slip)):
        slip[k] = (slip[k] + 1) % 4                    # a 90-degree slip that persists to the end
    rec_slip = diff_decode(slip)
    print(f"mid-burst persistent 90-deg slip: {biterrs(info, rec_slip)} bit errors "
          f"(non-differential would corrupt the whole tail ~{2*(len(slip)//2)} bits)")

    # (5) the ACTUAL deployment scenario: a cyclic continuous replay (iio_writedev -c), decoded as a
    # continuous stream (each symbol vs its predecessor), with a constant whole-stream rotation. This
    # is what board B sees. It also checks that the frame WRAPS cleanly: info[0] of a copy references
    # the last symbol of the previous copy, which only decodes right if the frame's total phase
    # increment is 0 mod 4.
    incs = [DIBIT_TO_P[d] for d in info]
    per = len(info)
    print(f"\ncyclic replay: frame total phase increment = {sum(incs)} = {sum(incs) % 4} mod 4 "
          f"({'wrap-consistent' if sum(incs) % 4 == 0 else 'NOT wrap-consistent -- one bit lost at the seam'})")
    tiled = info * 5
    q, qs = 0, []
    for d in tiled:
        q = (q + DIBIT_TO_P[d]) % 4
        qs.append(q)
    for rot in (0, 1):
        prev = rot
        rec_stream = []
        for qq in qs:
            qr = (qq + rot) % 4
            rec_stream.append(P_TO_DIBIT[(qr - prev) % 4])
            prev = qr
        errs = [biterrs(tiled[k*per:(k+1)*per], rec_stream[k*per:(k+1)*per]) for k in range(5)]
        print(f"   continuous decode, whole-stream rotation {90*rot:3d} deg: "
              f"per-copy bit errors {errs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
