#!/usr/bin/env python3
"""Cross-platform task runner for local course workflows."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TB_DIR = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "tb"
RTL_DIR = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "rtl"
DOCS_ASSETS_DIR = ROOT / "docs" / "assets"
DATASET_MANIFESTS_DIR = ROOT / "datasets" / "manifests"

GENERATED_DOC_ASSET_PATTERNS = (
    "course_reproducibility_summary.json",
    "course_reproducibility_summary.md",
    "lab21_*.png",
    "lab21_*.json",
    "lab22_*.png",
    "lab22_*.json",
    "lab23_*.png",
    "lab23_*.json",
    "lab35_*.png",
    "lab35_*.json",
    "lab36_*.png",
    "lab36_*.json",
    "lab37_*.png",
    "lab37_*.json",
    "lab43_*.png",
    "lab43_*.json",
    "lab43_*.md",
    "lab44_*.png",
    "lab44_*.json",
    "lab64_*.png",
    "lab64_*.json",
    "lab73_*.png",
    "lab73_*.json",
    "lab75_*.png",
    "lab75_*.json",
    "lab84_*.png",
    "lab84_*.json",
    "lab93_*.png",
    "lab93_*.json",
    "lab117_*.json",
    "end_to_end_tone_*.png",
    "end_to_end_tone_*.json",
    "end_to_end_bpsk_reference_*.png",
    "end_to_end_bpsk_reference_*.json",
)

GENERATED_TB_FILENAMES = (
    "fir_iq_4tap_input_vectors.txt",
    "fir_iq_4tap_expected_vectors.txt",
    "nco_mixer_iq_input_vectors.txt",
    "nco_mixer_iq_expected_vectors.txt",
    "bpsk_symbol_mapper_input_vectors.txt",
    "bpsk_symbol_mapper_expected_vectors.txt",
    "bpsk_upsampler_8x_input_vectors.txt",
    "bpsk_upsampler_8x_expected_vectors.txt",
    "bpsk_rrc_tx_fir_input_vectors.txt",
    "bpsk_rrc_tx_fir_expected_vectors.txt",
    "bpsk_rx_bit_recovery_input_vectors.txt",
    "bpsk_rx_bit_recovery_expected_bits.txt",
    "bpsk_rx_bit_recovery_meta.txt",
    "bpsk_framed_loopback_input_bits.txt",
    "bpsk_framed_loopback_expected_bits.txt",
    "bpsk_framed_loopback_meta.txt",
    "qpsk_timing_recovery_mf_input.mem",
    "qpsk_timing_recovery_expected.mem",
    "qpsk_timing_recovery_meta.txt",
    "qpsk_chain_drift_rx.mem",
)

GENERATED_RTL_FILENAMES = (
    "bpsk_rrc_tx_fir_taps.mem",
    "bpsk_frame_bits.mem",
)

LEGACY_ROOT_TB_PATTERNS = (
    "tb_*.out",
    "tb_*.vcd",
)

GENERATED_DATASET_FILENAMES = (
    "end_to_end_tone_demo_v1.yml",
    "end_to_end_bpsk_reference_v1.yml",
)

GENERATED_CAPTURE_DIRS = (
    ROOT / "blocks" / "block_09_recording_and_analysis_tools" / "assets" / "lab93_multiformat",
)

GENERATED_CAPTURE_FILENAMES = (
    ROOT / "blocks" / "block_11_integrated_sdr_project" / "assets" / "end_to_end_tone_demo" / "end_to_end_tone_demo_v1.ci16",
    ROOT / "blocks" / "block_11_integrated_sdr_project" / "assets" / "end_to_end_bpsk_reference" / "end_to_end_bpsk_reference_v1.ci16",
    ROOT / "blocks" / "block_11_integrated_sdr_project" / "assets" / "end_to_end_bpsk_reference" / "end_to_end_bpsk_reference_v1_tx_reference.ci16",
)

GENERATED_PACKAGE_FILENAMES = (
    ROOT / "blocks" / "block_11_integrated_sdr_project" / "assets" / "end_to_end_bpsk_reference" / "config.json",
    ROOT / "blocks" / "block_11_integrated_sdr_project" / "assets" / "end_to_end_bpsk_reference" / "handoff_files.json",
    ROOT / "blocks" / "block_11_integrated_sdr_project" / "assets" / "end_to_end_bpsk_reference" / "manifest.yml",
    ROOT / "blocks" / "block_11_integrated_sdr_project" / "assets" / "end_to_end_bpsk_reference" / "rrc_taps_float.txt",
    ROOT / "blocks" / "block_11_integrated_sdr_project" / "assets" / "end_to_end_bpsk_reference" / "rrc_taps_q15.txt",
    ROOT / "blocks" / "block_11_integrated_sdr_project" / "assets" / "end_to_end_bpsk_reference" / "sample_plan.json",
    ROOT / "blocks" / "block_11_integrated_sdr_project" / "assets" / "end_to_end_bpsk_reference" / "tx_bits.txt",
    ROOT / "blocks" / "block_11_integrated_sdr_project" / "assets" / "end_to_end_bpsk_reference" / "tx_symbols_float.txt",
    ROOT / "blocks" / "block_11_integrated_sdr_project" / "assets" / "end_to_end_bpsk_reference" / "tx_symbols_q15.txt",
)

GENERATED_ROOT_DIRS = (
    ROOT / "site",
    ROOT / ".pytest_cache",
    ROOT / ".ruff_cache",
)


def run(cmd: list[str], *, cwd: Path = ROOT) -> None:
    print(f">>> {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True)


def remove_tree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def is_git_tracked(path: Path) -> bool:
    """Return whether Git tracks path, so clean never deletes repository evidence."""
    try:
        relative = path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        raise ValueError(f"Refusing to inspect path outside repository: {path}") from None
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def remove_generated_file(path: Path) -> bool:
    if not path.exists() or is_git_tracked(path):
        return False
    path.unlink()
    return True


def remove_untracked_tree(path: Path) -> None:
    """Remove generated files below path while preserving any tracked evidence."""
    if not path.exists():
        return
    for candidate in sorted(path.rglob("*"), reverse=True):
        if candidate.is_file() or candidate.is_symlink():
            remove_generated_file(candidate)
        elif candidate.is_dir():
            try:
                candidate.rmdir()
            except OSError:
                pass
    try:
        path.rmdir()
    except OSError:
        pass


def task_install() -> None:
    run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])


def task_docs() -> None:
    run([sys.executable, "-m", "mkdocs", "build", "--strict"])


def task_serve() -> None:
    run([sys.executable, "-m", "mkdocs", "serve"])


def task_labs() -> None:
    run([sys.executable, "tools/run_all_labs.py"])


def task_hdl() -> None:
    run([sys.executable, "tools/run_block5_hdl_smoke.py"])


def task_test() -> None:
    run([sys.executable, "-m", "pytest", "-q"])


def task_lint() -> None:
    run([sys.executable, "-m", "ruff", "check", "blocks", "tools", "tests"])


def task_matlab_bpsk() -> None:
    matlab = shutil.which("matlab")
    if matlab is None:
        raise FileNotFoundError("matlab was not found on PATH")
    run(
        [
            matlab,
            "-batch",
            "lab_4_4_run_bpsk_simulink_models",
        ],
        cwd=ROOT / "blocks" / "block_04_simulink_and_fixed_point" / "matlab",
    )


def task_smoke() -> None:
    task_docs()
    task_labs()
    task_hdl()


def task_clean() -> None:
    for directory in GENERATED_ROOT_DIRS:
        remove_untracked_tree(directory)

    for pycache_dir in ROOT.rglob("__pycache__"):
        if pycache_dir.is_dir():
            remove_tree(pycache_dir)

    for pattern in ("*.out", "*.vcd"):
        for artifact in TB_DIR.glob(pattern):
            remove_generated_file(artifact)

    for pattern in LEGACY_ROOT_TB_PATTERNS:
        for artifact in ROOT.glob(pattern):
            remove_generated_file(artifact)

    for filename in GENERATED_TB_FILENAMES:
        artifact = TB_DIR / filename
        remove_generated_file(artifact)

    for filename in GENERATED_RTL_FILENAMES:
        artifact = RTL_DIR / filename
        remove_generated_file(artifact)

    if DOCS_ASSETS_DIR.exists():
        for pattern in GENERATED_DOC_ASSET_PATTERNS:
            for artifact in DOCS_ASSETS_DIR.glob(pattern):
                remove_generated_file(artifact)

    if DATASET_MANIFESTS_DIR.exists():
        for filename in GENERATED_DATASET_FILENAMES:
            artifact = DATASET_MANIFESTS_DIR / filename
            remove_generated_file(artifact)

        if not any(DATASET_MANIFESTS_DIR.iterdir()):
            DATASET_MANIFESTS_DIR.rmdir()

    for directory in GENERATED_CAPTURE_DIRS:
        remove_untracked_tree(directory)

    for artifact in GENERATED_CAPTURE_FILENAMES:
        remove_generated_file(artifact)

    for artifact in GENERATED_PACKAGE_FILENAMES:
        remove_generated_file(artifact)

    print("Clean completed.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local course tasks.")
    parser.add_argument(
        "task",
        choices=("install", "docs", "serve", "labs", "hdl", "test", "lint", "matlab-bpsk", "smoke", "clean"),
        help="Task to execute.",
    )
    args = parser.parse_args()

    actions = {
        "install": task_install,
        "docs": task_docs,
        "serve": task_serve,
        "labs": task_labs,
        "hdl": task_hdl,
        "test": task_test,
        "lint": task_lint,
        "matlab-bpsk": task_matlab_bpsk,
        "smoke": task_smoke,
        "clean": task_clean,
    }
    actions[args.task]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
