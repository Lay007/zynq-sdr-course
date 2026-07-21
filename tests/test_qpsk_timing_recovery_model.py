from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


PYTHON_DIR = (
    Path(__file__).resolve().parents[1] / "blocks" / "block_05_fpga_hdl_flow" / "python"
)
sys.path.insert(0, str(PYTHON_DIR))

import qpsk_timing_recovery_model as timing  # noqa: E402


def matched_waveform(dibits: np.ndarray, actual_sps: float) -> np.ndarray:
    taps = timing.load_rrc_taps()
    received = timing.resample_drift(timing.tx_waveform(dibits, taps), actual_sps)
    return np.convolve(received, taps, mode="full")


def test_float_and_fixed_loops_recover_short_high_drift_frame() -> None:
    dibits = timing.load_frame_dibits()
    matched = matched_waveform(dibits, 8.06)
    matched_i, matched_q = timing.quantize_matched(matched)

    floating = timing.timing_recovery_float(matched, 65, len(dibits))
    fixed = timing.timing_recovery_fixed(matched_i, matched_q, 65, len(dibits))
    fixed_phase = timing.fixed_phase_symbols(matched, 68, len(dibits))

    assert timing.symbol_errors(floating.symbols, dibits) == (0, len(dibits))
    assert timing.symbol_errors(fixed.symbols, dibits) == (0, len(dibits))
    assert timing.symbol_errors(fixed_phase, dibits)[0] > 0


def test_fixed_loop_tracks_realistic_clock_error_over_long_stream() -> None:
    count = 12_000
    dibits = np.random.default_rng(0x1134).integers(0, 4, count, dtype=np.int8)

    for actual_sps in (8.0008, 7.9992):  # +/-100 ppm sample-clock mismatch
        matched = matched_waveform(dibits, actual_sps)
        matched_i, matched_q = timing.quantize_matched(matched)
        recovered = timing.timing_recovery_fixed(matched_i, matched_q, 63, count)
        fixed_phase_best = min(
            timing.symbol_errors(
                timing.fixed_phase_symbols(matched, offset, count), dibits
            )[0]
            for offset in range(58, 70)
        )

        assert timing.symbol_errors(recovered.symbols, dibits) == (0, count)
        assert fixed_phase_best > 1_000


def test_dot_product_ted_removes_static_carrier_phase_sensitivity() -> None:
    dibits = timing.load_frame_dibits()
    matched = matched_waveform(dibits, 8.06)

    new_errors = []
    old_errors = []
    for phase_deg in range(0, 91, 5):
        rotation = np.exp(1j * np.deg2rad(phase_deg))
        matched_i, matched_q = timing.quantize_matched(matched * rotation)
        new_best = len(dibits)
        old_best = len(dibits)
        for offset in range(60, 70):
            new = timing.timing_recovery_fixed(matched_i, matched_q, offset, len(dibits))
            old = timing.timing_recovery_fixed(
                matched_i,
                matched_q,
                offset,
                len(dibits),
                ted=timing._ted_axis_sign,
            )
            new_best = min(
                new_best,
                timing.symbol_errors(new.symbols * np.conj(rotation), dibits)[0],
            )
            old_best = min(
                old_best,
                timing.symbol_errors(old.symbols * np.conj(rotation), dibits)[0],
            )
        new_errors.append(new_best)
        old_errors.append(old_best)

    assert max(new_errors) == 0
    assert max(old_errors) > 0
