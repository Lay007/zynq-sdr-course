import numpy as np
import pytest

from tools.ofdm_fft_fixed import FFT_SIZE, Q_MAX, fft64_q15, quantize_q15
from tools.ofdm_ifft_fixed import ifft64_q15


def _numpy_scaled_fft_q15(
    time_samples: tuple[tuple[int, int], ...],
) -> np.ndarray:
    complex_samples = np.array(
        [real + 1j * imag for real, imag in time_samples],
        dtype=np.complex128,
    ) / 32768.0
    reference = np.fft.fft(complex_samples) / FFT_SIZE
    return np.column_stack(
        [
            [quantize_q15(float(value)) for value in reference.real],
            [quantize_q15(float(value)) for value in reference.imag],
        ]
    )


def test_fft_rejects_wrong_length() -> None:
    with pytest.raises(ValueError, match="exactly 64"):
        fft64_q15(((0, 0),) * 63)


def test_scaled_fft_of_constant_input_is_dc_only() -> None:
    samples = ((512, 0),) * FFT_SIZE

    result = fft64_q15(samples)

    assert result.bins[0] == (512, 0)
    assert result.bins[1:] == ((0, 0),) * (FFT_SIZE - 1)
    assert result.total_saturations == 0


def test_bin1_ifft_round_trip_returns_expected_scaled_bin() -> None:
    bins = [(0, 0) for _ in range(FFT_SIZE)]
    bins[1] = (Q_MAX, 0)
    time_domain = ifft64_q15(tuple(bins)).samples

    result = fft64_q15(time_domain)
    fixed = np.asarray(result.bins, dtype=np.int64)
    reference = _numpy_scaled_fft_q15(time_domain)

    assert np.max(np.abs(fixed - reference)) <= 2
    assert abs(result.bins[1][0] - 512) <= 2
    assert abs(result.bins[1][1]) <= 2
    assert np.max(np.abs(np.delete(fixed, 1, axis=0))) <= 2
    assert result.total_saturations == 0


def test_scaled_fft_matches_numpy_for_deterministic_complex_vector() -> None:
    rng = np.random.default_rng(8048)
    samples = tuple(
        (int(real), int(imag))
        for real, imag in rng.integers(-2048, 2049, size=(FFT_SIZE, 2))
    )

    result = fft64_q15(samples)
    fixed = np.asarray(result.bins, dtype=np.int64)
    reference = _numpy_scaled_fft_q15(samples)

    assert np.max(np.abs(fixed - reference)) <= 2
    assert result.total_saturations == 0
