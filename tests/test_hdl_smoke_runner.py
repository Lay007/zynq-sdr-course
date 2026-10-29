from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


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
        "tb_qpsk_two_board_residual_cfo",
        "tb_qpsk_symbol_timing_recovery",
        "tb_qpsk_timing_recovery_mux",
        "tb_qpsk_timing_recovery_retained",
        "tb_bridge_rx_lclk_fifo",
        "tb_bpsk_zynq_ber_timing_recovery",
    }.issubset(names)
    assert all(source.is_file() for test in runner.TESTS for source in test.sources)


def test_all_generated_inputs_have_a_declared_generator() -> None:
    runner = load_runner()

    assert runner.GENERATORS
    assert all(generator.is_file() for generator in runner.GENERATORS)
    assert len(runner.REQUIRED_GENERATED_FILES) == len(set(runner.REQUIRED_GENERATED_FILES))


def test_select_tests_preserves_requested_order_and_rejects_unknown_names() -> None:
    runner = load_runner()

    selected = runner.select_tests(["tb_axis_iq_passthrough", "tb_iq_passthrough"])

    assert [test.name for test in selected] == ["tb_axis_iq_passthrough", "tb_iq_passthrough"]

    try:
        runner.select_tests(["tb_does_not_exist"])
    except ValueError as exc:
        assert "tb_does_not_exist" in str(exc)
    else:
        raise AssertionError("unknown test name was accepted")


def test_simulation_workspace_mirrors_generated_inputs(tmp_path: Path) -> None:
    runner = load_runner()

    runner.require_generated_inputs()
    runner.populate_simulation_workspace(tmp_path)

    assert all((tmp_path / path.relative_to(ROOT)).is_file() for path in runner.REQUIRED_GENERATED_FILES)
    assert not list(tmp_path.glob("*.out"))


@pytest.mark.parametrize("outcome", ["pass", "fail", "timeout"])
def test_simulation_artifacts_survive_workspace_cleanup(tmp_path, monkeypatch, outcome):
    runner = load_runner()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    artifacts = tmp_path / "artifacts"

    def simulate(command, **kwargs):
        (workspace / "wave.vcd").write_text("waveform", encoding="utf-8")
        if outcome == "timeout":
            raise subprocess.TimeoutExpired(command, 1, output=b"partial output\n", stderr=b"detail\n")
        return subprocess.CompletedProcess(command, 0, "PASS\n" if outcome == "pass" else "FAIL mismatch\n", "detail\n")

    monkeypatch.setattr(runner.subprocess, "run", simulate)
    if outcome == "pass":
        runner.run_sim(["vvp", "bench"], cwd=workspace, name="bench", timeout_s=1, artifacts_dir=artifacts)
    else:
        with pytest.raises(RuntimeError):
            runner.run_sim(["vvp", "bench"], cwd=workspace, name="bench", timeout_s=1, artifacts_dir=artifacts)
    runner.shutil.rmtree(workspace)
    assert (artifacts / "bench" / "wave.vcd").read_text(encoding="utf-8") == "waveform"
    assert "detail" in (artifacts / "bench" / "simulation.stderr.log").read_text(encoding="utf-8")
    assert (artifacts / "bench" / "simulation.stdout.log").stat().st_size > 0


def test_canonical_ci_triggers_cover_all_source_and_stimulus_dependencies():
    from fnmatch import fnmatchcase

    runner = load_runner()
    dependencies = {p for test in runner.TESTS for p in test.sources} | set(runner.STATIC_SIM_INPUTS)
    for filename in ("block5_hdl.yml", "hdl-canonical-ci.yml", "full_course_smoke.yml"):
        workflow = yaml.load((ROOT / ".github/workflows" / filename).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        for event in ("push", "pull_request"):
            patterns = workflow["on"][event]["paths"]
            uncovered = [p.relative_to(ROOT).as_posix() for p in dependencies
                         if not any(fnmatchcase(p.relative_to(ROOT).as_posix(), pattern) for pattern in patterns)]
            assert not uncovered, f"{filename}/{event} misses {uncovered}"


def test_failed_compile_keeps_diagnostics(tmp_path):
    runner = load_runner()
    with pytest.raises(subprocess.CalledProcessError):
        runner.run([sys.executable, "-c", "import sys; print('compile error', file=sys.stderr); sys.exit(1)"],
                   log_dir=tmp_path)
    assert "compile error" in (tmp_path / "compile.stderr.log").read_text(encoding="utf-8")


def test_ci_uploads_the_runners_artifact_directory_even_on_failure():
    import shlex

    for filename in ("block5_hdl.yml", "hdl-canonical-ci.yml", "full_course_smoke.yml"):
        workflow = yaml.load((ROOT / ".github/workflows" / filename).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        steps = next(iter(workflow["jobs"].values()))["steps"]
        command = next(step["run"] for step in steps if "run_block5_hdl_smoke.sh" in step.get("run", ""))
        args = shlex.split(command)
        directory = args[args.index("--artifacts-dir") + 1].rstrip("/")
        upload = next(step for step in steps if step.get("uses", "").startswith("actions/upload-artifact@"))
        assert directory in [line.rstrip("/") for line in upload["with"]["path"].splitlines()]
        assert upload["if"] == "always()"


def test_only_waveforms_changed_by_this_simulation_are_exported(tmp_path):
    runner = load_runner()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "previous.vcd").write_text("old test", encoding="utf-8")
    artifacts = tmp_path / "artifacts"
    runner.run_sim([sys.executable, "-c", "from pathlib import Path; Path('current.vcd').write_text('new test')"],
                   cwd=workspace, name="current", timeout_s=10, artifacts_dir=artifacts)
    assert (artifacts / "current/current.vcd").is_file()
    assert not (artifacts / "current/previous.vcd").exists()
