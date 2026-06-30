#!/usr/bin/env python3
"""Run the main local quality gates in the same order as a CI preflight."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> None:
    print(f">>> {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def run_hdl() -> None:
    bash = shutil.which("bash")
    if bash is None:
        raise FileNotFoundError(
            "bash was not found on PATH; run tools/run_block5_hdl_smoke.sh from a POSIX shell "
            "or install Git Bash/WSL for local HDL CI."
        )
    run([bash, "./tools/run_block5_hdl_smoke.sh"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip MkDocs/lab rebuilds and run only lint, pytest and HDL smoke.",
    )
    args = parser.parse_args()

    run([sys.executable, "-m", "ruff", "check", "blocks", "tools", "tests"])
    run([sys.executable, "-m", "pytest", "-q"])

    if not args.quick:
        run([sys.executable, "-m", "mkdocs", "build", "--strict"])
        run([sys.executable, "tools/run_all_labs.py"])

    run_hdl()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
