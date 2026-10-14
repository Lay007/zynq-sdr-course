"""The board-side message tool (sw/zmsg.c) must carry the same preamble and RRC taps as the FPGA."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_zmsg_tables_match_the_mem_files():
    result = subprocess.run([sys.executable, str(ROOT / "tools" / "gen_zmsg_tables.py"), "--check"], cwd=ROOT)
    assert result.returncode == 0, "sw/zmsg.c tables are out of date: run python tools/gen_zmsg_tables.py"
