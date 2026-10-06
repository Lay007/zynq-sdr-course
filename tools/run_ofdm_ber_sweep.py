#!/usr/bin/env python3
"""Sweep Es/N0 through the OFDM RTL receiver and compare the BER with AWGN theory.

Each point compiles tb_ofdm_tx_rx_qam16_loopback.sv with MODULATION, ESN0_DB10
(Es/N0 per used subcarrier, tenths of a dB), CHANNEL, CFO_PPM and SYMBOLS, runs
it with Icarus Verilog and reads its RESULT line. The chain is the full one:
TX, channel, time-domain CFO correction, FFT, zero-forcing channel equalizer
trained on ONE noisy training symbol, pilot phase correction, slicer.

Theory columns (flat channel, Gray mapping, perfect channel knowledge):
    QPSK    Pb = 1/2 * erfc(sqrt(Es/N0 / 2))
    16-QAM  Pb ~ 3/8 * erfc(sqrt(Es/N0 / 10))   (nearest-neighbour approximation)
and the same curve 3 dB later: with Z = Y/G and G estimated from one symbol with
the same noise, the error variance at the slicer roughly doubles. Simulation
only; the noise is $dist_normal with fixed seeds, so the run is repeatable.

Every data symbol of a run shares ONE noisy channel estimate, so a single run
measures the BER of one training realization; --seeds N repeats each point with
N noise seeds (N training realizations) and sums the errors.
"""

from __future__ import annotations

import argparse
import math
import re
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
BLOCK = ROOT / "blocks/block_08_modulation_and_synchronization"
BENCH = "tb_ofdm_tx_rx_qam16_loopback"
RESULT_RE = re.compile(r"RESULT .*bit_errors=(\d+) bits=(\d+) evm_pct=([0-9.]+)")


def theory_ber(modulation: str, esn0_db: float) -> float:
    esn0 = 10.0 ** (esn0_db / 10.0)
    if modulation == "qpsk":
        return 0.5 * math.erfc(math.sqrt(esn0 / 2.0))
    return 3.0 / 8.0 * math.erfc(math.sqrt(esn0 / 10.0))


def run_point(work: Path, modulation: str, esn0_db: float, symbols: int, channel: int, cfo_ppm: int, seed: int,
              cfo_corr: bool = True):
    output = work / "point.vvp"
    params = {
        "MODULATION": 1 if modulation == "qam16" else 0,
        "ESN0_DB10": round(esn0_db * 10),
        "REQUIRE_ZERO_BER": 0,
        "SYMBOLS": symbols,
        "CHANNEL": channel,
        "CFO_PPM": cfo_ppm,
        "NOISE_SEED": seed,
        "USE_CFO_CORR": int(cfo_corr),
    }
    subprocess.run(
        ["iverilog", "-g2012", "-s", BENCH, *[f"-P{BENCH}.{k}={v}" for k, v in params.items()],
         "-o", str(output), *map(str, sorted((BLOCK / "rtl").glob("ofdm_*.v"))), str(BLOCK / "tb" / f"{BENCH}.sv")],
        cwd=ROOT, check=True, timeout=300,
    )
    run = subprocess.run(["vvp", "-n", str(output)], cwd=ROOT, capture_output=True, text=True, timeout=3600)
    match = RESULT_RE.search(run.stdout)
    if not match:
        raise SystemExit(f"no RESULT line at Es/N0 {esn0_db} dB:\n{run.stdout[-2000:]}")
    return int(match.group(1)), int(match.group(2)), float(match.group(3))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--modulation", choices=("qpsk", "qam16"), default="qam16")
    parser.add_argument("--esn0", type=float, nargs="+", default=[12.0, 14.0, 16.0, 18.0, 20.0, 22.0])
    parser.add_argument("--symbols", type=int, default=100)
    parser.add_argument("--channel", type=int, default=0, help="0 flat, 1 Lab 8.5 multipath, 2 strong multipath")
    parser.add_argument("--cfo-ppm", type=int, default=0)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--seeds", type=int, default=1, help="noise seeds (training realizations) per point")
    parser.add_argument("--no-cfo-corr", action="store_true", help="bypass the time-domain CFO corrector")
    args = parser.parse_args()
    for command in ("iverilog", "vvp"):
        if shutil.which(command) is None:
            raise SystemExit(f"{command} is required; install Icarus Verilog")

    print(f"{args.modulation.upper()} OFDM RTL, channel {args.channel}, CFO {args.cfo_ppm} ppm, "
          f"{args.symbols} data symbols x {args.seeds} noise seeds per point (from {args.seed}), "
          f"CFO corrector {'off' if args.no_cfo_corr else 'on'}")
    print(" Es/N0 dB    bit errors / bits       BER   EVM %   theory BER   theory BER, -3 dB")
    with TemporaryDirectory(prefix="course-ofdm-ber-") as temporary:
        for esn0 in args.esn0:
            errors = bits = 0
            evm_sq = 0.0
            for seed in range(args.seed, args.seed + args.seeds):
                e, b, v = run_point(Path(temporary), args.modulation, esn0, args.symbols,
                                    args.channel, args.cfo_ppm, seed, not args.no_cfo_corr)
                errors, bits, evm_sq = errors + e, bits + b, evm_sq + v * v
            evm = math.sqrt(evm_sq / args.seeds)
            print(f"{esn0:8.1f} {errors:10d} / {bits:<8d} {errors / bits:10.2e} {evm:7.2f} "
                  f"{theory_ber(args.modulation, esn0):12.2e} {theory_ber(args.modulation, esn0 - 3.0):19.2e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
