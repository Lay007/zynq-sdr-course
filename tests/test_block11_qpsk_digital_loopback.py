from __future__ import annotations

import sys
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1] / "blocks" / "block_11_integrated_sdr_project" / "python"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from lab_11_27_runtime_qpsk_digital_loopback import summarize_sweep  # noqa: E402


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
    summary = summarize_sweep([], symbol_count=140)

    assert summary["total_attempts"] == 0
    assert summary["zero_error_rate"] == 0.0
    assert summary["attempts_by_offset"] == []
