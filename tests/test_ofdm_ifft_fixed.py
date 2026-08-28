import numpy as np
import pytest

from tools.ofdm_ifft_fixed import (
    FFT_SIZE,
    Q_MAX,
    Q_MIN,
    ifft64_q15,
    quantize_q15,
)


def _lab85_frequency_bins(seed: int = 805) -> tuple[tuple[int, int], ...]:
    rng = np.random.default_rng(seed)
    used_k = np.concatenate([np.arange(-26, 0), np.arange(1, 27)])
    pilot_k = np.array([-21, -7, 7, 21])
    pilot_set = set(pilot_k.tolist())
    data_k = np.array([k for k in used_k if k not in pilot_set])

    bits = rng.integers(0, 2, size=2 * len(data_k), dtype=np.uint8)
    pairs = bits.reshape(-1, 2)
    i_data = np.where(pairs[:, 0] == 0, 23170, -23170)
    q_data = np.where(pairs[:, 1] == 0, 23170, -23170)

    bins: list[tuple[int, int]] = [(0, 0) for _ in range(FFT_SIZE)]
    for k, i_value, q_value in zip(data_k, i_data, q_data, strict=True):
        bins[int(k) % FFT_SIZE] = (int(i_value), int(q_value))

    pilot_values = [32767, 32767, 32767, -32768]
    for k, pilot_value in zip(pilot_k, pilot_values, strict=True):
        bins[int(k) % FFT_SIZE] = (pilot_value, 0)

    return tuple(bins)


def _numpy_ifft_q15(freq_bins: tuple[tuple[int, int], ...]) -> np.ndarray:
    complex_bins = np.array(
        [real + 1j * imag for real, imag in freq_bins],
        dtype=np.complex128,
    ) / 32768.0
    reference = np.fft.ifft(complex_bins)
    return np.column_stack(
        [
            [quantize_q15(float(value)) for value in reference.real],
            [quantize_q15(float(value)) for value in reference.imag],
        ]
    )


def test_q15_endpoint_quantization() -> None:
    assert quantize_q15(1.0) == Q_MAX
    assert quantize_q15(-1.0) == Q_MIN
    assert quantize_q15(0.0) == 0
    assert quantize_q15(1.5) == Q_MAX
    assert quantize_q15(-1.5) == Q_MIN


def test_ifft_rejects_wrong_length() -> None:
    with pytest.raises(ValueError, match="exactly 64"):
        ifft64_q15(((0, 0),) * 63)


def test_ifft_rejects_out_of_range_input() -> None:
    bins = [(0, 0) for _ in range(FFT_SIZE)]
    bins[3] = (Q_MAX + 1, 0)
    with pytest.raises(ValueError, match="signed Q1.15"):
        ifft64_q15(tuple(bins))


def test_dc_bin_gives_constant_time_domain_output() -> None:
    bins = [(0, 0) for _ in range(FFT_SIZE)]
    bins[0] = (Q_MAX, 0)

    result = ifft64_q15(tuple(bins))

    assert result.samples == ((512, 0),) * FFT_SIZE
    assert result.stage_saturations == (0, 0, 0, 0, 0, 0)
    assert result.total_saturations == 0


def test_lab85_vector_matches_numpy_within_two_output_lsbs() -> None:
    freq_bins = _lab85_frequency_bins()
    result = ifft64_q15(freq_bins)
    fixed = np.asarray(result.samples, dtype=np.int64)
    reference = _numpy_ifft_q15(freq_bins)
    error = fixed - reference

    assert np.max(np.abs(error)) <= 2
    assert result.stage_saturations == (0, 0, 0, 0, 0, 0)
    assert result.total_saturations == 0


def test_multiple_lab85_symbols_remain_unsaturated_and_close_to_float() -> None:
    for seed in (1, 7, 85, 805, 2026):
        freq_bins = _lab85_frequency_bins(seed)
        result = ifft64_q15(freq_bins)
        fixed = np.asarray(result.samples, dtype=np.int64)
        reference = _numpy_ifft_q15(freq_bins)

        assert np.max(np.abs(fixed - reference)) <= 2
        assert result.total_saturations == 0
