from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "blocks"
    / "block_06_rf_frontend_and_ad9363"
    / "python"
    / "lab_6_10_agc_phase_transition_analysis.py"
)
SPEC = importlib.util.spec_from_file_location("lab_6_10_agc_phase_transition_analysis", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
AGC = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AGC  # dataclasses needs the module registered before exec
SPEC.loader.exec_module(AGC)


def test_self_test_separates_a_real_discontinuity_from_cfo_rotation() -> None:
    result = AGC.run_self_test()

    assert result["self_test_pass"] is True
    assert result["hardware_measurement_claimed"] is False
    assert result["evidence_scope"] == "synthetic-self-test-only"
    assert result["detected_discontinuity_error_rad"] < 0.05
    assert result["control_false_positive_error_rad"] < 0.05
    assert result["with_glitch"]["recovery_samples"] is not None


def test_analyze_transition_reports_zero_discontinuity_for_pure_cfo() -> None:
    n = 2048
    index = 1024
    n_arr = np.arange(n, dtype=np.float64)
    x = 0.4 * np.exp(1j * 0.02 * n_arr)
    result = AGC.analyze_transition(x, index, fit_window=128)
    assert abs(result.phase_discontinuity_rad) < 1e-6
    assert abs(result.amplitude_step_db) < 1e-6


def test_analyze_transition_reports_the_injected_amplitude_step() -> None:
    n = 2048
    index = 1024
    n_arr = np.arange(n, dtype=np.float64)
    amp = np.where(n_arr < index, 0.1, 0.4)
    x = amp * np.exp(1j * 0.0 * n_arr)
    result = AGC.analyze_transition(x, index, fit_window=128)
    expected_step_db = 20.0 * np.log10(0.4 / 0.1)
    assert result.amplitude_step_db == pytest.approx(expected_step_db, abs=0.05)


def test_analyze_transition_rejects_a_transition_too_close_to_the_edges() -> None:
    x = np.ones(100, dtype=np.complex128)
    with pytest.raises(ValueError, match="samples before it"):
        AGC.analyze_transition(x, 10, fit_window=256)


def test_analyze_capture_file_reads_metadata_driven_transitions(tmp_path: Path) -> None:
    n = 2048
    index = 1024
    n_arr = np.arange(n, dtype=np.float64)
    amp = np.where(n_arr < index, 0.2, 0.2)
    x = amp * np.exp(1j * 0.01 * n_arr)

    capture_path = tmp_path / "capture.ci16"
    scale = 32767.0
    i = np.clip(np.round(np.real(x) * scale), -32768, 32767).astype("<i2")
    q = np.clip(np.round(np.imag(x) * scale), -32768, 32767).astype("<i2")
    interleaved = np.empty(2 * n, dtype="<i2")
    interleaved[0::2] = i
    interleaved[1::2] = q
    interleaved.tofile(capture_path)

    metadata_path = tmp_path / "capture.json"
    metadata_path.write_text(
        json.dumps(
            {
                "sampling": {"iq_format": "ci16", "sample_rate_hz": 3_840_000},
                "gain_transitions": [{"sample_index": index}],
            }
        ),
        encoding="utf-8",
    )

    result = AGC.analyze_capture_file(capture_path, metadata_path, fit_window=128)
    assert result["hardware_measurement_claimed"] is True
    assert result["evidence_scope"] == "draft-from-real-capture"
    assert len(result["transitions"]) == 1
    assert result["transitions"][0]["sample_index"] == index
