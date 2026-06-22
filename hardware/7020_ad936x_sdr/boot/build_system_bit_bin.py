#!/usr/bin/env python3
"""Convert a Xilinx `.bit` into the word-swapped `.bit.bin` payload used by `fpga load`."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


TRAILING_NOOP_WORD = bytes.fromhex("00000020")
TRAILING_NOOP_COUNT = 4


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def default_output_path(bit_path: Path) -> Path:
    return Path(f"{bit_path}.bin")


def read_be16(payload: bytes, offset: int) -> tuple[int, int]:
    end = offset + 2
    if end > len(payload):
        raise ValueError("Unexpected end of .bit file while reading 16-bit field.")
    return int.from_bytes(payload[offset:end], "big"), end


def read_be32(payload: bytes, offset: int) -> tuple[int, int]:
    end = offset + 4
    if end > len(payload):
        raise ValueError("Unexpected end of .bit file while reading 32-bit field.")
    return int.from_bytes(payload[offset:end], "big"), end


def parse_xilinx_bit(bit_payload: bytes) -> tuple[dict[str, str], bytes]:
    cursor = 0
    magic_len, cursor = read_be16(bit_payload, cursor)
    magic_end = cursor + magic_len
    if magic_end > len(bit_payload):
        raise ValueError("Unexpected end of .bit file while reading header magic.")
    cursor = magic_end

    sentinel, cursor = read_be16(bit_payload, cursor)
    if sentinel != 0x0001:
        raise ValueError(f"Unexpected .bit header sentinel: 0x{sentinel:04X}")

    metadata: dict[str, str] = {}
    while cursor < len(bit_payload):
        tag_byte = bit_payload[cursor : cursor + 1]
        if not tag_byte:
            break
        cursor += 1
        tag = tag_byte.decode("ascii", errors="strict")

        if tag == "e":
            payload_len, cursor = read_be32(bit_payload, cursor)
            payload_end = cursor + payload_len
            if payload_end > len(bit_payload):
                raise ValueError(
                    "Unexpected end of .bit file while reading bitstream payload."
                )
            return metadata, bit_payload[cursor:payload_end]

        value_len, cursor = read_be16(bit_payload, cursor)
        value_end = cursor + value_len
        if value_end > len(bit_payload):
            raise ValueError(
                f"Unexpected end of .bit file while reading tag '{tag}'."
            )
        metadata[tag] = (
            bit_payload[cursor:value_end].rstrip(b"\x00").decode(
                "ascii",
                errors="replace",
            )
        )
        cursor = value_end

    raise ValueError("The .bit file does not contain an 'e' configuration payload tag.")


def word_swap_bitstream(payload: bytes) -> bytes:
    if len(payload) % 4 != 0:
        raise ValueError(
            "The extracted bitstream payload length is not a multiple of 32 bits."
        )

    swapped = bytearray(len(payload))
    for index in range(0, len(payload), 4):
        swapped[index : index + 4] = payload[index : index + 4][::-1]
    return bytes(swapped)


def convert_bit_to_fpga_load_payload(
    bit_payload: bytes,
    *,
    append_trailing_noops: bool = True,
) -> tuple[dict[str, str], bytes]:
    metadata, raw_payload = parse_xilinx_bit(bit_payload)
    converted = bytearray(word_swap_bitstream(raw_payload))
    if append_trailing_noops:
        converted.extend(TRAILING_NOOP_WORD * TRAILING_NOOP_COUNT)
    return metadata, bytes(converted)


def build_system_bit_bin(
    bit_path: Path,
    *,
    output_path: Path | None = None,
    append_trailing_noops: bool = True,
) -> Path:
    bit_path = bit_path.resolve()
    if not bit_path.exists():
        raise FileNotFoundError(f"Missing input bit file: {bit_path}")
    if bit_path.suffix.lower() != ".bit":
        raise ValueError(f"Expected a .bit input, got: {bit_path.name}")

    output_path = (output_path or default_output_path(bit_path)).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    _metadata, converted = convert_bit_to_fpga_load_payload(
        bit_path.read_bytes(),
        append_trailing_noops=append_trailing_noops,
    )
    output_path.write_bytes(converted)
    return output_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bit_path", type=Path, help="Input raw .bit file")
    parser.add_argument(
        "--output",
        type=Path,
        help="Output .bit.bin path; defaults to <bit_path>.bin",
    )
    parser.add_argument(
        "--no-trailing-noops",
        action="store_true",
        help="Do not append the four trailing 0x20000000 NOOP words.",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    bit_path = args.bit_path.resolve()
    metadata, converted = convert_bit_to_fpga_load_payload(
        bit_path.read_bytes(),
        append_trailing_noops=not args.no_trailing_noops,
    )
    output_path = (args.output or default_output_path(bit_path)).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(converted)

    print(f"Input : {bit_path}")
    print(f"Output: {output_path}")
    print(f"Size  : {output_path.stat().st_size} bytes")
    print(f"MD5   : {md5_file(output_path)}")
    if metadata:
        print("Tags  :")
        for key in sorted(metadata):
            print(f"  {key}: {metadata[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
