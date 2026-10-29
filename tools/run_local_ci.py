#!/usr/bin/env python3
"""Run the main local quality gates in the same order as a CI preflight."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTEST_BASETEMP = ROOT / ".pytest-tmp-local-ci"


def run(cmd: list[str]) -> None:
    print(f">>> {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def run_hdl() -> None:
    run([sys.executable, "tools/run_block5_hdl_smoke.py"])
    run([sys.executable, "tools/run_block8_css_rtl.py"])
    run([sys.executable, "tools/run_ofdm_rtl.py"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--quick",
        action="store_true",
        help="Skip MkDocs/lab rebuilds and run only lint, pytest and HDL smoke.",
    )
    modes.add_argument("--software-only", action="store_true", help="Run lint, registry and pytest without HDL or rebuilds.")
    modes.add_argument("--hdl-only", action="store_true", help="Run Block 5, CSS and OFDM simulation only; requires Icarus.")
    args = parser.parse_args()

    if args.hdl_only:
        run_hdl()
        return 0

    run([sys.executable, "-m", "ruff", "check", "blocks", "tools", "tests"])
    run([sys.executable, "tools/check_lab_id_registry.py"])
    # Keep pytest's numbered temporary directories inside the repository. On
    # Windows the shared user temp root can retain a locked ``pytest-current``
    # junction and turn a successful test run into a cleanup failure.
    run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--basetemp",
            str(PYTEST_BASETEMP),
        ]
    )

    if not (args.quick or args.software_only):
        run([sys.executable, "-m", "mkdocs", "build", "--strict"])
        run([sys.executable, "tools/run_all_labs.py"])

    if not args.software_only:
        run_hdl()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
