from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest


MODULE_DIR = Path(__file__).resolve().parents[1] / "blocks" / "block_10_kicad_and_basic_electronics" / "python"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from lab_10_2_rf_passives_design import (  # noqa: E402
    dbm_to_loaded_rms_voltage,
    design_pi_attenuator,
    rc_lowpass_metrics,
)


def test_10_db_50_ohm_pi_attenuator_matches_reference_values() -> None:
    design = design_pi_attenuator(10.0, 50.0)

    assert design.voltage_ratio == pytest.approx(math.sqrt(10.0))
    assert design.series_resistor_ohm == pytest.approx(71.151, abs=0.001)
    assert design.shunt_resistor_ohm == pytest.approx(96.248, abs=0.001)


def test_rc_response_is_minus_3_db_at_cutoff() -> None:
    resistance = 1_000.0
    capacitance = 1e-9
    cutoff = 1.0 / (2.0 * math.pi * resistance * capacitance)

    metrics = rc_lowpass_metrics(resistance, capacitance, [cutoff])

    assert metrics["cutoff_hz"] == pytest.approx(cutoff)
    assert metrics["response"][0]["magnitude_db"] == pytest.approx(-3.0103, abs=0.0001)


def test_zero_dbm_into_50_ohm_is_223_millivolts_rms() -> None:
    assert dbm_to_loaded_rms_voltage(0.0, 50.0) == pytest.approx(0.2236068)
