from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / "blocks" / "block_08_modulation_and_synchronization" / "python"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, PY / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


LAB81 = _load("lab_8_1_cfo_estimation_correction")
LAB82 = _load("lab_8_2_phase_offset_correction")


def _qpsk(n: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    bits = rng.integers(0, 2, size=2 * n, dtype=np.uint8)
    return bits, LAB82.bits_to_qpsk(bits)


@pytest.mark.parametrize("phase", [-0.7, -0.3, 0.0, 0.3, 0.7])
def test_4th_power_phase_estimate_has_no_pi_over_4_offset(phase: float) -> None:
    # Regression: angle(mean(r**4))/4 without the sign flip was off by pi/4.
    _, tx = _qpsk(2048, 1)
    rx = tx * np.exp(1j * phase)
    assert abs(LAB82.estimate_phase_4th_power(rx) - phase) < 1e-9
    assert abs(LAB81.estimate_phase_qpsk(rx) - phase) < 1e-9


def test_phase_outside_pi_over_4_is_ambiguous_by_a_quarter_turn() -> None:
    _, tx = _qpsk(2048, 2)
    estimate = LAB82.estimate_phase_4th_power(tx * np.exp(1j * 0.82))
    assert abs(estimate - (0.82 - np.pi / 2)) < 1e-9


def test_blind_correction_recovers_bits_for_default_offset() -> None:
    cfg = LAB82.PhaseConfig()
    assert abs(cfg.phase_offset_rad) < np.pi / 4
    rng = np.random.default_rng(cfg.seed)
    bits = rng.integers(0, 2, size=2 * cfg.symbol_count, dtype=np.uint8)
    tx = LAB82.bits_to_qpsk(bits)
    noise = rng.standard_normal(cfg.symbol_count) + 1j * rng.standard_normal(
        cfg.symbol_count
    )
    rx = tx * np.exp(1j * cfg.phase_offset_rad) + cfg.noise_rms * noise
    corrected = rx * np.exp(-1j * LAB82.estimate_phase_4th_power(rx))
    assert LAB82.ber(bits, rx)[0] > 0.01
    assert LAB82.ber(bits, corrected)[1] == 0


def test_cfo_estimator_and_residual_phase() -> None:
    cfg = LAB81.CfoConfig()
    bits, tx = _qpsk(cfg.symbol_count, 3)
    n = np.arange(cfg.symbol_count)
    rx = tx * np.exp(
        1j * (2 * np.pi * cfg.cfo_hz * n / cfg.sample_rate_hz + cfg.phase_offset_rad)
    )
    cfo = LAB81.estimate_cfo_4th_power(rx, cfg.sample_rate_hz)
    assert abs(cfo - cfg.cfo_hz) < 0.01
    derotated = rx * np.exp(-1j * 2 * np.pi * cfo * n / cfg.sample_rate_hz)
    residual = LAB81.estimate_phase_qpsk(derotated)
    assert abs(residual - cfg.phase_offset_rad) < 1e-3
    corrected = derotated * np.exp(-1j * residual)
    assert LAB81.ber(bits, corrected)[1] == 0
