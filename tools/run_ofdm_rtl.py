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

# Benches run a second time with parameter overrides (iverilog -P), besides their default run.
VARIANTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    # the board's sample domain: 62.5 MHz divided clock, DAC request and ADC strobe every 30 clocks
    # (2.083 MS/s) 17 clocks apart, and a 3 kHz carrier offset
    ("tb_ofdm_radio_core", ("SCLK_HALF_NS=8", "STROBE=30", "RX_PHASE=17", "CFO_HZ=3000.0")),
    # beyond the modem's own CFO range (+-16.3 kHz): only the preamble's coarse correction saves it
    ("tb_ofdm_radio_core", ("SCLK_HALF_NS=8", "STROBE=30", "RX_PHASE=17", "CFO_HZ=-28000.0")),
    # 20 dB below the default level: the level normalization brings it back (gain 2^(5/2))
    ("tb_ofdm_radio_core", ("SCLK_HALF_NS=8", "STROBE=30", "RX_PHASE=17", "CFO_HZ=3000.0", "CHANNEL_GAIN=0.1")),
    # Both at once needs the DC tracker settled first (SETTLE_SAMPLES=4096, about 3 minutes here):
    # run by hand, see reports/fpga/ofdm-frame-sync-rtl-sim-20261019.md.
)


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
        for name, params in VARIANTS:
            bench = BLOCK / "tb" / f"{name}.sv"
            output = Path(temporary) / f"{name}_variant.vvp"
            overrides = [f"-P{name}.{p}" for p in params]
            print(f"{name} with {' '.join(params)}")
            subprocess.run(
                ["iverilog", "-g2012", "-Wall", *defines, *overrides, "-s", name, "-o", str(output),
                 *map(str, sources), str(bench)], cwd=ROOT, check=True, timeout=60,
            )
            subprocess.run(["vvp", str(output)], cwd=ROOT, check=True, timeout=120)
    mode = "baseline, fabric memory" if args.baseline else (
        "pipelined, fabric memory" if args.fabric else "pipelined, block-RAM memory")
    print(f"OFDM RTL ({mode} IFFT/FFT): {len(benches)} testbenches and {len(VARIANTS)} parameter variant(s) "
          "passed (simulation only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
