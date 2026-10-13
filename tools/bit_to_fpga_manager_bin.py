#!/usr/bin/env python3
"""Convert a Vivado .bit into the .bin that the Zynq Linux fpga_manager loads.

This is what `bootgen -arch zynq -process_bitstream bin` produces, without needing bootgen:

1. drop the .bit header (design name, part, date and time fields up to the 'e' length field);
2. append four type-1 NOOP words (0x20000000), as bootgen does;
3. byte-swap every 32-bit word.

Checked on 2026-10-14 to reproduce, byte for byte, two bootgen outputs of the course: the
`*.wordswap.bit.bin` used by the runtime-reload labs (Lab 11.12 onwards) and the `system.bit.bin`
written next to the course overlay build.

usage: python tools/bit_to_fpga_manager_bin.py <in.bit> <out.bin> [--compare reference.bin]
"""
from __future__ import annotations

import argparse
import hashlib
import struct
from pathlib import Path

NOOP = bytes.fromhex("20000000")


def bit_payload(data: bytes) -> bytes:
    """Configuration data of a .bit file (everything after the header's 'e' length field)."""
    (n,) = struct.unpack(">H", data[0:2])
    pos = 2 + n + 2                    # first field, then the 0x0001 length
    while pos < len(data):
        key = data[pos:pos + 1]
        pos += 1
        if key == b"e":
            (length,) = struct.unpack(">I", data[pos:pos + 4])
            pos += 4
            return data[pos:pos + length]
        (length,) = struct.unpack(">H", data[pos:pos + 2])
        pos += 2 + length
    raise ValueError("no 'e' field: not a Xilinx .bit file")


def swap32(data: bytes) -> bytes:
    if len(data) % 4:
        raise ValueError("payload is not a whole number of 32-bit words")
    out = bytearray(len(data))
    out[0::4], out[1::4], out[2::4], out[3::4] = data[3::4], data[2::4], data[1::4], data[0::4]
    return bytes(out)


def convert(bit: bytes) -> bytes:
    return swap32(bit_payload(bit) + NOOP * 4)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("bit", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--compare", type=Path, help="reference .bin that must come out identical")
    args = ap.parse_args()
    payload = convert(args.bit.read_bytes())
    args.out.write_bytes(payload)
    print(f"{args.out}: {len(payload)} bytes, sha256 {hashlib.sha256(payload).hexdigest()}")
    if args.compare:
        same = args.compare.read_bytes() == payload
        print("identical to reference:", same)
        return 0 if same else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
