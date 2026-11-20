#!/usr/bin/env python3
"""Check three FIR schedules against common deterministic integer vectors."""

import argparse
import random
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCK = ROOT / "blocks/block_05_fpga_hdl_flow"
MODES = ("parallel", "folded", "pipelined")
SEED = 94


def golden(samples, taps):
    results = []
    for index in range(len(samples)):
        acc = sum(samples[index - k] * h for k, h in enumerate(taps) if k <= index)
        results.append(max(-32768, min(32767, (acc + 16384) // 32768)))
    return results


def make_vectors(path: Path) -> None:
    rng = random.Random(SEED)
    # The non-unity tap sets exercise both output rails and the +2**32
    # accumulator endpoint. The asymmetric set exposes tap-order errors.
    coefficient_sets = (
        (4096, 12288, 12288, 4096),
        (-32768, -32768, -32768, -32768),
        (16384, -20971, 9137, 32767),
    )
    rows = [str(len(coefficient_sets))]
    for taps in coefficient_sets:
        # +/-4 times the Lab 5.2 first tap (4096) is +/-0.5 output LSB.
        pairs = [(0, 0), (4, -4)] + [(0, 0)] * 4
        pairs += [(16384, -16384)] + [(0, 0)] * 4
        pairs += [(-32768, 32767)] * 6 + [(32767, -32768)] * 6
        pairs += [(1, -1), (0, 0), (-3, 3)] + [(0, 0)] * 4
        pairs += [(rng.randrange(-32768, 32768), rng.randrange(-32768, 32768))
                  for _ in range(128)]
        seq_i, seq_q = zip(*pairs)
        expected_i, expected_q = golden(seq_i, taps), golden(seq_q, taps)
        rows.append(" ".join(map(str, (*taps, len(pairs)))))
        for index, ((i_value, q_value), i_out, q_out) in enumerate(zip(pairs, expected_i, expected_q)):
            gap = 7 if index % 13 == 12 else 0
            rows.append(f"{gap} {i_value} {q_value} {i_out} {q_out}")
    path.write_text("\n".join(rows) + "\n", encoding="ascii", newline="\n")


def run(work: Path) -> None:
    iverilog, vvp = shutil.which("iverilog"), shutil.which("vvp")
    if not iverilog or not vvp:
        raise SystemExit("Install Icarus Verilog and put iverilog and vvp on PATH.")
    make_vectors(work / "fir_vectors.txt")
    for mode, name in enumerate(MODES):
        image = work / f"{name}.out"
        subprocess.run(
            [iverilog, "-g2012", "-s", "tb_fir_iq_architectures",
             f"-Ptb_fir_iq_architectures.ARCH={mode}", "-o", str(image),
             str(BLOCK / "rtl/fir_iq_architectures.sv"),
             str(BLOCK / "tb/tb_fir_iq_architectures.sv")],
            cwd=work, check=True, timeout=30,
        )
        result = subprocess.run([vvp, str(image)], cwd=work, text=True,
                                capture_output=True, timeout=30)
        log = result.stdout + result.stderr
        (work / f"{name}.txt").write_text(log, encoding="utf-8", newline="\n")
        print(f"{name}: {log}", end="")
        result.check_returncode()
        if not re.search(rf"^PASS ARCH={mode} compared=[1-9]\d* ", log, re.MULTILINE):
            raise SystemExit(f"{name}: missing simulation PASS")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts-dir", type=Path, help="Keep generated vectors and simulator logs")
    args = parser.parse_args()
    if args.artifacts_dir:
        work = args.artifacts_dir.resolve()
        work.mkdir(parents=True, exist_ok=True)
        run(work)
    else:
        with tempfile.TemporaryDirectory(prefix="fir-architectures-") as work:
            run(Path(work))


if __name__ == "__main__":
    main()
