from __future__ import annotations

import sys
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1] / "blocks" / "block_11_integrated_sdr_project" / "python"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from lab_11_27_runtime_qpsk_digital_loopback import (  # noqa: E402
    decode_payload_error_position,
    loopback_mode_bits,
    resolve_start_offsets,
    summarize_sweep,
)


def test_decode_payload_error_position_handles_segments_and_no_error_sentinel() -> None:
    decoded = decode_payload_error_position(0x04030201, 0x00C80006)
    assert decoded == {
        "segment_errors": [1, 2, 3, 4],
        "first_error_index": 6,
        "last_error_index": 200,
    }

    clean = decode_payload_error_position(0, 0xFFFFFFFF)
    assert clean["segment_errors"] == [0, 0, 0, 0]
    assert clean["first_error_index"] is None
    assert clean["last_error_index"] is None


def test_summarize_sweep_reports_repeatability_by_offset() -> None:
    sweep = [
        {"start_offset": 100, "received_symbols": 140, "total_bit_errors": 0},
        {"start_offset": 100, "received_symbols": 140, "total_bit_errors": 2},
        {"start_offset": 101, "received_symbols": 140, "total_bit_errors": 0},
        {"start_offset": 101, "received_symbols": 0, "total_bit_errors": 0},
    ]

    summary = summarize_sweep(sweep, symbol_count=140)

    assert summary["total_attempts"] == 4
    assert summary["full_frame_attempts"] == 3
    assert summary["zero_error_attempts"] == 2
    assert summary["zero_error_rate"] == 0.5
    assert summary["zero_error_offsets"] == [100, 101]
    assert summary["attempts_by_offset"] == [
        {
            "start_offset": 100,
            "attempts": 2,
            "full_frames": 2,
            "zero_error_frames": 1,
            "zero_error_rate": 0.5,
        },
        {
            "start_offset": 101,
            "attempts": 2,
            "full_frames": 1,
            "zero_error_frames": 1,
            "zero_error_rate": 0.5,
        },
    ]
    assert "2/4 attempts" in summary["conclusion"]


def test_summarize_empty_sweep_has_zero_rate() -> None:
    summary = summarize_sweep([], symbol_count=140, loopback="fabric")

    assert summary["total_attempts"] == 0
    assert summary["zero_error_rate"] == 0.0
    assert summary["attempts_by_offset"] == []
    assert summary["mode"] == "qpsk_fabric_loopback"


def test_loopback_mode_bits_selects_fabric_or_ad9361_source() -> None:
    assert loopback_mode_bits("fabric", "raw") == 0x50
    assert loopback_mode_bits("ad9361", "raw") == 0x30
    assert loopback_mode_bits("ad9361", "fifo") == 0x10
    assert loopback_mode_bits("rf", "raw") == 0x1630
    assert loopback_mode_bits("rf", "fifo") == 0x1610


def test_summarize_rf_sweep_names_physical_path() -> None:
    summary = summarize_sweep(
        [{"start_offset": 62, "received_symbols": 140, "total_bit_errors": 0}],
        symbol_count=140,
        loopback="rf",
    )

    assert summary["mode"] == "qpsk_rf_path"
    assert "QPSK RF path reached BER=0" in summary["conclusion"]


def test_rf_default_sweeps_only_the_eight_picker_phases() -> None:
    assert resolve_start_offsets("rf", None) == list(range(8))
    assert resolve_start_offsets("fabric", None) != list(range(8))
    assert resolve_start_offsets("rf", [3, 7]) == [3, 7]
