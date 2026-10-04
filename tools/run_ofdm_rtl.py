#!/usr/bin/env python3
"""Run every committed OFDM testbench locally with the CI simulator."""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
BLOCK = ROOT / "blocks/block_08_modulation_and_synchronization"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="build the IFFT/FFT with the one-cycle baseline butterfly (OFDM_IFFT_PIPELINED=0)",
    )
    parser.add_argument(
        "--fabric",
        action="store_true",
        help="keep the pipelined IFFT/FFT working memory in fabric logic instead of block RAM (OFDM_IFFT_BRAM=0)",
    )
    args = parser.parse_args()
    # The one-cycle baseline always uses fabric memory (block RAM needs the pipelined schedule).
    defines = ["-DOFDM_IFFT_PIPELINED=0"] if args.baseline else []
    if args.fabric:
        defines.append("-DOFDM_IFFT_BRAM=0")
    for command in ("iverilog", "vvp"):
        if shutil.which(command) is None:
            raise SystemExit(f"{command} is required; install Icarus Verilog")
    sources = sorted((BLOCK / "rtl").glob("ofdm_*.v"))
    benches = sorted((BLOCK / "tb").glob("tb_ofdm_*.sv"))
    if not sources or not benches:
        raise SystemExit("OFDM sources/testbenches are missing")
    with TemporaryDirectory(prefix="course-ofdm-") as temporary:
        for bench in benches:
            output = Path(temporary) / f"{bench.stem}.vvp"
            subprocess.run(
                ["iverilog", "-g2012", "-Wall", *defines, "-s", bench.stem, "-o", str(output),
                 *map(str, sources), str(bench)], cwd=ROOT, check=True, timeout=60,
            )
            subprocess.run(["vvp", str(output)], cwd=ROOT, check=True, timeout=120)
    mode = "baseline, fabric memory" if args.baseline else (
        "pipelined, fabric memory" if args.fabric else "pipelined, block-RAM memory")
    print(f"OFDM RTL ({mode} IFFT/FFT): {len(benches)} testbenches passed (simulation only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
