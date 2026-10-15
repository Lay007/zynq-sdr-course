#!/usr/bin/env python3
"""Issue #68: does the receiver find a packet sent once, after silence? Fixed window vs listen mode.

Runs blocks/block_05_fpga_hdl_flow/tb/tb_qpsk_listen.v (qpsk_zynq_ber_top with the gpreg bridge
parameters, Lab 11.45 mode) on streams from gen_qpsk_burst_stream.py: one frame, then silence
with noise, cyclic, at the levels measured on board B (noise 16 counts rms at 71 dB; the frame
peak at TX -30 dB is about 590 counts, at TX -50 dB about 80). Each reception starts at a
pseudo-random point of the stream; each period's frame starts at a random sample (random symbol
timing phase). Burst formats (two_board_burst.burst_iq): no reference, one reference symbol, or
a 32-symbol training lead-in plus the reference. A noise-only stream checks that a listening attempt with no
packet ends by itself (timeout) once the 65535-symbol window is used up. Cases run in parallel;
one table is printed.
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

TB = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "tb" / "tb_qpsk_listen.v"
GEN = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "python" / "gen_qpsk_burst_stream.py"
BUILD = ROOT / "tmp" / "listen"
RESULT = re.compile(r"RESULT file=(\S+) listen=(\d) bursts=(\d+) locked=(\d+) clean=(\d+) gross=(\d+) "
                    r"payload_errors=(\d+)/(\d+) timeouts=(\d+) hung=(\d+) mean_fed=(\d+)")
FRAME = 152 * 8

# name: (generator args, listen, bursts, max samples fed per reception)
CASES = {
    "gap 19, fixed window": (["--gap", "19", "--ref", "--jitter"], 0, 20, 700000),
    "gap 19, listen, no reference": (["--gap", "19", "--jitter"], 1, 20, 700000),
    "gap 19, listen, reference only": (["--gap", "19", "--ref", "--jitter"], 1, 20, 700000),
    "gap 4, listen, reference only": (["--gap", "4", "--ref", "--jitter", "--periods", "16"], 1, 30, 700000),
    "gap 4, listen, lead 32": (["--gap", "4", "--lead", "32", "--jitter", "--periods", "16"], 1, 30, 700000),
    "gap 19, listen, lead 32": (["--gap", "19", "--lead", "32", "--jitter"], 1, 20, 700000),
    "gap 99, listen, lead 32": (["--gap", "99", "--periods", "2", "--lead", "32", "--jitter"], 1, 10, 700000),
    "gap 19, weak, listen, lead 32": (["--gap", "19", "--peak", "80", "--lead", "32", "--jitter"], 1, 20, 700000),
    "noise only, listen": (["--gap", "-1", "--samples", str(4 * FRAME * 20)], 1, 1, 700000),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cases", nargs="+", default=list(CASES))
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args()

    iverilog, vvp = require_tool("iverilog"), require_tool("vvp")
    BUILD.mkdir(parents=True, exist_ok=True)
    jobs = []
    for k, name in enumerate(args.cases):
        gen, listen, bursts, max_feed = CASES[name]
        mem = f"listen_case{k}.mem"
        out = subprocess.run([sys.executable, str(GEN), *gen, "--name", mem], cwd=ROOT, check=True,
                             capture_output=True, text=True).stdout.split()
        ns = int(out[1])
        vvp_out = BUILD / f"listen_case{k}.vvp"
        subprocess.run([iverilog, "-g2012", f"-DLISTEN={listen}", f"-DBURSTS={bursts}", f"-DMAX_FEED={max_feed}",
                        f"-DNS={ns}", f'-DFILE="{mem}"', "-o", str(vvp_out), *(str(p) for p in QPSK_TOP), str(TB)],
                       cwd=ROOT, check=True, capture_output=True)
        jobs.append((name, vvp_out))

    def run(job):
        name, out = job
        log = subprocess.run([vvp, str(out)], cwd=ROOT, check=True, capture_output=True, text=True).stdout
        m = RESULT.search(log)
        if not m:
            raise RuntimeError(f"no RESULT line for {name}:\n{log}")
        return {"case": name, "listen": int(m[2]), "bursts": int(m[3]), "locked": int(m[4]), "clean": int(m[5]),
                "gross": int(m[6]), "payload_errors": int(m[7]), "payload_bits": int(m[8]), "timeouts": int(m[9]),
                "hung": int(m[10]), "mean_samples_fed": int(m[11])}

    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        rows = list(pool.map(run, jobs))
    print(f"{'case':>34} | receptions locked clean gross timeouts payload_errors mean_wait_frames")
    for r in rows:
        print(f"{r['case']:>34} | {r['bursts']:10d} {r['locked']:6d} {r['clean']:5d} {r['gross']:5d} {r['timeouts']:8d} "
              f"{r['payload_errors']:6d}/{r['payload_bits']:<6d} {r['mean_samples_fed'] / FRAME:8.1f}")
    if args.json_out:
        args.json_out.write_text(json.dumps({"rows": rows}, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
