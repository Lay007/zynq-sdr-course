#!/usr/bin/env python3
"""Write the preamble and RRC tables into blocks/block_11_integrated_sdr_project/sw/zmsg.c.

The board-side message tool must build exactly the frame the PL modem expects, so its tables come
from the same files the FPGA build reads: the first 48 bits of bpsk_frame_bits.mem (the Lab 11.45
long preamble) and the Q15 taps of bpsk_rrc_tx_fir_taps.mem. tests/test_zmsg_tables.py fails if the
C source and the .mem files drift apart.

    python tools/gen_zmsg_tables.py          # rewrite the block between the markers
    python tools/gen_zmsg_tables.py --check  # exit 1 if it is out of date
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "rtl"
SRC = ROOT / "blocks" / "block_11_integrated_sdr_project" / "sw" / "zmsg.c"
BEGIN, END = "/* BEGIN TABLES */", "/* END TABLES */"


def preamble_bits(n: int = 48) -> list[int]:
    toks = [t for t in (RTL / "bpsk_frame_bits.mem").read_text().split() if t.strip() in ("0", "1")]
    return [int(t) for t in toks[:n]]


def rrc_taps_q15() -> list[int]:
    taps = []
    for tok in (RTL / "bpsk_rrc_tx_fir_taps.mem").read_text().split():
        v = int(tok.strip(), 16)
        taps.append(v - 0x10000 if v >= 0x8000 else v)
    return taps


def table_block() -> str:
    pre = preamble_bits()
    taps = rrc_taps_q15()
    lines = [BEGIN,
             f"static const uint8_t PREAMBLE[{len(pre)}] = {{{', '.join(map(str, pre))}}};",
             f"#define RRC_TAPS_N {len(taps)}",
             "static const double RRC_TAPS[RRC_TAPS_N] = {"]
    for i in range(0, len(taps), 8):
        lines.append("    " + ", ".join(f"{t} / 32768.0" for t in taps[i:i + 8]) + ",")
    lines += ["};", END]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    src = SRC.read_text(encoding="utf-8")
    i, j = src.index(BEGIN), src.index(END) + len(END)
    new = src[:i] + table_block() + src[j:]
    if args.check:
        return 0 if new == src else 1
    SRC.write_text(new, encoding="utf-8")
    print("tables written:", len(preamble_bits()), "preamble bits,", len(rrc_taps_q15()), "taps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
