"""rtl/ofdm_sync_preamble_rom.v is what tools/generate_ofdm_sync_preamble_rom.py writes (issue #48)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import generate_ofdm_sync_preamble_rom as G  # noqa: E402


def test_committed_rom_matches_the_generator():
    assert G.OUT.read_text(encoding="utf-8") == G.verilog(G.rom_values())


def test_rom_body_has_two_equal_halves():
    text = G.OUT.read_text(encoding="utf-8")
    words = [int(m, 16) for m in re.findall(r"= \{16'h([0-9A-F]{4}), 16'h[0-9A-F]{4}\}", text)]
    assert len(words) == 80
    pre = G.rom_values()
    assert np.array_equal(pre[16:48], pre[48:80])
    # cyclic prefix = the last 16 samples of the body
    assert np.array_equal(pre[:16], pre[64:80])
