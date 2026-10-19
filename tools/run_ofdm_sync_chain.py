#!/usr/bin/env python3
"""Issue #48 stage 4b: a received stream through the RTL frame synchronizer and the RTL receiver.

Builds frames with tools/ofdm_rf_link.py (sync preamble + the RTL transmitter's training and data
symbols), sends each through the channel model, and runs the continuous stream through
tb_ofdm_rx_sync_chain.sv (ofdm_frame_sync -> ofdm_axi_modem). Checks per frame:

* the synchronizer is bit-exact with tools/ofdm_frame_sync_fixed.py: the samples it hands to the
  modem are exactly the received samples from the model's first-symbol index on;
* the bit errors of the decided data.

    python tools/run_ofdm_sync_chain.py --frames 5 --snr-db 20 --cfo-hz 3000

Simulation only. Requires iverilog and vvp.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BLOCK = ROOT / "blocks" / "block_08_modulation_and_synchronization"
sys.path.insert(0, str(ROOT / "tools"))
import ofdm_frame_sync_fixed as F  # noqa: E402
import ofdm_rf_link as O  # noqa: E402

BENCH = "tb_ofdm_rx_sync_chain"


def build(work: Path, frame_symbols: int, train_symbols: int, sample_gap: int) -> Path:
    out = work / "chain.vvp"
    if not out.exists():
        subprocess.run(["iverilog", "-g2012", "-s", BENCH, f"-P{BENCH}.FRAME_SYMBOLS={frame_symbols}",
                        f"-P{BENCH}.CE_TRAIN_SYMBOLS={train_symbols}", f"-P{BENCH}.SAMPLE_GAP={sample_gap}",
                        "-o", str(out),
                        *map(str, sorted((BLOCK / "rtl").glob("ofdm_*.v"))), str(BLOCK / "tb" / f"{BENCH}.sv")],
                       check=True, capture_output=True, text=True)
    return out


def run_one(work: Path, rng: np.random.Generator, args) -> dict:
    burst, data, true_start = O.make_frame(work, rng, args)
    frac = rng.uniform(0, 1) if args.fractional else 0.0
    dc = args.dc * np.exp(1j * rng.uniform(0, 2 * np.pi))
    rx = O.channel(burst, rng, args.snr_db, args.cfo_hz, args.fs, frac, dc, args.iq_gain_db, args.iq_phase_deg,
                   args.rx_rms)
    iq = work / "chain_iq.txt"
    np.savetxt(iq, np.column_stack([rx.real, rx.imag]).astype(np.int64), fmt="%d")
    n_sym = args.train_symbols + args.data_symbols
    vvp = build(work, n_sym, args.train_symbols, args.sample_gap)
    p = subprocess.run(["vvp", "-n", str(vvp), f"+IQ={iq}", f"+SYNC_OUT={work / 'sync.txt'}",
                        f"+BITS_OUT={work / 'bits.txt'}"], capture_output=True, text=True, timeout=900)
    result = [x for x in p.stdout.splitlines() if x.startswith("RESULT")]
    if p.returncode != 0 or not result:
        raise RuntimeError(p.stdout[-500:] + p.stderr[-300:])
    model = F.detect(rx)
    row = {"true_first": true_start + O.N, "model_first": model[0] if model else None, "rtl": result[0]}
    sync = np.loadtxt(work / "sync.txt", dtype=np.int64, ndmin=2)
    # Same number of frames as the model (none included), and the same samples handed over.
    found = int(result[0].split("frames_found=")[1].split()[0])
    row["rtl_matches_model"] = found == len(model)
    if model and sync.size:
        ref = rx[model[0]: model[0] + len(sync)]
        row["rtl_matches_model"] &= bool(len(ref) == len(sync) and np.array_equal(sync[:, 0], ref.real.astype(np.int64))
                                         and np.array_equal(sync[:, 1], ref.imag.astype(np.int64)))
    txt = (work / "bits.txt").read_text().split()
    pairs = np.array(txt, dtype=np.int64).reshape(-1, 2) if txt else np.zeros((0, 2), dtype=np.int64)
    got = np.full(48 * args.data_symbols, -1)
    for k, (idx, bits) in enumerate(pairs[: 48 * args.data_symbols]):
        got[(k // 48) * 48 + idx] = bits
    row["bits"] = 2 * len(data)
    row["bit_errors"] = int(sum(bin(int(a) ^ int(b)).count("1") if b >= 0 else 2 for a, b in zip(data, got)))
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--frames", type=int, default=3)
    ap.add_argument("--data-symbols", type=int, default=10)
    ap.add_argument("--train-symbols", type=int, default=1)
    ap.add_argument("--fs", type=float, default=2.083e6)
    ap.add_argument("--snr-db", type=float, default=30.0)
    ap.add_argument("--cfo-hz", type=float, default=0.0)
    ap.add_argument("--fractional", action="store_true")
    ap.add_argument("--dc", type=float, default=0.0)
    ap.add_argument("--iq-gain-db", type=float, default=0.0)
    ap.add_argument("--iq-phase-deg", type=float, default=0.0)
    ap.add_argument("--rx-rms", type=float, default=3700.0)
    ap.add_argument("--sample-gap", type=int, default=48,
                    help="clocks per sample: 48 = 2.083 MS/s at the 100 MHz modem clock, as on the board")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for _ in range(args.frames):
            row = run_one(work, rng, args)
            rows.append(row)
            print(json.dumps(row), flush=True)
    summary = {"frames": len(rows), "bits": sum(r["bits"] for r in rows), "bit_errors": sum(r["bit_errors"] for r in rows),
               "rtl_matches_model": all(r.get("rtl_matches_model", False) for r in rows)}
    print(json.dumps(summary))
    if args.json_out:
        args.json_out.write_text(json.dumps({"summary": summary, "frames": rows, "args": {k: str(v) for k, v in vars(args).items()}},
                                            indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
