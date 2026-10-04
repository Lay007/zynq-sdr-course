from __future__ import annotations

import cmath
import math
import random
from pathlib import Path

from tools.generate_ofdm_channel_eq_vectors import DEFAULT_OUT, NORMALIZED_OUT, build_frames, render
from tools.ofdm_channel_equalizer_fixed import (
    data_index_for_bin,
    equalize,
    equalize_normalized,
    estimate,
    inverse,
    is_null,
    train_bits,
    train_reference,
)


def test_committed_vectors_match_the_model() -> None:
    frames = build_frames()
    assert Path(DEFAULT_OUT).read_text(encoding="utf-8") == render(frames)
    assert Path(NORMALIZED_OUT).read_text(encoding="utf-8") == render(frames, normalize=True)


def test_cordic_inverse_is_accurate() -> None:
    for energy in (1, 3, 1000, 2**17 + 5, 724 * 724, 512 * 512, 2**33 - 1):
        z, sh = inverse(energy)
        assert abs(z / 2**sh - 2**14 / energy) <= 2 ** 14 / energy * 4e-5
    assert inverse(0) == (0, 37)


def test_zero_forcing_puts_every_carrier_on_one_grid() -> None:
    rng = random.Random(11)
    for _ in range(200):
        h = rng.uniform(0.05, 1.8) * cmath.exp(1j * rng.uniform(-math.pi, math.pi))
        k = rng.choice([b for b in range(64) if not is_null(b) and b not in (7, 21, 43, 57)])
        xr, xi = train_reference(k)
        train = h * complex(xr, xi) * 362
        g = estimate(k, (round(train.real), round(train.imag)))
        sr, si = rng.choice([-1, 1]), rng.choice([-1, 1])
        y = h * complex(sr, si) * 362
        (zr, zi), sat = equalize_normalized((round(y.real), round(y.imag)), g, inverse(g[0] ** 2 + g[1] ** 2))
        assert sat == 0
        # 2^14 * Y / G with G = 2 * 362 * H: about 8192 per component, whatever |H|.
        assert abs(zr - sr * 8192) < 8192 * 0.06 and abs(zi - si * 8192) < 8192 * 0.06


def test_training_reference_covers_the_lab85_plan() -> None:
    used = [k for k in range(64) if not is_null(k)]
    assert len(used) == 52
    assert sorted({data_index_for_bin(k) for k in used if k not in (7, 21, 43, 57)}) == list(range(48))
    assert [train_reference(k) for k in (7, 21, 43, 57)] == [(1, 0), (-1, 0), (1, 0), (1, 0)]
    assert train_reference(0) is None and train_reference(32) is None
    assert {train_bits(d) for d in range(48)} == {(0, 0), (0, 1), (1, 0), (1, 1)}


def test_qpsk_signs_survive_any_channel_phase_without_division() -> None:
    """Z = Y conj(G) has the transmitted signs for every carrier phase and gain."""
    rng = random.Random(7)
    for _ in range(200):
        h = rng.uniform(0.2, 1.4) * cmath.exp(1j * rng.uniform(-math.pi, math.pi))
        k = rng.choice([b for b in range(64) if not is_null(b) and b not in (7, 21, 43, 57)])
        xr, xi = train_reference(k)
        train = h * complex(xr, xi) * 362
        g = estimate(k, (round(train.real), round(train.imag)))
        sr, si = rng.choice([-1, 1]), rng.choice([-1, 1])
        y = h * complex(sr, si) * 362
        (zr, zi), sat = equalize((round(y.real), round(y.imag)), g)
        assert sat == 0
        assert (zr > 0) == (sr > 0) and (zi > 0) == (si > 0)


def test_unit_channel_gives_half_scale() -> None:
    k = 1
    xr, xi = train_reference(k)
    g = estimate(k, (362 * xr, 362 * xi))
    (zr, zi), _ = equalize((362, -362), g)
    # 362 * 724 / 16 = 16380.5, rounded half away from zero.
    assert (zr, zi) == (16381, -16381)
