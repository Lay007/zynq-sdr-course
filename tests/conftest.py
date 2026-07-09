from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "tools" / "run_block5_hdl_smoke.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_block5_hdl_smoke", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session", autouse=True)
def block5_generated_inputs() -> None:
    """Build the Block-5 stimulus the HDL testbenches and analyzers read.

    The vectors and the ``*_bits.mem`` ROMs are generated, not committed (.gitignore),
    so on a clean checkout they simply do not exist. The Block-5 HDL job creates them by
    going through the smoke runner; pytest reads the same files directly and has to do
    the same, otherwise every test that opens ``bpsk_frame_bits.mem`` fails with
    FileNotFoundError on CI while passing on any developer machine that has run the
    simulations once.
    """
    runner = _load_runner()
    try:
        runner.require_generated_inputs()
    except RuntimeError:
        runner.generate_vectors()
        runner.require_generated_inputs()
