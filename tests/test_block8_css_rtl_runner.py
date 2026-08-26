from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "tools" / "run_block8_css_rtl.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_block8_css_rtl", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_css_rtl_suite_has_unique_existing_sources() -> None:
    runner = load_runner()
    names = [test.name for test in runner.TESTS]

    assert names == [
        "tb_css_dechirp_mul",
        "tb_css_sf7_dechirp_frontend",
        "tb_css_symbol_buffer",
        "tb_css_dft128_core",
        "tb_css_peak_detector",
        "tb_css_sf7_sequential_detector",
        "tb_css_sf7_axis_detector",
        "tb_css_sf7_axi_accelerator",
    ]
    assert len(names) == len(set(names))
    assert runner.GENERATOR.is_file()
    assert all(source.is_file() for test in runner.TESTS for source in test.sources)


def test_css_rtl_runner_rejects_unknown_test() -> None:
    runner = load_runner()

    try:
        runner.select_tests(["tb_missing_css_block"])
    except ValueError as exc:
        assert "tb_missing_css_block" in str(exc)
    else:
        raise AssertionError("unknown CSS RTL test name was accepted")
