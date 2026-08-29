from __future__ import annotations

import sys
from pathlib import Path


LAB_DIR = Path(__file__).resolve().parents[1] / "blocks" / "block_11_integrated_sdr_project" / "python"
if str(LAB_DIR) not in sys.path:
    sys.path.insert(0, str(LAB_DIR))

from end_to_end_bpsk_reference import write_utf8_lf  # noqa: E402


def test_write_utf8_lf_is_platform_independent(tmp_path: Path) -> None:
    output = tmp_path / "artifact.json"

    write_utf8_lf(output, "{\n  \"ok\": true\n}\n")

    assert output.read_bytes() == b'{\n  "ok": true\n}\n'
