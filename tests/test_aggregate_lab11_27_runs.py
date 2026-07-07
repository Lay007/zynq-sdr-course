from __future__ import annotations

import json
import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from aggregate_lab11_27_runs import aggregate_runs  # noqa: E402


def write_run(path: Path, *, errors: list[int], reboot_ok: bool = True) -> None:
    payload = {
        "run_tag": path.stem,
        "symbol_count": 140,
        "bitstream": {"md5": "abc123"},
        "summary": {"mode": "qpsk_fabric_loopback"},
        "sweep": [
            {
                "start_offset": 62,
                "received_symbols": 140,
                "total_bit_errors": error_count,
            }
            for error_count in errors
        ],
        "reboot_after": {"ok": reboot_ok},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_aggregate_runs_counts_boots_and_attempts(tmp_path: Path) -> None:
    run_a = tmp_path / "a.json"
    run_b = tmp_path / "b.json"
    write_run(run_a, errors=[0, 0])
    write_run(run_b, errors=[3, 0])

    summary = aggregate_runs([run_a, run_b], start_offset=62)

    assert summary["boot_sessions"] == 2
    assert summary["successful_boot_sessions"] == 2
    assert summary["boot_success_rate"] == 1.0
    assert summary["attempts_at_offset"] == 4
    assert summary["zero_error_attempts_at_offset"] == 3
    assert summary["zero_error_rate_at_offset"] == 0.75
