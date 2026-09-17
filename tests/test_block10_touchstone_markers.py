from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "blocks"
    / "block_10_kicad_and_basic_electronics"
    / "python"
    / "lab_10_5_touchstone_marker_extract.py"
)
SPEC = importlib.util.spec_from_file_location("lab_10_5_touchstone_marker_extract", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
TS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TS  # dataclasses needs the module registered before exec
SPEC.loader.exec_module(TS)


def test_self_test_recovers_the_injected_attenuator_response(tmp_path: Path) -> None:
    result = TS.run_self_test(tmp_path)

    assert result["self_test_pass"] is True
    assert result["hardware_measurement_claimed"] is False
    assert result["evidence_scope"] == "synthetic-self-test-only"
    assert "S11, dB" in result["markdown_table"]


def test_parse_touchstone_s2p_reads_db_format(tmp_path: Path) -> None:
    path = tmp_path / "thru.s2p"
    path.write_text(
        "! test fixture\n"
        "# MHZ S DB R 50\n"
        "10 -0.5 0 -0.2 5 -0.2 5 -0.5 0\n"
        "20 -0.5 0 -0.2 10 -0.2 10 -0.5 0\n",
        encoding="utf-8",
    )
    sweep = TS.parse_touchstone(path)
    assert sweep.n_ports == 2
    assert sweep.reference_ohm == 50.0
    assert sweep.frequency_hz == (10e6, 20e6)
    assert TS.db_of(sweep.params["S21"][0]) == pytest.approx(-0.2, abs=1e-9)


def test_parse_touchstone_rejects_wrong_extension(tmp_path: Path) -> None:
    path = tmp_path / "thru.txt"
    path.write_text("# MHZ S DB R 50\n10 0 0\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"\.s1p or \.s2p"):
        TS.parse_touchstone(path)


def test_parse_touchstone_rejects_non_monotonic_frequency(tmp_path: Path) -> None:
    path = tmp_path / "bad.s1p"
    path.write_text("# MHZ S DB R 50\n10 0 0\n5 0 0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="strictly increasing"):
        TS.parse_touchstone(path)


def test_interpolate_param_handles_a_large_phase_step_without_cancellation() -> None:
    import math

    freqs = (10e6, 100e6)
    magnitude = 0.3
    # Exactly the same magnitude at both ends, phase turns by 170 degrees
    # between them -- naive complex-part interpolation would partially
    # cancel the magnitude at the midpoint instead of preserving it.
    v0 = complex(magnitude, 0.0)
    v1 = magnitude * complex(math.cos(math.radians(170.0)), math.sin(math.radians(170.0)))
    interpolated = TS._interpolate_param(freqs, (v0, v1), 55e6)
    assert abs(interpolated) == pytest.approx(magnitude, abs=1e-9)


def test_extract_markers_reports_one_port_s21_as_none(tmp_path: Path) -> None:
    path = tmp_path / "load.s1p"
    path.write_text("# MHZ S DB R 50\n10 -20 0\n20 -20 0\n", encoding="utf-8")
    sweep = TS.parse_touchstone(path)
    rows = TS.extract_markers(sweep, [15e6])
    assert rows[0].s21_db is None
    assert rows[0].s21_phase_deg is None
    assert rows[0].s11_db == pytest.approx(-20.0, abs=1e-9)


def test_render_markdown_table_matches_report_template_header() -> None:
    header = TS.render_markdown_table([]).splitlines()[0]
    for column in ("Frequency", "S11, dB", "VSWR", "S21, dB", "Phase / delay", "Comment"):
        assert column in header
