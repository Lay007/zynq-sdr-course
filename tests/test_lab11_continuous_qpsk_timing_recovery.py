from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIR = ROOT / "blocks" / "block_11_integrated_sdr_project" / "python"
sys.path.insert(0, str(PYTHON_DIR))

from lab_11_34_continuous_qpsk_timing_recovery import compare  # noqa: E402


def campaign(*, timing: bool, clean: tuple[int, int], full: tuple[int, int]) -> dict:
    points = []
    for cfo, clean_count, full_count in zip((0, 30_000), clean, full):
        points.append(
            {
                "cfo_hz": cfo,
                "coarse_on": {
                    "attempts": 20,
                    "clean_frames": clean_count,
                    "full_frames": full_count,
                },
            }
        )
    return {
        "timing_recovery": timing,
        "carrier_hz": 915e6,
        "tx_gain_db": -30,
        "rx_gain_db": 50,
        "start_offsets": [0, 1],
        "retries_per_offset": 10,
        "points": points,
    }


def test_equal_budget_gardner_improvement_advances_to_long_ber() -> None:
    baseline = campaign(timing=False, clean=(8, 10), full=(18, 18))
    gardner = campaign(timing=True, clean=(14, 15), full=(19, 19))

    summary = compare(baseline, gardner)

    assert summary["passed"] is True
    assert summary["decision"] == "accept_gardner_for_long_ber"
    assert summary["baseline_fixed_sampler"]["attempts"] == 40
    assert summary["continuous_gardner"]["clean_frames"] == 29


def test_mismatched_campaign_budget_is_rejected() -> None:
    baseline = campaign(timing=False, clean=(8, 10), full=(18, 18))
    gardner = campaign(timing=True, clean=(14, 15), full=(19, 19))
    gardner["retries_per_offset"] = 9

    with pytest.raises(ValueError, match="budgets do not match"):
        compare(baseline, gardner)
