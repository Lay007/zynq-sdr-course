#!/usr/bin/env python3
"""Sweep the carrier frequency offset through the pilot-corrected OFDM RTL loopback.

For each offset, tb_ofdm_tx_rx_pilot_corrected_loopback.sv is compiled with
CFO_PPM (offset in 1e-6 cycles per sample), run with Icarus Verilog, and its RESULT
line is read: bit errors, and the tracker's phase for the last symbol. The phase is
printed next to the float model from ofdm_cfo_pilot_bias.py, so the table shows both
where the common-phase correction stops being enough and that the RTL estimate
follows the float model, bias included. Simulation only.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from ofdm_cfo_pilot_bias import pilot_phase

ROOT = Path(__file__).resolve().parents[1]
BLOCK = ROOT / "blocks/block_08_modulation_and_synchronization"
BENCH = "tb_ofdm_tx_rx_pilot_corrected_loopback"
RESULT_RE = re.compile(r"RESULT .*bit_errors=(\d+) bits=(\d+) phase=(-?\d+)")


def run_point(work: Path, angle_deg: int, cfo_ppm: int, symbols: int) -> tuple[int, int, int]:
    output = work / f"cfo_{cfo_ppm}.vvp"
    sources = sorted((BLOCK / "rtl").glob("ofdm_*.v"))
    subprocess.run(
        ["iverilog", "-g2012", "-s", BENCH,
         f"-P{BENCH}.ANGLE_DEG={angle_deg}", f"-P{BENCH}.CFO_PPM={cfo_ppm}", f"-P{BENCH}.SYMBOLS={symbols}",
         "-o", str(output), *map(str, sources), str(BLOCK / "tb" / f"{BENCH}.sv")],
        cwd=ROOT, check=True, timeout=120,
    )
    # The bench exits non-zero when bits are wrong; that is a data point here.
    run = subprocess.run(["vvp", "-n", str(output)], cwd=ROOT, capture_output=True, text=True, timeout=600)
    match = RESULT_RE.search(run.stdout)
    if not match:
        raise SystemExit(f"no RESULT line for CFO {cfo_ppm} ppm:\n{run.stdout[-2000:]}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--angle-deg", type=int, default=30)
    parser.add_argument("--symbols", type=int, default=8)
    parser.add_argument("--ppm", type=int, nargs="+", default=[0, 1000, 2000, 4000, 5000, 6000, 7000, 8000])
    args = parser.parse_args()
    for command in ("iverilog", "vvp"):
        if shutil.which(command) is None:
            raise SystemExit(f"{command} is required; install Icarus Verilog")

    print(f"Pilot-corrected OFDM RTL loopback, channel {args.angle_deg} deg, {args.symbols} symbols "
          "(phase units: pi = 2^15)")
    print("   CFO ppm   CFO / subcarrier spacing   bit errors   RTL phase   float-model phase   phase step / symbol (deg)")
    with TemporaryDirectory(prefix="course-ofdm-cfo-") as temporary:
        for ppm in args.ppm:
            errors, bits, phase = run_point(Path(temporary), args.angle_deg, ppm, args.symbols)
            model = pilot_phase(args.angle_deg, ppm, args.symbols)["estimate"]
            print(f"{ppm:10d} {ppm * 1e-6 * 64:26.3f} {errors:7d}/{bits:<5d} {phase:10d} {model:19.1f} "
                  f"{ppm * 1e-6 * 80 * 360:25.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
