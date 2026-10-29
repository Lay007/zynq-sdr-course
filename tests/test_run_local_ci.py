from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("mode,hdl,docs", [(None, True, True), ("--quick", True, False),
                                         ("--software-only", False, False), ("--hdl-only", True, False)])
def test_preflight_modes_select_the_expected_checks(monkeypatch, mode, hdl, docs):
    path = Path(__file__).resolve().parents[1] / "tools/run_local_ci.py"
    spec = importlib.util.spec_from_file_location("review_local_ci", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []
    monkeypatch.setattr(module, "run", calls.append)
    monkeypatch.setattr(sys, "argv", [str(path)] + ([mode] if mode else []))
    assert module.main() == 0
    flattened = [" ".join(command) for command in calls]
    assert any("run_block5_hdl_smoke.py" in call for call in flattened) == hdl
    assert any("run_ofdm_rtl.py" in call for call in flattened) == hdl
    assert any("mkdocs" in call for call in flattened) == docs
    assert any("pytest" in command for command in calls) == (mode != "--hdl-only")
