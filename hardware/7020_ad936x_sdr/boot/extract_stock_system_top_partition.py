#!/usr/bin/env python3
"""Extract the stock PL partition payload from a Zynq BOOT.bin image.

The vendor SD image ships a BOOT.bin that already contains the working PL
partition used by the board during early boot. This helper extracts the
embedded `system_top.bit` partition payload exactly as it appears in BOOT.bin,
so it can be reused as a known-good `fpga load` baseline when a rebuilt Vivado
image is still under investigation.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def read_u32_le(blob: bytes, offset: int) -> int:
    return int.from_bytes(blob[offset : offset + 4], "little")


def read_word_swapped_c_string(blob: bytes, offset: int, size: int = 32) -> str:
    raw = blob[offset : offset + size]
    words = [raw[i : i + 4][::-1] for i in range(0, len(raw), 4)]
    unswapped = b"".join(words)
    return unswapped.split(b"\x00", 1)[0].decode("ascii", errors="replace")


def find_partition(boot_blob: bytes, image_name: str) -> tuple[int, int]:
    image_header_table_offset = read_u32_le(boot_blob, 0x98)
    total_images = read_u32_le(boot_blob, image_header_table_offset + 0x04)
    image_header_offset = read_u32_le(boot_blob, image_header_table_offset + 0x0C) * 4

    current_image_header = image_header_offset
    for _ in range(total_images):
        image_name_found = read_word_swapped_c_string(
            boot_blob, current_image_header + 0x10
        )
        partition_header_offset_words = read_u32_le(boot_blob, current_image_header + 0x04)
        partition_header_offset = partition_header_offset_words * 4

        if image_name_found == image_name:
            partition_offset_words = read_u32_le(boot_blob, partition_header_offset + 0x14)
            partition_length_words = read_u32_le(boot_blob, partition_header_offset + 0x08)
            return partition_offset_words * 4, partition_length_words * 4

        next_image_header_words = read_u32_le(boot_blob, current_image_header + 0x00)
        if next_image_header_words == 0:
            break
        current_image_header = next_image_header_words * 4

    raise ValueError(f"Image header '{image_name}' not found in BOOT.bin")

def main() -> int:
    script_dir = Path(__file__).resolve().parent
    default_boot = script_dir / "sd_image" / "BOOT.bin"
    default_output = script_dir.parent / "stock_system_top_from_BOOT.bin"

    parser = argparse.ArgumentParser(
        description="Extract a named partition from a Zynq BOOT.bin image."
    )
    parser.add_argument(
        "--boot-bin",
        type=Path,
        default=default_boot,
        help=f"Input BOOT.bin path (default: {default_boot})",
    )
    parser.add_argument(
        "--image-name",
        default="system_top.bit",
        help="Image header name to extract (default: system_top.bit)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help=f"Output extracted partition payload file (default: {default_output})",
    )
    args = parser.parse_args()

    boot_blob = args.boot_bin.read_bytes()
    partition_offset, partition_length = find_partition(boot_blob, args.image_name)
    payload = boot_blob[partition_offset : partition_offset + partition_length]

    args.output.write_bytes(payload)
    print(f"boot_bin={args.boot_bin}")
    print(f"image_name={args.image_name}")
    print(f"partition_offset=0x{partition_offset:08X}")
    print(f"partition_length={partition_length}")
    print(f"md5={hashlib.md5(payload).hexdigest()}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
