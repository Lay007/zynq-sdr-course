from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from summarize_snapshot_impl_sweep import choose_best, eligible_run  # noqa: E402


def make_run(name: str, wns: float, *, complete: bool = True) -> dict:
    return {
        "run_name": name,
        "status": "complete" if complete else "failed",
        "metrics": {
            "timing": {"wns_ns": wns, "timing_met": wns >= 0.0},
            "route": {"fully_routed": True},
        },
        "bitstream": {"sha256": "a" * 64},
    }


def test_choose_best_ignores_failed_and_negative_runs() -> None:
    runs = [
        make_run("negative", -0.1),
        make_run("passing", 0.12),
        make_run("best", 0.27),
        make_run("failed", 0.8, complete=False),
    ]

    assert not eligible_run(runs[0])
    assert choose_best(runs)["run_name"] == "best"
