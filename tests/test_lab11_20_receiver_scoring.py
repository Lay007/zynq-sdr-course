from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

LAB_DIR = Path(__file__).resolve().parents[1] / "blocks" / "block_11_integrated_sdr_project" / "python"
if str(LAB_DIR) not in sys.path:
    sys.path.insert(0, str(LAB_DIR))

from end_to_end_bpsk_reference import bits_to_bpsk  # noqa: E402
from lab_11_20_read_rtl_wav_ota_bpsk_ber import receiver_decode_bpsk  # noqa: E402


def _frame() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(20)
    bits = rng.integers(0, 2, size=281, dtype=np.uint8)
    return bits, bits_to_bpsk(bits).astype(np.complex128)


def test_receiver_scoring_tracks_phase_from_the_preamble_only() -> None:
    bits, symbols = _frame()
    n = np.arange(len(symbols), dtype=np.float64)
    frame = 0.4 * symbols * np.exp(1j * (0.003 * n + 2.0))  # residual CFO + large phase
    result = receiver_decode_bpsk(frame, tx_bits=bits, tx_symbols=symbols, preamble_len=25)
    assert result["payload_bits"] == 256
    assert result["bit_errors_payload"] == 0


def test_receiver_scoring_reports_payload_errors() -> None:
    bits, symbols = _frame()
    frame = symbols.copy()
    frame[100:105] *= -1
    result = receiver_decode_bpsk(frame, tx_bits=bits, tx_symbols=symbols, preamble_len=25)
    assert result["bit_errors_payload"] == 5
