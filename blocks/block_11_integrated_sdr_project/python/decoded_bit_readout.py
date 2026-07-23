#!/usr/bin/env python3
"""Read board B's decoded-bit register (gp_ctrl[16]) and align it to the frame ROM.

The bridge shifts every recovered dibit into a 288-bit register that freezes when the burst
completes. Bits arrive I-then-Q per symbol and shift up, so SYMBOL order is reversed while I stays
in the lower bit of each pair: frame bit i (symbol s = i>>1, axis = i&1) sits at
2*((SYMS-1-s) + soff) + axis, where soff counts symbols captured after the frame's last one.
"""

import lab_11_32_two_board_fabric_coarse_cfo as B

BASE = 0x79040000
A_OFF = f"0x{BASE + 0x4C4:X}"
A_CAP = f"0x{BASE + 0x5C8:X}"
A_CTRL = f"0x{BASE + 0x404:X}"
BITS_READ_BIT = 0x1_0000          # gp_ctrl[16]
SYMS = B.SYMBOLS                  # 140
FRAME_BITS = 2 * SYMS             # 280


def frame_rom() -> list[int]:
    toks = [t for t in (B.FRAME_MEM).read_text().split() if t.strip() in ("0", "1")]
    return [int(t) for t in toks[:FRAME_BITS]]


def read_decoded(runner, hold_mode: int) -> tuple[int, int]:
    """Return (288-bit integer, bit count). Read only after the burst is done."""
    cmd = "; ".join(f"/sbin/devmem {A_OFF} 32 {a}; /sbin/devmem {A_CAP} 32" for a in range(10))
    runner(f"/sbin/devmem {A_CTRL} 32 0x{(hold_mode | BITS_READ_BIT):X}")
    rc, out, err = runner(cmd)
    runner(f"/sbin/devmem {A_CTRL} 32 0x{hold_mode:X}")
    words = [int(w, 16) for w in out.split() if w.startswith("0x")]
    if len(words) < 10:
        raise RuntimeError(f"short readout: {len(words)} words")
    value = 0
    for i in range(9):
        value |= words[i] << (32 * i)
    return value, words[9] & 0x3FF


# The QPSK BER counter does NOT compare the raw dibits to the ROM. It runs two frame-sync branches
# -- A emits {d0, d1}, B emits the 90-degree de-rotation {d1, ~d0} -- and each resolves its own
# 180-degree ambiguity with an invert flag, so four rotations are possible. The readout captures the
# RAW dibits, so a comparison must try all four; using only the identity makes a rotated burst look
# like ~half the frame is wrong, which is exactly the 121-129 mismatch signature seen on the bench.
ROTATIONS = {
    "A":        lambda i, q: (i, q),
    "A+invert": lambda i, q: (i ^ 1, q ^ 1),
    "B(90)":    lambda i, q: (q, i ^ 1),
    "B+invert": lambda i, q: (q ^ 1, i),
}


def align_to_rom(value: int, count: int, rom: list[int], max_soff: int = 8):
    """Best (rotation, symbol offset) and the frame bits where the decoder disagrees with the ROM."""
    best = None
    for rot_name, rot in ROTATIONS.items():
        for soff in range(max_soff + 1):
            bad = []
            broke = False
            for s in range(SYMS):
                base = 2 * ((SYMS - 1 - s) + soff)
                if base + 1 >= 288:
                    broke = True
                    break
                i_raw = (value >> base) & 1
                q_raw = (value >> (base + 1)) & 1
                i_cmp, q_cmp = rot(i_raw, q_raw)
                if i_cmp != rom[2 * s]:
                    bad.append(2 * s)
                if q_cmp != rom[2 * s + 1]:
                    bad.append(2 * s + 1)
            if broke:
                continue
            if best is None or len(bad) < len(best[2]):
                best = (rot_name, soff, sorted(bad))
    return best


def decoded_frame_bits(value: int, soff: int) -> list[int]:
    out = []
    for i in range(FRAME_BITS):
        s, axis = i >> 1, i & 1
        out.append((value >> (2 * ((SYMS - 1 - s) + soff) + axis)) & 1)
    return out
