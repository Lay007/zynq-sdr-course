#!/usr/bin/env python3
"""Many receptions from one continuous stream: the DC blocker kept across frames vs reset per frame.

Runs blocks/block_05_fpga_hdl_flow/tb/tb_qpsk_dc_bursts.v (qpsk_zynq_ber_top with the gpreg bridge
parameters, Lab 11.45 mode) for two streams that board A transmits on the two-board bench: a steady
level and a 20 dB drop at symbol 60 every 8 frames with a slow return. Three receiver settings:
DC blocker kept across frames (DC_PERSIST = 1, the default since issue #66), DC blocker reset at
every frame (DC_PERSIST = 0, the behaviour before), and DC blocker off. Prints one table.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from run_block5_hdl_smoke import QPSK_TOP, require_tool  # noqa: E402

TB = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "tb" / "tb_qpsk_dc_bursts.v"
GEN = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "python" / "gen_qpsk_level_step.py"
BUILD = ROOT / "tmp" / "level_step"
RESULT = re.compile(r"RESULT stream=(\w+) dc_en=(\d) persist=(\d) bursts=(\d+) locked=(\d+) clean=(\d+) "
                    r"gross=(\d+) payload_errors=(\d+)/(\d+) hung=(\d+)")
SETTINGS = {"kept across frames": (1, 1), "reset every frame": (1, 0), "DC blocker off": (0, 1)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bursts", type=int, default=80)
    ap.add_argument("--cfo-hz", type=float, default=500.0)
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args()

    iverilog, vvp = require_tool("iverilog"), require_tool("vvp")
    BUILD.mkdir(parents=True, exist_ok=True)
    streams = ("steady", "saw_down")
    for s in streams:
        subprocess.run([sys.executable, str(GEN), "--stream", s, "--samples", "200000", "--cfo-hz", str(args.cfo_hz)],
                       cwd=ROOT, check=True, capture_output=True)
    jobs = []
    for s in streams:
        for name, (dc, persist) in SETTINGS.items():
            out = BUILD / f"bursts_{s}_{dc}{persist}.vvp"
            subprocess.run([iverilog, "-g2012", f"-DDC_EN={dc}", f"-DPERSIST={persist}", f'-DSTREAM="{s}"',
                            f"-DBURSTS={args.bursts}", "-o", str(out), *(str(p) for p in QPSK_TOP), str(TB)],
                           cwd=ROOT, check=True, capture_output=True)
            jobs.append((s, name, out))

    def run(job):
        s, name, out = job
        log = subprocess.run([vvp, str(out)], cwd=ROOT, check=True, capture_output=True, text=True).stdout
        m = RESULT.search(log)
        if not m:
            raise RuntimeError(f"no RESULT line for {s} / {name}:\n{log}")
        return {"stream": s, "setting": name, "bursts": int(m[4]), "locked": int(m[5]), "clean": int(m[6]),
                "gross": int(m[7]), "payload_errors": int(m[8]), "payload_bits": int(m[9]), "hung": int(m[10])}

    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        rows = list(pool.map(run, jobs))
    print(f"{'stream':>9} {'setting':>20} | locked clean gross payload_errors")
    for r in rows:
        print(f"{r['stream']:>9} {r['setting']:>20} | {r['locked']:6d} {r['clean']:5d} {r['gross']:5d} "
              f"{r['payload_errors']:6d}/{r['payload_bits']}")
    if args.json_out:
        args.json_out.write_text(json.dumps({"cfo_hz": args.cfo_hz, "rows": rows}, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
