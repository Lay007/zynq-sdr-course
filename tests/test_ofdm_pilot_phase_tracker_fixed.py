from __future__ import annotations

import cmath
import math

import pytest

from tools.generate_ofdm_pilot_tracker_vectors import DEFAULT_OUT, STREAM_REFS, build_cases, render
from tools.ofdm_equalizer_fixed import equalize_q15
from tools.ofdm_pilot_phase_tracker_fixed import COEFF_ONE, track_symbol


def _pilots(amplitude: float, degrees: float, refs: list[int] = STREAM_REFS) -> list[tuple[int, int]]:
    out = []
    for ref in refs:
        value = (1 if ref >= 0 else -1) * amplitude * cmath.exp(1j * math.radians(degrees))
        out.append((round(value.real), round(value.imag)))
    return out


@pytest.mark.parametrize("degrees", range(-180, 181, 5))
def test_coefficient_is_the_unit_inverse_rotation(degrees: int) -> None:
    result = track_symbol(_pilots(12000, degrees), STREAM_REFS)
    ideal = COEFF_ONE * cmath.exp(-1j * math.radians(degrees))
    assert abs(result.coefficient[0] - ideal.real) <= 7
    assert abs(result.coefficient[1] - ideal.imag) <= 7
    phase_error = (result.phase - degrees / 180 * 32768 + 32768) % 65536 - 32768
    assert abs(phase_error) <= 3
    assert not result.zero_energy


@pytest.mark.parametrize("degrees", [-150, -60, 0, 37, 91, 179])
def test_tracker_plus_equalizer_removes_the_common_phase(degrees: int) -> None:
    coefficient = track_symbol(_pilots(8000, degrees), STREAM_REFS).coefficient
    data = 9000 * cmath.exp(1j * math.radians(degrees + 45))
    out = equalize_q15((round(data.real), round(data.imag)), coefficient).sample
    target = 9000 * cmath.exp(1j * math.radians(45))
    assert abs(out[0] - target.real) <= 10
    assert abs(out[1] - target.imag) <= 10


def test_zero_energy_gives_identity_and_a_flag() -> None:
    result = track_symbol([(0, 0)] * 4, STREAM_REFS)
    assert result.coefficient == (COEFF_ONE, 0)
    assert result.zero_energy


def test_only_the_reference_sign_matters() -> None:
    pilots = _pilots(10000, 30)
    flipped_refs = [-32768 if r >= 0 else 32767 for r in STREAM_REFS]
    flipped = track_symbol(pilots, flipped_refs)
    # Flipping every reference sign is a pi rotation of the correlation.
    assert flipped.correlation == tuple(-c for c in track_symbol(pilots, STREAM_REFS).correlation)


def test_committed_vectors_match_the_model() -> None:
    assert DEFAULT_OUT.read_text(encoding="utf-8") == render(build_cases())
