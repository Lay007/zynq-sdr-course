#!/usr/bin/env python3
"""Cross-platform task runner for local course workflows."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TB_DIR = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "tb"
RTL_DIR = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "rtl"
PY_DIR = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "python"
DOCS_ASSETS_DIR = ROOT / "docs" / "assets"
DATASET_MANIFESTS_DIR = ROOT / "datasets" / "manifests"

GENERATED_DOC_ASSET_PATTERNS = (
    "course_reproducibility_summary.json",
    "course_reproducibility_summary.md",
    "lab35_*.png",
    "lab35_*.json",
    "lab36_*.png",
    "lab36_*.json",
    "lab37_*.png",
    "lab37_*.json",
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
    "end_to_end_tone_*.png",
    "end_to_end_tone_*.json",
)

GENERATED_TB_FILENAMES = (
    "fir_iq_4tap_input_vectors.txt",
    "fir_iq_4tap_expected_vectors.txt",
    "nco_mixer_iq_input_vectors.txt",
    "nco_mixer_iq_expected_vectors.txt",
)

LEGACY_ROOT_TB_PATTERNS = (
    "tb_*.out",
    "tb_*.vcd",
)

GENERATED_DATASET_FILENAMES = (
    "end_to_end_tone_demo_v1.yml",
)


def run(cmd: list[str], *, cwd: Path = ROOT) -> None:
    print(f">>> {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True)


def task_install() -> None:
    run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])


def task_docs() -> None:
    run([sys.executable, "-m", "mkdocs", "build", "--strict"])


def task_serve() -> None:
    run([sys.executable, "-m", "mkdocs", "serve"])


def task_labs() -> None:
    run([sys.executable, "tools/run_all_labs.py"])


def task_hdl() -> None:
    run(
        [
            "iverilog",
            "-g2012",
            "-o",
            str(TB_DIR / "tb_iq_passthrough.out"),
            str(RTL_DIR / "iq_passthrough.v"),
            str(TB_DIR / "tb_iq_passthrough.v"),
        ]
    )
    run(["vvp", str(TB_DIR / "tb_iq_passthrough.out")])

    run([sys.executable, str(PY_DIR / "generate_fir_iq_4tap_vectors.py")])
    run(
        [
            "iverilog",
            "-g2012",
            "-o",
            str(TB_DIR / "tb_fir_iq_4tap.out"),
            str(RTL_DIR / "fir_iq_4tap.v"),
            str(TB_DIR / "tb_fir_iq_4tap.v"),
        ]
    )
    run(["vvp", str(TB_DIR / "tb_fir_iq_4tap.out")])

    run([sys.executable, str(PY_DIR / "generate_nco_mixer_iq_vectors.py")])
    run(
        [
            "iverilog",
            "-g2012",
            "-o",
            str(TB_DIR / "tb_nco_mixer_iq.out"),
            str(RTL_DIR / "nco_mixer_iq.v"),
            str(TB_DIR / "tb_nco_mixer_iq.v"),
        ]
    )
    run(["vvp", str(TB_DIR / "tb_nco_mixer_iq.out")])

    run(
        [
            "iverilog",
            "-g2012",
            "-o",
            str(TB_DIR / "tb_axis_iq_passthrough.out"),
            str(RTL_DIR / "axis_iq_passthrough.v"),
            str(TB_DIR / "tb_axis_iq_passthrough.v"),
        ]
    )
    run(["vvp", str(TB_DIR / "tb_axis_iq_passthrough.out")])


def task_smoke() -> None:
    task_docs()
    task_labs()
    task_hdl()


def task_clean() -> None:
    site_dir = ROOT / "site"
    if site_dir.exists():
        for path in sorted(site_dir.rglob("*"), reverse=True):
            if path.is_file() or path.is_symlink():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        site_dir.rmdir()

    for pattern in ("*.out", "*.vcd"):
        for artifact in TB_DIR.glob(pattern):
            artifact.unlink()

    for pattern in LEGACY_ROOT_TB_PATTERNS:
        for artifact in ROOT.glob(pattern):
            artifact.unlink()

    for filename in GENERATED_TB_FILENAMES:
        artifact = TB_DIR / filename
        if artifact.exists():
            artifact.unlink()

    if DOCS_ASSETS_DIR.exists():
        for pattern in GENERATED_DOC_ASSET_PATTERNS:
            for artifact in DOCS_ASSETS_DIR.glob(pattern):
                artifact.unlink()

    if DATASET_MANIFESTS_DIR.exists():
        for filename in GENERATED_DATASET_FILENAMES:
            artifact = DATASET_MANIFESTS_DIR / filename
            if artifact.exists():
                artifact.unlink()

        if not any(DATASET_MANIFESTS_DIR.iterdir()):
            DATASET_MANIFESTS_DIR.rmdir()

    print("Clean completed.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local course tasks.")
    parser.add_argument(
        "task",
        choices=("install", "docs", "serve", "labs", "hdl", "smoke", "clean"),
        help="Task to execute.",
    )
    args = parser.parse_args()

    actions = {
        "install": task_install,
        "docs": task_docs,
        "serve": task_serve,
        "labs": task_labs,
        "hdl": task_hdl,
        "smoke": task_smoke,
        "clean": task_clean,
    }
    actions[args.task]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
