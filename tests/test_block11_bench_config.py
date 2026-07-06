from __future__ import annotations

import importlib
import sys
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1] / "blocks" / "block_11_integrated_sdr_project" / "python"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import bench_config  # noqa: E402


def test_bench_defaults_can_be_overridden_from_environment(monkeypatch) -> None:
    with monkeypatch.context() as context:
        context.setenv("ZYNQ_SSH_HOST", "10.20.30.40")
        context.setenv("ZYNQ_SSH_USER", "operator")
        context.setenv("ZYNQ_SSH_PASSWORD", "test-secret")
        context.setenv("ZYNQ_SSH_PORT", "2222")
        context.setenv("ZYNQ_SSH_TIMEOUT_S", "4.5")
        context.delenv("ZYNQ_IIO_URI", raising=False)

        config = importlib.reload(bench_config)

        assert config.DEFAULT_HOST == "10.20.30.40"
        assert config.DEFAULT_USER == "operator"
        assert config.DEFAULT_PASSWORD == "test-secret"
        assert config.DEFAULT_PORT == 2222
        assert config.DEFAULT_TIMEOUT_S == 4.5
        assert config.DEFAULT_IIO_URI == "ip:10.20.30.40"

    importlib.reload(bench_config)
