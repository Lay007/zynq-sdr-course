from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


LAB_DIR = Path(__file__).resolve().parents[1] / "blocks" / "block_11_integrated_sdr_project" / "python"
if str(LAB_DIR) not in sys.path:
    sys.path.insert(0, str(LAB_DIR))

from end_to_end_bpsk_reference import rrc_taps, upsample  # noqa: E402
from lab_11_22_capture_runtime_pl_rtl_monitor_wav import build_qpsk_attempt_summary  # noqa: E402
from lab_11_28_read_rtl_wav_ota_qpsk import detect_frame, load_reference  # noqa: E402


def test_qpsk_detector_recovers_known_rom_frame_with_cfo() -> None:
    sample_rate_hz = 3_840_000.0
    sps = 8
    tx_bits, tx_symbols = load_reference(140)
    taps = rrc_taps(0.35, 8, sps)
    burst = np.convolve(upsample(tx_symbols, sps), taps)
    capture = np.concatenate([np.zeros(257, dtype=np.complex128), burst])
    n = np.arange(len(capture), dtype=np.float64)
    capture *= np.exp(1j * (2.0 * np.pi * 2_400.0 * n / sample_rate_hz + 0.43))
    matched = np.convolve(capture, taps)

    result = detect_frame(
        matched,
        tx_bits=tx_bits,
        tx_symbols=tx_symbols,
        sps=sps,
        sample_rate_hz=sample_rate_hz,
        sync_symbol_count=16,
        candidate_count=12,
    )

    assert result["bit_errors_total"] == 0
    assert result["ber_total"] == 0.0
    assert abs(result["residual_cfo_hz"] - 2_400.0) < 10.0


def test_qpsk_capture_summary_counts_attempt_outcomes() -> None:
    attempts = [
        {"ok": True, "received_symbols": 140, "total_bit_errors": 0, "payload_errors": 0},
        {"ok": True, "received_symbols": 140, "total_bit_errors": 2, "payload_errors": 2},
        {"ok": True, "received_symbols": 0, "total_bit_errors": 0, "payload_errors": 0},
        {"ok": False},
    ]

    summary = build_qpsk_attempt_summary(attempts, 140)

    assert summary["attempt_count"] == 4
    assert summary["command_success_count"] == 3
    assert summary["complete_internal_rx_count"] == 2
    assert summary["zero_error_internal_rx_count"] == 1
