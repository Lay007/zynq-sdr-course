"""tools/run_ofdm_radio_board.py without a board: RESULT parsing and the plan (issue #48)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import run_ofdm_radio_board as R  # noqa: E402


def test_parse_result_takes_the_last_line_and_converts_numbers():
    text = ("frame 0: 0 bit errors\nRESULT frames=1 lost=1 bits=0\n"
            "RESULT frames=100 lost=2 bits=9408 bit_errors=3 tx_gain=-10.00 rate=2083334\n")
    row = R.parse_result(text)
    assert row == {"frames": 100, "lost": 2, "bits": 9408, "bit_errors": 3, "tx_gain": -10.0, "rate": 2083334}
    assert R.ber(row) == 3 / 9408
    assert R.parse_result("no result here") == {}


def test_dry_run_plans_the_ladder_and_the_reboot():
    out = subprocess.run([sys.executable, str(ROOT / "tools" / "run_ofdm_radio_board.py"), "loop", "--dry-run",
                          "--tx-gains", "-20", "-10", "--rx-shifts", "4", "5"],
                         capture_output=True, text=True, check=True).stdout
    assert out.count(" loop --frames") == 4
    assert "fpga_manager load" in out and "warm reboot" in out


def test_two_board_never_loads_the_rx_board():
    out = subprocess.run([sys.executable, str(ROOT / "tools" / "run_ofdm_radio_board.py"), "two-board", "--dry-run",
                          "--hot-load-tx", "--rx-host", "192.168.20.1"],
                         capture_output=True, text=True, check=True).stdout
    load_lines = [line for line in out.splitlines() if "fpga_manager load" in line]
    assert load_lines and all("192.168.20.1" not in line for line in load_lines)
