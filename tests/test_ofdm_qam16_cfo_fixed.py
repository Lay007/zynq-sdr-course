from __future__ import annotations

import cmath
import math
from pathlib import Path

from tools.generate_ofdm_cfo_vectors import DEFAULT_OUT, build_streams, render
from tools.ofdm_cfo_corrector_fixed import ATAN, CfoCorrector, rotate, vector_angle
from tools.ofdm_qam16_fixed import LEVEL_INNER, LEVEL_OUTER, THRESHOLD, demap, map_bits, slice_axis


def test_qam16_gray_levels_and_round_trip() -> None:
    assert (LEVEL_INNER, LEVEL_OUTER) == (10362, 31086)
    assert THRESHOLD == 5461
    levels = {}
    for code in range(16):
        i, q = map_bits(code)
        levels[code] = (i, q)
        # equalized grid: 2^14 * X / (2 * outer) -> outer 8192, inner 8192 / 3
        zi, zq = (round(v * 8192 / LEVEL_OUTER) for v in (i, q))
        assert demap(zi, zq) == code
    # Gray on each axis: +3, +1, -1, -3 differ by one bit between neighbours
    order = [0b00, 0b01, 0b11, 0b10]
    assert [map_bits(b << 2)[0] for b in order] == [31086, 10362, -10362, -31086]


def test_slicer_thresholds() -> None:
    assert slice_axis(5460) == (0, 1)
    assert slice_axis(5461) == (0, 0)
    assert slice_axis(-5461) == (1, 0)
    assert slice_axis(0) == (0, 1)


def test_committed_cfo_vectors_match_the_model() -> None:
    assert Path(DEFAULT_OUT).read_text(encoding="utf-8") == render(build_streams())


def test_cordic_angle_and_rotation_accuracy() -> None:
    assert ATAN[0] == 1 << 21
    for degrees in range(-179, 180, 7):
        th = math.radians(degrees)
        a = vector_angle(round(1e9 * math.cos(th)), round(1e9 * math.sin(th)))
        assert abs(a * 360 / (1 << 24) - degrees) < 1e-3
        x = (12000, -7000)
        r = rotate(x, round(th * (1 << 24) / (2 * math.pi)))
        ideal = complex(*x) * cmath.exp(1j * th)
        assert abs(complex(*r) - ideal) < 3.0


def test_cfo_estimate_from_the_vectors_streams() -> None:
    streams = build_streams()
    for stream, cfo in ((0, 0.004), (1, -0.006), (2, 0.0075)):
        model = CfoCorrector()
        for frame in streams[stream]:
            model.correct(frame)
        assert abs(-model.theta / (1 << 24) / 64 - cfo) < 2e-6
