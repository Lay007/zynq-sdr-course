"""Regression and negative-control checks for the practice pilot."""

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXERCISE = ROOT / "practice" / "fir-q15"
GRADER = EXERCISE / "check.py"


def _grade(*args):
    return subprocess.run(
        [sys.executable, str(GRADER), *map(str, args)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_reference_passes_all_stages():
    result = _grade("--stage", 3, "--solution")
    assert result.returncode == 0, result.stderr
    assert "PASS: all stages 1-3" in result.stdout


def test_untouched_starter_must_fail():
    result = _grade("--stage", 1, "--path", EXERCISE)
    assert result.returncode != 0
    assert "NotImplementedError" in result.stderr


def test_workspace_initialization_is_non_destructive(tmp_path):
    workspace = tmp_path / "student"
    result = _grade("--init", workspace)
    assert result.returncode == 0, result.stderr
    assert (workspace / "starter.py").read_bytes() == (
        EXERCISE / "starter.py"
    ).read_bytes()
    (workspace / "starter.py").write_text("# student's own edits\n")
    retry = _grade("--init", workspace)
    assert retry.returncode != 0
    assert (workspace / "starter.py").read_text() == "# student's own edits\n"


def test_wrong_tap_order_is_rejected(tmp_path):
    original = (EXERCISE / "reference.py").read_text()
    mutated = original.replace("samples[n - k]", "samples[k]", 1)
    assert mutated != original
    (tmp_path / "starter.py").write_text(mutated)
    result = _grade("--stage", 1, "--path", tmp_path)
    assert result.returncode != 0


def test_truncation_in_quantizer_is_rejected(tmp_path):
    original = (EXERCISE / "reference.py").read_text()
    mutated = original.replace("round(v * 32768)", "int(v * 32768)", 1)
    assert mutated != original
    (tmp_path / "starter.py").write_text(mutated)
    result = _grade("--stage", 2, "--path", tmp_path)
    assert result.returncode != 0


def test_floor_rounding_in_integer_fir_is_rejected(tmp_path):
    original = (EXERCISE / "reference.py").read_text()
    mutated = original.replace(
        "_round_div_ties_even(accumulator, 32768)", "accumulator // 32768", 1
    )
    assert mutated != original
    (tmp_path / "starter.py").write_text(mutated)
    result = _grade("--stage", 3, "--path", tmp_path)
    assert result.returncode != 0
