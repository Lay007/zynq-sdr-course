from __future__ import annotations

import sys
from pathlib import Path

import pytest


MODULE_DIR = (
    Path(__file__).resolve().parents[1]
    / "hardware"
    / "7020_ad936x_sdr"
    / "boot"
)
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from build_system_bit_bin import (  # noqa: E402
    TRAILING_NOOP_COUNT,
    TRAILING_NOOP_WORD,
    build_system_bit_bin,
    convert_bit_to_fpga_load_payload,
    parse_xilinx_bit,
)


def encode_test_bit(payload: bytes) -> bytes:
    header = bytearray()
    header.extend((9).to_bytes(2, "big"))
    header.extend(bytes.fromhex("0ff00ff00ff00ff00f"))
    header.extend((1).to_bytes(2, "big"))

    for tag, value in (
        ("a", "synthetic_test.ncd"),
        ("b", "xc7z020clg400-1"),
        ("c", "2026/06/22"),
        ("d", "12:34:56"),
    ):
        encoded = value.encode("ascii") + b"\x00"
        header.extend(tag.encode("ascii"))
        header.extend(len(encoded).to_bytes(2, "big"))
        header.extend(encoded)

    header.extend(b"e")
    header.extend(len(payload).to_bytes(4, "big"))
    header.extend(payload)
    return bytes(header)


def system_top_bit_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    return (
        root
        / "hardware"
        / "7020_ad936x_sdr"
        / "ps"
        / "ad936x_no_os_reference"
        / "platform"
        / "hw"
        / "system_top.bit"
    )


def require_tracked_vendor_payload() -> tuple[Path, Path]:
    bit_path = system_top_bit_path()
    expected_path = bit_path.with_suffix(".bit.bin")
    missing = [str(path.relative_to(Path(__file__).resolve().parents[1])) for path in (bit_path, expected_path) if not path.exists()]
    if missing:
        pytest.skip("Vendor FPGA payload is not available in this checkout: " + ", ".join(missing))
    return bit_path, expected_path


def test_convert_bit_to_fpga_load_payload_word_swaps_and_appends_noops() -> None:
    raw_payload = bytes.fromhex("ffffffff000000bb11220044aa995566")
    metadata, converted = convert_bit_to_fpga_load_payload(encode_test_bit(raw_payload))

    assert metadata["a"] == "synthetic_test.ncd"
    assert metadata["b"] == "xc7z020clg400-1"
    assert converted == bytes.fromhex(
        "ffffffffbb00000044002211665599aa"
    ) + (TRAILING_NOOP_WORD * TRAILING_NOOP_COUNT)


def test_convert_bit_to_fpga_load_payload_rejects_non_word_aligned_payload() -> None:
    try:
        convert_bit_to_fpga_load_payload(encode_test_bit(b"\x01\x02\x03"))
    except ValueError as exc:
        assert "multiple of 32 bits" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected a non-word-aligned payload failure.")


def test_build_system_bit_bin_matches_tracked_vendor_payload(tmp_path: Path) -> None:
    bit_path, expected_path = require_tracked_vendor_payload()
    output_path = tmp_path / "system_top.bit.bin"

    result_path = build_system_bit_bin(bit_path, output_path=output_path)
    metadata, raw_payload = parse_xilinx_bit(bit_path.read_bytes())

    assert result_path == output_path.resolve()
    assert result_path.read_bytes() == expected_path.read_bytes()
    assert metadata["a"].startswith("system_top")
    assert "Version=2021.1" in metadata["a"]
    assert len(raw_payload) + (len(TRAILING_NOOP_WORD) * TRAILING_NOOP_COUNT) == result_path.stat().st_size
