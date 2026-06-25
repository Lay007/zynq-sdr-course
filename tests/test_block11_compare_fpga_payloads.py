from __future__ import annotations

import sys
from pathlib import Path

import pytest


MODULE_DIR = Path(__file__).resolve().parents[1] / "hardware" / "7020_ad936x_sdr"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from compare_fpga_payloads import compare_payloads  # noqa: E402


def system_top_payload_paths() -> tuple[Path, Path]:
    root = Path(__file__).resolve().parents[1]
    bit_path = (
        root
        / "hardware"
        / "7020_ad936x_sdr"
        / "ps"
        / "ad936x_no_os_reference"
        / "platform"
        / "hw"
        / "system_top.bit"
    )
    return bit_path, bit_path.with_suffix(".bit.bin")


def require_tracked_vendor_payload() -> tuple[Path, Path]:
    root = Path(__file__).resolve().parents[1]
    bit_path, bit_bin_path = system_top_payload_paths()
    missing = [str(path.relative_to(root)) for path in (bit_path, bit_bin_path) if not path.exists()]
    if missing:
        pytest.skip("Vendor FPGA payload is not available in this checkout: " + ", ".join(missing))
    return bit_path, bit_bin_path


def test_compare_payloads_normalizes_raw_bit_against_tracked_bit_bin() -> None:
    bit_path, bit_bin_path = require_tracked_vendor_payload()

    report = compare_payloads(bit_path, bit_bin_path)

    assert report.identical is True
    assert report.first_diff_offset is None
    assert report.common_prefix_bytes == bit_bin_path.stat().st_size


def test_compare_payloads_reports_first_diff_and_trailing_extra_bytes(tmp_path: Path) -> None:
    lhs_path = tmp_path / "lhs.bin"
    rhs_path = tmp_path / "rhs.bin"
    lhs_path.write_bytes(bytes.fromhex("0011223344556677"))
    rhs_path.write_bytes(bytes.fromhex("00112233445566778899aabb"))

    report = compare_payloads(lhs_path, rhs_path)

    assert report.identical is False
    assert report.first_diff_offset == 8
    assert report.common_prefix_bytes == 8
    assert report.length_delta_bytes == 4
    assert report.rhs_has_only_trailing_extra_data is True
