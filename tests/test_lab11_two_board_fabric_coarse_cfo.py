from __future__ import annotations

import sys
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1] / "blocks" / "block_11_integrated_sdr_project" / "python"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from lab_11_32_two_board_fabric_coarse_cfo import (  # noqa: E402
    summarize_attempts,
    summarize_experiment,
)


def attempt(offset: int, received: int, errors: int, *, timed_out: bool = False) -> dict:
    return {
        "start_offset": offset,
        "received_symbols": received,
        "total_bit_errors": errors,
        "timed_out": timed_out,
        "ok": True,
    }


def test_summarize_attempts_separates_acquisition_from_aggregate_ber() -> None:
    summary = summarize_attempts(
        [
            attempt(0, 140, 0),
            attempt(1, 140, 140),
            attempt(2, 0, 0, timed_out=True),
            attempt(3, 140, 70),
        ]
    )

    assert summary["locked"] is True
    assert summary["reached_zero"] is True
    assert summary["best_errors"] == 0
    assert summary["best_ber"] == 0.0
    assert summary["full_frames"] == 3
    assert summary["clean_frames"] == 1
    assert summary["attempts"] == 4
    assert summary["total_bits_in_full_frames"] == 840
    assert summary["total_errors_in_full_frames"] == 210
    assert summary["aggregate_ber"] == 0.25
    assert summary["lock_rate"] == 0.75
    assert summary["clean_attempt_rate"] == 0.25
    assert summary["clean_given_lock_rate"] == 1 / 3
    assert len(summary["attempt_results"]) == 4


def test_summarize_attempts_reports_no_lock_without_fake_zero_ber() -> None:
    summary = summarize_attempts([attempt(0, 0, 0, timed_out=True)])

    assert summary["locked"] is False
    assert summary["reached_zero"] is False
    assert summary["best_ber"] is None
    assert summary["aggregate_ber"] is None
    assert summary["clean_attempt_rate"] == 0.0


def test_summarize_attempts_preserves_and_decodes_timing_observability() -> None:
    row = attempt(3, 140, 0)
    row["debug"] = {
        "adc_input": "0x20008000",
        "capture": "0xFFFFFFFF",
        "tx": "0x00000001",
        "rx": "0x00000002",
    }

    result = summarize_attempts([row], timing_recovery=True)["attempt_results"][0]

    assert result["debug"]["adc_input"] == "0x20008000"
    assert result["timing_debug"] == {
        "mu_q16": 0x8000,
        "omega_q16": 0x2000,
        "ted_error": -1,
    }


def point(cfo: float, *, on_zero: bool, off_zero: bool) -> dict:
    def side(reached_zero: bool) -> dict:
        return {
            "reached_zero": reached_zero,
            "clean_frames": int(reached_zero),
            "attempts": 8,
        }

    return {"cfo_hz": cfo, "coarse_on": side(on_zero), "coarse_off": side(off_zero)}


def test_acceptance_allows_costas_at_zero_but_rejects_it_at_large_cfo() -> None:
    summary = summarize_experiment(
        [
            point(0.0, on_zero=True, off_zero=True),
            point(15_000.0, on_zero=True, off_zero=False),
            point(30_000.0, on_zero=True, off_zero=False),
        ],
        min_discriminating_cfo_hz=15_000.0,
    )

    assert summary["passed"] is True
    assert summary["coarse_on_acquired_points"] == 3
    assert summary["costas_only_acquired_discriminating_points"] == 0
    assert "3/3 CFO points" in summary["conclusion"]


def test_acceptance_fails_when_coarse_misses_a_point() -> None:
    summary = summarize_experiment(
        [point(0.0, on_zero=True, off_zero=True), point(30_000.0, on_zero=False, off_zero=False)],
        min_discriminating_cfo_hz=15_000.0,
    )

    assert summary["passed"] is False
