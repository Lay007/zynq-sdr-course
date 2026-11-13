"""The diagnostic grader must accept references and reject behavioral defects."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "practice/diagnostics"
spec = importlib.util.spec_from_file_location("diagnostic_grader", HERE / "check.py")
GRADER = importlib.util.module_from_spec(spec)
spec.loader.exec_module(GRADER)


def test_reference_and_all_software_mutants_are_distinguished():
    result = GRADER.self_test()
    assert result["passed"]
    assert result["learner_completion"] is False
    assert len(result["controls"]) == 11
    for control in result["controls"]:
        assert control["result"]["passed"] == control["expected_pass"], control["control"]


def test_wrong_cfo_sign_doubles_the_frequency_error():
    result = GRADER.check_python(GRADER.load_module(HERE / "starter.py"), "cfo")
    clean = result["checks"][0]["metrics"]
    assert clean["residual_cfo_hz"] == pytest.approx(5500, abs=1e-6)
    assert clean["bit_errors"] > 0
    assert clean["compared_bits"] == 4096


def test_iq_swap_mirrors_both_frequency_signs():
    result = GRADER.check_python(GRADER.load_module(HERE / "starter.py"), "iq")
    for check in result["checks"][:2]:
        metrics = check["metrics"]
        assert metrics["observed_peak_hz"] == -metrics["expected_peak_hz"]


def test_accumulator_wrap_is_exposed_only_by_the_stress_vectors():
    checks = GRADER.check_python(GRADER.load_module(HERE / "starter.py"), "fir")["checks"]
    by_name = {c["test"]: c for c in checks}
    assert by_name["small_signal_scale"]["passed"]
    assert by_name["causal_asymmetric_impulse"]["passed"]
    assert not by_name["positive_overload"]["passed"]
    assert not by_name["negative_overload"]["passed"]
    assert not by_name["signed_product_endpoint"]["passed"]


@pytest.mark.parametrize("value", [np.array([np.nan]), np.zeros(3), np.zeros((3, 1))])
def test_bad_output_cannot_produce_a_pass(value):
    candidate = SimpleNamespace(decode_iq=lambda raw: value)
    with pytest.raises(ValueError, match="finite output samples"):
        GRADER.check_python(candidate, "iq")


def test_init_preserves_learner_files_and_the_starter_fails(tmp_path):
    workspace = tmp_path / "learner"
    GRADER.initialize(workspace)
    candidate = GRADER.load_module(workspace / "learner.py")
    assert all(not GRADER.check_python(candidate, case)["passed"] for case in GRADER.PYTHON_CASES)
    report = workspace / "report.md"
    report.write_text("My prediction", encoding="utf-8")
    with pytest.raises(FileExistsError):
        GRADER.initialize(workspace)
    assert report.read_text(encoding="utf-8") == "My prediction"


def test_cli_exit_codes_json_and_source_preservation(tmp_path, capsys):
    output = tmp_path / "metrics.json"
    for source, code in (("reference.py", 0), ("starter.py", 1)):
        path = HERE / source
        before = path.read_bytes()
        assert GRADER.main(["check", "--case", "fir", "--implementation", str(path), "--output", str(output)]) == code
        saved = json.loads(output.read_text(encoding="utf-8"))
        assert saved["passed"] == (code == 0)
        assert saved["source"]["sha256"] == GRADER.source_info(path)["sha256"]
        assert path.read_bytes() == before
    assert GRADER.main(["check", "--case", "fir", "--implementation", str(path), "--output", str(path)]) == 2
    assert path.read_bytes() == before
    broken = tmp_path / "broken.py"
    broken.write_text("def fir_q15(\n", encoding="utf-8")
    assert GRADER.main(["check", "--case", "fir", "--implementation", str(broken), "--output", str(output)]) == 2
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["passed"] is False
    assert saved["completed"] is False
    assert saved["error_type"] == "SyntaxError"
    assert "ERROR:" in capsys.readouterr().err


def test_learner_exception_is_a_tool_error_not_behavioral_failure(tmp_path):
    broken = tmp_path / "broken.py"
    broken.write_text("def decode_iq(raw):\n    return 1 / 0\n", encoding="utf-8")
    assert GRADER.main(["check", "--case", "iq", "--implementation", str(broken)]) == 2


def test_missing_rtl_tools_are_an_error_not_a_pass(monkeypatch):
    monkeypatch.setattr(GRADER.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="no RTL result"):
        GRADER.self_test(rtl_only=True)


@pytest.mark.parametrize("compile_code,sim_code,log", [
    (1, 0, ""), (0, 0, ""), (0, 1, "unrelated fatal"),
    (0, 0, "DIAGNOSTIC_FAIL: broken"), (0, 1, "DIAGNOSTIC_PASS: false success"),
])
def test_infrastructure_errors_do_not_count_as_killed_mutants(monkeypatch, compile_code, sim_code, log):
    monkeypatch.setattr(GRADER.shutil, "which", lambda name: name)

    def fake_run(command, **kwargs):
        if command[0] == "iverilog":
            return subprocess.CompletedProcess(command, compile_code, "", "compile diagnostic")
        return subprocess.CompletedProcess(command, sim_code, log, "")

    monkeypatch.setattr(GRADER.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError):
        GRADER.check_axis(GRADER.AXIS_REFERENCE)


@pytest.mark.skipif(not shutil.which("iverilog") or not shutil.which("vvp"), reason="Icarus required; CI runs RTL self-test explicitly")
def test_real_axis_reference_and_mutants():
    result = GRADER.self_test(rtl_only=True)
    assert result["passed"]
    controls = {c["control"]: c for c in result["controls"]}
    assert "received=64" in controls["axis_reference"]["result"]["log"]
    assert "stalled output changed" in controls["axis_drop"]["result"]["log"]
    assert "duplicate" in controls["axis_duplicate"]["result"]["log"]


def test_manifest_references_real_cases_and_pages():
    manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    assert {c["id"] for c in manifest["cases"]} == {*GRADER.PYTHON_CASES, "axis"}
    assert not manifest["hardware_required"]
    for path in manifest["pages"].values():
        assert (ROOT / path).is_file()
