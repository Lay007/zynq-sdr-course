from pathlib import Path

from tools.ofdm_ifft_fixed import FFT_SIZE, ifft64_q15

ROOT = Path(__file__).resolve().parents[1]
TX_VECTOR = ROOT / "verification" / "vectors" / "block08_ofdm_tx_cycle4_expected.mem"

QPSK_LEVEL = 23170
PILOT_POS = 32767
PILOT_NEG = -32768


def _signed16(value: int) -> int:
    return value - 0x10000 if value & 0x8000 else value


def _load_packed_complex(path: Path) -> tuple[tuple[int, int], ...]:
    samples: list[tuple[int, int]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        packed = int(stripped, 16)
        samples.append(
            (
                _signed16((packed >> 16) & 0xFFFF),
                _signed16(packed & 0xFFFF),
            )
        )
    return tuple(samples)


def _cycle4_mapper_output(index: int) -> tuple[int, int]:
    bits = index % 4
    if bits == 0:  # 00
        return QPSK_LEVEL, QPSK_LEVEL
    if bits == 1:  # 01
        return QPSK_LEVEL, -QPSK_LEVEL
    if bits == 2:  # 10
        return -QPSK_LEVEL, QPSK_LEVEL
    return -QPSK_LEVEL, -QPSK_LEVEL  # 11


def _build_lab85_cycle4_bins() -> tuple[tuple[int, int], ...]:
    used_k = [*range(-26, 0), *range(1, 27)]
    pilot_k = {-21, -7, 7, 21}
    data_k = [k for k in used_k if k not in pilot_k]

    assert len(data_k) == 48

    bins = [(0, 0) for _ in range(FFT_SIZE)]
    for data_index, k in enumerate(data_k):
        bins[k % FFT_SIZE] = _cycle4_mapper_output(data_index)

    for k, pilot in zip((-21, -7, 7, 21), (PILOT_POS, PILOT_POS, PILOT_POS, PILOT_NEG), strict=True):
        bins[k % FFT_SIZE] = (pilot, 0)

    return tuple(bins)


def test_canonical_mapped_tx_vector_matches_python_fixed_path_exactly() -> None:
    result = ifft64_q15(_build_lab85_cycle4_bins())
    canonical = _load_packed_complex(TX_VECTOR)

    assert len(canonical) == FFT_SIZE
    assert result.samples == canonical
    assert result.stage_saturations == (0, 0, 0, 0, 0, 0)
    assert result.total_saturations == 0
