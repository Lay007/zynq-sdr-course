from __future__ import annotations

import sys
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1] / "blocks" / "block_11_integrated_sdr_project" / "python"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from lab_11_35_paired_timing_ab import (  # noqa: E402
    error_localization,
    is_lock,
    paired_difference,
    summarize,
    synthetic_row,
)


def pair(
    *,
    fixed_lock: bool,
    gardner_lock: bool,
    fixed_clean: bool = False,
    gardner_clean: bool = False,
    cfo: float = 30_000.0,
) -> dict:
    return {
        "cfo_hz": cfo,
        "fixed": synthetic_row(lock=fixed_lock, clean=fixed_clean),
        "gardner": synthetic_row(lock=gardner_lock, clean=gardner_clean),
    }


def test_paired_difference_keeps_discordant_direction() -> None:
    pairs = [
        pair(fixed_lock=False, gardner_lock=True),
        pair(fixed_lock=False, gardner_lock=True),
        pair(fixed_lock=True, gardner_lock=False),
        pair(fixed_lock=True, gardner_lock=True),
    ]

    result = paired_difference(pairs, is_lock)

    assert result["fixed_successes"] == 2
    assert result["gardner_successes"] == 3
    assert result["gardner_only"] == 2
    assert result["fixed_only"] == 1
    assert result["delta"] == 0.25


def test_summary_accepts_clean_noninferiority_and_lock_superiority() -> None:
    pairs = []
    for index in range(400):
        pairs.append(
            pair(
                fixed_lock=index < 240,
                gardner_lock=index < 320,
                fixed_clean=index < 100,
                gardner_clean=index < 100,
                cfo=float((index % 3) * 30_000),
            )
        )

    result = summarize(pairs, clean_margin=0.02, lock_margin=0.10)

    assert result["clean_noninferior"] is True
    assert result["lock_superior"] is True
    assert result["passed"] is True
    assert result["decision"] == "promote_gardner"


def test_summary_rejects_clean_deficit_even_with_more_locks() -> None:
    pairs = []
    for index in range(400):
        pairs.append(
            pair(
                fixed_lock=index < 240,
                gardner_lock=index < 320,
                fixed_clean=index < 120,
                gardner_clean=index < 80,
            )
        )

    result = summarize(pairs, clean_margin=0.02, lock_margin=0.10)

    assert result["paired_clean"]["delta"] == -0.1
    assert result["clean_noninferior"] is False
    assert result["passed"] is False
    assert result["decision"] == "retain_fixed_baseline"


def test_timing_telemetry_is_split_by_decode_outcome() -> None:
    pairs = [
        pair(fixed_lock=True, gardner_lock=True, gardner_clean=True),
        pair(fixed_lock=True, gardner_lock=True, gardner_clean=False),
        pair(fixed_lock=True, gardner_lock=False),
    ]
    pairs[0]["gardner"]["timing_debug"]["omega_q16"] = 16_300
    pairs[1]["gardner"]["timing_debug"]["omega_q16"] = 16_400
    pairs[2]["gardner"]["timing_debug"]["omega_q16"] = 16_500

    telemetry = summarize(pairs, clean_margin=0.02, lock_margin=0.10)[
        "gardner_timing_telemetry"
    ]

    assert telemetry["clean"]["omega_q16"]["min"] == 16_300
    assert telemetry["dirty_full"]["omega_q16"]["min"] == 16_400
    assert telemetry["no_lock"]["omega_q16"]["min"] == 16_500


def test_error_localization_separates_preamble_from_payload() -> None:
    rows = [
        synthetic_row(lock=True, clean=True),
        synthetic_row(lock=True, clean=False),
        synthetic_row(lock=True, clean=False),
        synthetic_row(lock=True, clean=False),
        synthetic_row(lock=False, clean=False),
    ]
    rows[0]["payload_errors"] = 0
    rows[1]["total_bit_errors"] = 1
    rows[1]["payload_errors"] = 0
    rows[1]["payload_error_position"] = {
        "segment_errors": [0, 0, 0, 0],
        "first_error_index": None,
        "last_error_index": None,
    }
    rows[2]["total_bit_errors"] = 1
    rows[2]["payload_errors"] = 1
    rows[2]["payload_error_position"] = {
        "segment_errors": [1, 0, 0, 0],
        "first_error_index": 6,
        "last_error_index": 6,
    }
    rows[3]["total_bit_errors"] = 3
    rows[3]["payload_errors"] = 2
    rows[3]["payload_error_position"] = {
        "segment_errors": [0, 0, 1, 1],
        "first_error_index": 130,
        "last_error_index": 250,
    }
    rows[0]["payload_error_position"] = {
        "segment_errors": [0, 0, 0, 0],
        "first_error_index": None,
        "last_error_index": None,
    }

    result = error_localization(rows)

    assert result["telemetry_available"] is True
    assert result["full_frames"] == 4
    assert result["total_bit_errors"] == 5
    assert result["preamble_bit_errors"] == 2
    assert result["payload_bit_errors"] == 3
    assert result["preamble_only_dirty_frames"] == 1
    assert result["payload_only_dirty_frames"] == 1
    assert result["mixed_dirty_frames"] == 1
    assert result["single_bit_preamble_frames"] == 1
    assert result["single_bit_payload_frames"] == 1
    assert result["position_telemetry_available"] is True
    assert result["payload_error_segments"] == [1, 0, 1, 1]
    assert result["first_payload_error_index"]["min"] == 6
    assert result["first_payload_error_index"]["max"] == 130
    assert result["last_payload_error_index"]["max"] == 250
