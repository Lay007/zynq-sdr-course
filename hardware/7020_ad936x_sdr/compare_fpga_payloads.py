#!/usr/bin/env python3
"""Compare two FPGA-load payloads after normalizing raw `.bit` inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from boot.build_system_bit_bin import convert_bit_to_fpga_load_payload


WINDOW_RADIUS = 16


@dataclass(frozen=True)
class PayloadInfo:
    path: str
    kind: str
    size_bytes: int
    md5: str
    metadata: dict[str, str]


@dataclass(frozen=True)
class PayloadDiffReport:
    lhs: PayloadInfo
    rhs: PayloadInfo
    identical: bool
    common_prefix_bytes: int
    common_suffix_bytes: int
    compared_prefix_md5_equal: bool
    length_delta_bytes: int
    first_diff_offset: int | None
    first_diff_word_offset: int | None
    differing_bytes_in_common_prefix: int
    lhs_diff_window_hex: str
    rhs_diff_window_hex: str
    rhs_has_only_trailing_extra_data: bool
    lhs_has_only_trailing_extra_data: bool


def md5_bytes(payload: bytes) -> str:
    return hashlib.md5(payload).hexdigest()


def common_prefix_length(lhs: bytes, rhs: bytes) -> int:
    limit = min(len(lhs), len(rhs))
    for index in range(limit):
        if lhs[index] != rhs[index]:
            return index
    return limit


def common_suffix_length(lhs: bytes, rhs: bytes, *, prefix_len: int) -> int:
    lhs_limit = len(lhs) - prefix_len
    rhs_limit = len(rhs) - prefix_len
    limit = min(lhs_limit, rhs_limit)
    for index in range(1, limit + 1):
        if lhs[-index] != rhs[-index]:
            return index - 1
    return limit


def differing_bytes(lhs: bytes, rhs: bytes, prefix_len: int) -> int:
    return sum(
        1
        for index in range(prefix_len)
        if lhs[index] != rhs[index]
    )


def hex_window(payload: bytes, offset: int | None) -> str:
    if offset is None:
        return ""
    start = max(0, offset - WINDOW_RADIUS)
    end = min(len(payload), offset + WINDOW_RADIUS)
    return payload[start:end].hex()


def load_payload(path: Path) -> tuple[PayloadInfo, bytes]:
    raw_payload = path.read_bytes()
    metadata: dict[str, str] = {}

    if path.suffix.lower() == ".bit":
        metadata, payload = convert_bit_to_fpga_load_payload(raw_payload)
        kind = "raw_bit_normalized_to_fpga_load_payload"
    else:
        payload = raw_payload
        kind = "fpga_load_payload"

    info = PayloadInfo(
        path=str(path),
        kind=kind,
        size_bytes=len(payload),
        md5=md5_bytes(payload),
        metadata=metadata,
    )
    return info, payload


def compare_payloads(lhs_path: Path, rhs_path: Path) -> PayloadDiffReport:
    lhs_info, lhs_payload = load_payload(lhs_path.resolve())
    rhs_info, rhs_payload = load_payload(rhs_path.resolve())

    prefix_len = common_prefix_length(lhs_payload, rhs_payload)
    first_diff_offset = None if lhs_payload == rhs_payload else prefix_len
    suffix_len = common_suffix_length(
        lhs_payload,
        rhs_payload,
        prefix_len=prefix_len,
    )

    lhs_has_only_trailing_extra_data = (
        prefix_len == len(rhs_payload)
        and len(lhs_payload) > len(rhs_payload)
    )
    rhs_has_only_trailing_extra_data = (
        prefix_len == len(lhs_payload)
        and len(rhs_payload) > len(lhs_payload)
    )

    return PayloadDiffReport(
        lhs=lhs_info,
        rhs=rhs_info,
        identical=lhs_payload == rhs_payload,
        common_prefix_bytes=prefix_len,
        common_suffix_bytes=suffix_len,
        compared_prefix_md5_equal=md5_bytes(lhs_payload[:prefix_len]) == md5_bytes(rhs_payload[:prefix_len]),
        length_delta_bytes=len(rhs_payload) - len(lhs_payload),
        first_diff_offset=first_diff_offset,
        first_diff_word_offset=None if first_diff_offset is None else first_diff_offset // 4,
        differing_bytes_in_common_prefix=differing_bytes(lhs_payload, rhs_payload, prefix_len),
        lhs_diff_window_hex=hex_window(lhs_payload, first_diff_offset),
        rhs_diff_window_hex=hex_window(rhs_payload, first_diff_offset),
        rhs_has_only_trailing_extra_data=rhs_has_only_trailing_extra_data,
        lhs_has_only_trailing_extra_data=lhs_has_only_trailing_extra_data,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lhs", type=Path)
    parser.add_argument("rhs", type=Path)
    parser.add_argument("--json-out", type=Path)
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    report = compare_payloads(args.lhs, args.rhs)
    output = json.dumps(asdict(report), indent=2)
    print(output)

    if args.json_out is not None:
        args.json_out.write_text(output + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
