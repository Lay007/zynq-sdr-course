#!/usr/bin/env python3
"""Run every committed OFDM testbench locally with the CI simulator."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
BLOCK = ROOT / "blocks/block_08_modulation_and_synchronization"


def main() -> int:
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
                ["iverilog", "-g2012", "-Wall", "-s", bench.stem, "-o", str(output),
                 *map(str, sources), str(bench)], cwd=ROOT, check=True, timeout=60,
            )
            subprocess.run(["vvp", str(output)], cwd=ROOT, check=True, timeout=120)
    print(f"OFDM RTL: {len(benches)} testbenches passed (simulation only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
