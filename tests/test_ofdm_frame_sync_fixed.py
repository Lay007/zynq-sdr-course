"""Bit-exact model of rtl/ofdm_frame_sync.v (issue #48 stage 4b), without the RTL."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import ofdm_frame_sync_fixed as F  # noqa: E402
import ofdm_rf_link as O  # noqa: E402
from test_ofdm_rf_link_sync import _burst  # noqa: E402


def test_dc_tracker_removes_a_constant_offset():
    y = F.dc_track(np.full(4000, 300, dtype=np.int64))
    assert abs(int(y[-1])) <= 1


def test_one_frame_found_early_inside_the_cyclic_prefix():
    rng = np.random.default_rng(5)
    for lead in (300, 517, 899):
        x, body_start = _burst(rng, lead)
        y = O.channel(x, rng, 20.0, 3000.0, 2.083e6, 0.4, 0.0, 0.0, 0.0, 3700.0)
        found = F.detect(y)
        first_symbol = body_start + O.N
        assert len(found) == 1, (lead, found)
        # the window may start early (inside the CP of the first symbol), never late
        assert -O.CP // 2 <= found[0] - first_symbol <= 0, (lead, found[0], first_symbol)


def test_dc_offset_in_silence_gives_no_second_frame():
    # Without the DC tracker a 3 % DC offset made the silence after the burst look periodic
    # and a false second frame was found 93 samples after it.
    rng = np.random.default_rng(6)
    x, _ = _burst(rng, 400)
    y = O.channel(x, rng, 30.0, 0.0, 2.083e6, 0.0, 0.03, 0.0, 0.0, 3700.0)
    assert len(F.detect(y)) == 1


def test_noise_alone_gives_no_frame():
    rng = np.random.default_rng(7)
    noise = (rng.normal(size=3000) + 1j * rng.normal(size=3000)) * 1000.0
    assert F.detect(np.round(noise.real) + 1j * np.round(noise.imag)) == []
