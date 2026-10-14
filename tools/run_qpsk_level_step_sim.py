#!/usr/bin/env python3
"""Simulate the board's QPSK receiver (Lab 11.45 mode) against a 20 dB level step mid-frame.

Runs blocks/block_05_fpga_hdl_flow/tb/tb_qpsk_level_step.v with Icarus Verilog for every
combination of step case (none / low / down / up), carrier offset and receiver start point
(`prev`: samples of the preceding strong frame the receiver sees before the first full frame),
with the DC blocker on and off, and prints one table. Inputs come from
blocks/block_05_fpga_hdl_flow/python/gen_qpsk_level_step.py and go to tmp/level_step/.

This is a demonstration, not a pass/fail test: with the DC blocker on, a drop after a strong
preamble is expected to fail (issue #58 follow-up, reports/hardware/ad9361-agc-frame-step-20261014.md).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from run_block5_hdl_smoke import QPSK_TOP, require_tool  # noqa: E402

TB = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "tb" / "tb_qpsk_level_step.v"
GEN = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "python" / "gen_qpsk_level_step.py"
BUILD = ROOT / "tmp" / "level_step"
RESULT = re.compile(r"RESULT case=(\w+) dc_en=(\d) received=(\d+) total_errors=(\d+) payload_errors=(\d+) "
                    r"first=(\d+) last=(\d+) mean_dc=([\d.]+) timed_out=(\d)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cases", nargs="+", default=["none", "low", "down", "up"])
    ap.add_argument("--cfo-hz", type=float, nargs="+", default=[0.0, 500.0, 3000.0])
    ap.add_argument("--prev", type=int, nargs="+", default=[0, 400, 900])
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args()

    iverilog, vvp = require_tool("iverilog"), require_tool("vvp")
    BUILD.mkdir(parents=True, exist_ok=True)
    exe = {}
    for dc in (1, 0):
        for case in args.cases:
            out = BUILD / f"tb_{dc}_{case}.vvp"
            subprocess.run([iverilog, "-g2012", f"-DDC_EN={dc}", f'-DCASE="{case}"', "-o", str(out),
                            *(str(p) for p in QPSK_TOP), str(TB)], cwd=ROOT, check=True,
                           capture_output=True)
            exe[dc, case] = out
    rows = []
    print(f"{'cfo_hz':>7} {'prev':>5} {'case':>5} | DC on: received payload_err | DC off: received payload_err")
    for cfo in args.cfo_hz:
        for prev in args.prev:
            subprocess.run([sys.executable, str(GEN), "--cfo-hz", str(cfo), "--prev", str(prev), "--lead", "50",
                            "--cases", *args.cases], cwd=ROOT, check=True, capture_output=True)
            for case in args.cases:
                res = {}
                for dc in (1, 0):
                    log = subprocess.run([vvp, str(exe[dc, case])], cwd=ROOT, check=True,
                                         capture_output=True, text=True).stdout
                    m = RESULT.search(log)
                    if not m:
                        raise RuntimeError(f"no RESULT line for case={case} dc={dc}:\n{log}")
                    res[dc] = {"received": int(m[3]), "payload_errors": int(m[5]), "mean_dc": float(m[8])}
                rows.append({"cfo_hz": cfo, "prev": prev, "case": case, "dc_on": res[1], "dc_off": res[0]})
                print(f"{cfo:7.0f} {prev:5d} {case:>5} | {res[1]['received']:8d} {res[1]['payload_errors']:11d} |"
                      f" {res[0]['received']:9d} {res[0]['payload_errors']:11d}")
    if args.json_out:
        args.json_out.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
