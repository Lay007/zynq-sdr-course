from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "blocks"
    / "block_08_modulation_and_synchronization"
    / "python"
    / "lab_8_7_snr_vs_ber_traps.py"
)
SPEC = importlib.util.spec_from_file_location("lab_8_7_snr_vs_ber_traps", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
LAB = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = LAB
SPEC.loader.exec_module(LAB)


def _run(**kwargs):
    cfg = LAB.LabConfig()
    rng = np.random.default_rng(cfg.seed)
    taps = LAB.rrc_taps(cfg.rrc_alpha, cfg.rrc_span_symbols, cfg.samples_per_symbol)
    tx_bits = rng.integers(0, 2, size=2 * cfg.symbol_count, dtype=np.uint8)
    tx_symbols = LAB.bits_to_qpsk(tx_bits)
    scenario = LAB.Scenario(name="t", **kwargs)
    metrics, _ = LAB.run_scenario(cfg, scenario, tx_bits, tx_symbols, taps, rng)
    return metrics


def test_awgn_reference_is_error_free() -> None:
    metrics = _run(snr_db=18.0)
    assert metrics.ber == 0.0
    assert metrics.compared_bits == 8192
    assert metrics.evm_percent < 10.0


def test_high_snr_carrier_offset_is_a_coin_flip() -> None:
    metrics = _run(snr_db=25.0, cfo_hz=25_000.0)
    assert 0.45 < metrics.ber < 0.55
    assert metrics.evm_percent > 100.0


def test_tiny_cfo_is_already_fatal_without_phase_tracking() -> None:
    # 50 Hz is only 0.0375 deg/symbol but accumulates ~154 deg over the record.
    metrics = _run(snr_db=25.0, cfo_hz=50.0)
    assert metrics.ber > 0.3


def test_timing_offset_breaks_ber_only_beyond_two_samples() -> None:
    assert _run(snr_db=25.0, timing_offset_samples=2).ber == 0.0
    assert _run(snr_db=25.0, timing_offset_samples=3).ber > 1e-2


def test_qpsk_phase_ambiguity_leaves_evm_clean_but_ber_wrong() -> None:
    reference = _run(snr_db=25.0)
    rotated = _run(snr_db=25.0, phase_deg=90.0)
    inverted = _run(snr_db=25.0, phase_deg=180.0)
    assert rotated.evm_percent < 5.0
    assert abs(rotated.evm_percent - reference.evm_percent) < 1.0
    assert abs(rotated.ber - 0.5) < 0.02
    assert inverted.ber > 0.98


def test_clipping_raises_evm_but_not_qpsk_ber() -> None:
    clean = _run(snr_db=25.0)
    clipped = _run(snr_db=25.0, clip_limit=0.18)
    assert clipped.ber == 0.0
    assert clipped.evm_percent > 2.0 * clean.evm_percent


def test_frame_slip_loses_bits_and_scrambles_the_rest() -> None:
    metrics = _run(snr_db=25.0, frame_slip_symbols=1)
    assert metrics.compared_bits == 8190
    assert metrics.ber > 0.4
