"""Tables of ofdm_frame_conditioner (issue #48): the sine ROM and the CORDIC arctangents."""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "blocks/block_08_modulation_and_synchronization/rtl"
sys.path.insert(0, str(ROOT / "tools"))
import generate_ofdm_sin_rom as G  # noqa: E402


def test_committed_sin_rom_matches_the_generator():
    assert G.OUT.read_text(encoding="utf-8") == G.verilog()


def test_sin_table_endpoints_are_exact():
    t = G.table()
    assert t[0] == 0 and t[256] == 32767 and len(t) == 257


def test_cordic_arctangents():
    text = (RTL / "ofdm_frame_conditioner.v").read_text(encoding="utf-8")
    found = {int(i): int(v) for i, v in re.findall(r"4'd(\d+): atan_tab = 16'd(\d+);", text)}
    assert sorted(found) == list(range(15))
    for i, v in found.items():
        assert v == round(math.atan(2.0 ** -i) / (2 * math.pi) * 65536), i
