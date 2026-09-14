from __future__ import annotations

import pytest

from tools.ofdm_equalizer_fixed import equalize_q15


def test_identity_coefficient_preserves_sample() -> None:
    result = equalize_q15((10000, -7000), (16384, 0))
    assert result.sample == (10000, -7000)
    assert result.saturation_count == 0


def test_minus_j_coefficient_removes_plus_90_degree_rotation() -> None:
    result = equalize_q15((-5000, 10000), (0, -16384))
    assert result.sample == (10000, 5000)
    assert result.saturation_count == 0


def test_q2_14_coefficient_supports_gain_above_unity() -> None:
    result = equalize_q15((10000, -8000), (24576, 0))
    assert result.sample == (15000, -12000)
    assert result.saturation_count == 0


def test_clipped_components_are_counted_explicitly() -> None:
    result = equalize_q15((25000, 25000), (24576, 0))
    assert result.sample == (32767, 32767)
    assert result.saturation_count == 2


def test_rounding_is_half_lsb_away_from_zero() -> None:
    positive = equalize_q15((1, 0), (8192, 0))
    negative = equalize_q15((-1, 0), (8192, 0))
    assert positive.sample == (1, 0)
    assert negative.sample == (-1, 0)


def test_out_of_range_input_is_rejected() -> None:
    with pytest.raises(ValueError):
        equalize_q15((32768, 0), (16384, 0))
