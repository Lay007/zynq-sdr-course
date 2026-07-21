from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIR = ROOT / "blocks" / "block_11_integrated_sdr_project" / "python"
sys.path.insert(0, str(PYTHON_DIR))

from lab_11_33_residual_cfo_timing_hypothesis import build_summary  # noqa: E402


def write_run(path: Path, *, offset: int, clean: int, full: int, attempts: int = 40) -> None:
    path.write_text(
        """{
  "start_offsets": [%d],
  "points": [{
    "cfo_hz": 30000,
    "coarse_on": {
      "clean_frames": %d,
      "full_frames": %d,
      "attempts": %d,
      "clean_attempt_rate": %.6f,
      "lock_rate": %.6f,
      "aggregate_ber": 0.1
    }
  }]
}
"""
        % (offset, clean, full, attempts, clean / attempts, full / attempts)
    )


def test_live_ab_vetoes_a_replay_only_improvement(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.json"
    candidate_a = tmp_path / "candidate_a.json"
    candidate_b = tmp_path / "candidate_b.json"
    write_run(accepted, offset=4, clean=27, full=39)
    write_run(candidate_a, offset=3, clean=12, full=31)
    write_run(candidate_b, offset=5, clean=14, full=29)

    summary = build_summary(accepted, [candidate_a, candidate_b])

    assert summary["passed"] is True
    assert summary["decision"] == "reject_settled_squared_energy_picker"
    assert summary["accepted_receiver"]["clean_attempt_rate"] == 0.675
    assert summary["best_rejected_picker_run"]["clean_attempt_rate"] == 0.35
    assert summary["rtl_evidence"]["retained_capture_old_costas_errors"] == 124
    assert summary["rtl_evidence"]["retained_capture_tuned_costas_errors"] == 0
