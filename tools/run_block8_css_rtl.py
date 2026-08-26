#!/usr/bin/env python3
"""Generate vectors and run the canonical Block 8 CSS RTL regressions."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLOCK_DIR = ROOT / "blocks" / "block_08_modulation_and_synchronization"
RTL_DIR = BLOCK_DIR / "rtl"
TB_DIR = BLOCK_DIR / "tb"
GENERATOR = BLOCK_DIR / "python" / "generate_css_sf7_detector_vectors.py"
FAIL_RE = re.compile(r"\bFAIL\b")


@dataclass(frozen=True)
class HdlTest:
    name: str
    sources: tuple[Path, ...]
    timeout_s: float = 30.0


TESTS = (
    HdlTest(
        "tb_css_dechirp_mul",
        (RTL_DIR / "css_dechirp_mul.v", TB_DIR / "tb_css_dechirp_mul.sv"),
    ),
    HdlTest(
        "tb_css_sf7_dechirp_frontend",
        (
            RTL_DIR / "css_dechirp_mul.v",
            RTL_DIR / "css_sf7_ref_rom.v",
            RTL_DIR / "css_sf7_dechirp_frontend.v",
            TB_DIR / "tb_css_sf7_dechirp_frontend.sv",
        ),
    ),
    HdlTest(
        "tb_css_symbol_buffer",
        (
            RTL_DIR / "css_symbol_buffer.v",
            TB_DIR / "tb_css_symbol_buffer.sv",
        ),
    ),
    HdlTest(
        "tb_css_sf7_sequential_detector",
        (
            RTL_DIR / "css_dechirp_mul.v",
            RTL_DIR / "css_sf7_ref_rom.v",
            RTL_DIR / "css_sf7_dechirp_frontend.v",
            RTL_DIR / "css_q15_rom.v",
            RTL_DIR / "css_sf7_sequential_detector.v",
            TB_DIR / "tb_css_sf7_sequential_detector.sv",
        ),
        timeout_s=180.0,
    ),
)


def require_tool(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise FileNotFoundError(f"{name} was not found on PATH")
    return executable


def select_tests(names: list[str] | None) -> tuple[HdlTest, ...]:
    if not names:
        return TESTS
    by_name = {test.name: test for test in TESTS}
    unknown = [name for name in names if name not in by_name]
    if unknown:
        raise ValueError(f"Unknown CSS RTL test(s): {', '.join(unknown)}")
    return tuple(by_name[name] for name in names)


def run_tests(*, generate: bool = True, names: list[str] | None = None) -> None:
    iverilog = require_tool("iverilog")
    vvp = require_tool("vvp")
    if generate:
        subprocess.run([sys.executable, str(GENERATOR)], cwd=ROOT, check=True)

    selected = select_tests(names)
    with tempfile.TemporaryDirectory(prefix="zynq-sdr-css-rtl-") as temporary_dir:
        workspace = Path(temporary_dir)
        for test in selected:
            missing = [str(path.relative_to(ROOT)) for path in test.sources if not path.is_file()]
            if missing:
                raise FileNotFoundError(f"{test.name}: missing sources: {', '.join(missing)}")

            output = workspace / f"{test.name}.out"
            compile_command = [
                iverilog,
                "-g2012",
                "-Wall",
                "-s",
                test.name,
                "-o",
                str(output),
                *(str(path) for path in test.sources),
            ]
            print(f">>> {' '.join(compile_command)}", flush=True)
            subprocess.run(compile_command, cwd=ROOT, check=True, timeout=30)

            result = subprocess.run(
                [vvp, str(output)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                timeout=test.timeout_s,
            )
            sys.stdout.write(result.stdout)
            if result.stderr:
                sys.stderr.write(result.stderr)
            failures = [line for line in result.stdout.splitlines() if FAIL_RE.search(line)]
            if failures:
                raise RuntimeError(
                    f"{test.name}: testbench reported failure:\n  " + "\n  ".join(failures)
                )
            print(f"PASS {test.name}", flush=True)

    print(f"Block 8 CSS RTL passed: {len(selected)} testbenches.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-generate", action="store_true")
    parser.add_argument("--test", action="append", dest="tests")
    args = parser.parse_args()
    run_tests(generate=not args.no_generate, names=args.tests)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
