from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "tools" / "run_block5_hdl_smoke.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_block5_hdl_smoke", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_canonical_hdl_suite_has_unique_existing_sources() -> None:
    runner = load_runner()
    names = [test.name for test in runner.TESTS]

    assert len(names) == len(set(names))
    assert {
        "tb_qpsk_zynq_ber_top",
        "tb_qpsk_bridge_loopback",
        "tb_bridge_rx_lclk_fifo",
        "tb_bpsk_zynq_ber_timing_recovery",
    }.issubset(names)
    assert all(source.is_file() for test in runner.TESTS for source in test.sources)


def test_all_generated_inputs_have_a_declared_generator() -> None:
    runner = load_runner()

    assert runner.GENERATORS
    assert all(generator.is_file() for generator in runner.GENERATORS)
    assert len(runner.REQUIRED_GENERATED_FILES) == len(set(runner.REQUIRED_GENERATED_FILES))
