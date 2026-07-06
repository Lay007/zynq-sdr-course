from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from generate_block5_vivado_reports import normalize_report_text  # noqa: E402


def test_normalize_report_text_removes_time_host_and_output_path(tmp_path: Path) -> None:
    output_dir = tmp_path / "reports"
    text = "\n".join(
        [
            "| Date         : Mon Jul  6 12:03:46 2026",
            "| Host         : BUILD-HOST running Windows",
            f"| Command      : report_timing_summary -file {output_dir.as_posix()}/timing.rpt",
            "| Design       : fir_iq_4tap   ",
        ]
    )

    normalized = normalize_report_text(text, output_dir)

    assert "2026" not in normalized
    assert "BUILD-HOST" not in normalized
    assert str(tmp_path).replace("\\", "/") not in normalized
    assert "<output_dir>/timing.rpt" in normalized
    assert normalized.endswith("| Design       : fir_iq_4tap\n")
