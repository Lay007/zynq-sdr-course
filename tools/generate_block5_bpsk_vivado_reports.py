#!/usr/bin/env python3
"""Generate reproducible Vivado OOC implementation evidence for the Block 5 BPSK RTL (Labs 5.6-5.11)."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from generate_block5_vivado_reports import detect_vivado, normalize_reports
from generate_block8_ofdm_vivado_reports import parse_top, validate

ROOT = Path(__file__).resolve().parents[1]
TCL_SCRIPT = ROOT / "tools" / "vivado_block5_bpsk_ooc.tcl"
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "fpga" / "block5_bpsk_vivado_ooc_raw"
DEFAULT_PART = "xc7z020clg400-2"
DEFAULT_CLOCK_PERIOD_NS = 10.0

# (top module, clock port, lab)
TOPS: tuple[tuple[str, str, str], ...] = (
    ("bpsk_symbol_mapper", "clk", "5.7"),
    ("bpsk_upsampler_8x", "clk", "5.7"),
    ("bpsk_rrc_tx_fir", "clk", "5.6"),
    ("bpsk_rrc_rx_fir", "clk", "5.8"),
    ("bpsk_symbol_timing_sampler", "clk", "5.8"),
    ("bpsk_hard_decision", "clk", "5.8"),
    ("bpsk_rx_bit_recovery_chain", "clk", "5.8"),
    ("bpsk_symbol_timing_recovery", "clk", "5.8"),
    ("bpsk_frame_bit_source", "clk", "5.9"),
    ("bpsk_framed_tx_chain", "clk", "5.9"),
    ("bpsk_ber_counter", "clk", "5.9"),
    ("bpsk_zynq_ber_top", "clk", "5.10"),
    ("bpsk_zynq_ber_axi_lite", "s_axi_aclk", "5.11"),
)


def run_vivado(vivado_bin: Path, output_dir: Path, part: str, period_ns: float, top: str, clock: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "cmd.exe", "/c", str(vivado_bin), "-mode", "batch", "-nojournal", "-nolog",
        "-source", str(TCL_SCRIPT), "-tclargs",
        str(output_dir), part, f"{period_ns:.3f}", top, clock,
    ]
    # Vivado drops helper files into its working directory; keep them with the reports.
    subprocess.run(command, cwd=output_dir, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--part", default=DEFAULT_PART)
    parser.add_argument("--clock-period-ns", type=float, default=DEFAULT_CLOCK_PERIOD_NS)
    parser.add_argument("--reuse", action="store_true", help="parse an existing report directory without rerunning Vivado")
    parser.add_argument("--top", action="append", dest="tops", help="run only these tops (repeatable)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    selected = [t for t in TOPS if not args.tops or t[0] in args.tops]
    if not args.reuse:
        vivado_bin = detect_vivado()
        print(f"Vivado: {vivado_bin}")
        for top, clock, _lab in selected:
            run_vivado(vivado_bin, output_dir, args.part, args.clock_period_ns, top, clock)
    normalize_reports(output_dir)

    entries = []
    for top, clock, lab in selected:
        entry = parse_top(output_dir, args.clock_period_ns, top, clock)
        validate(entry)
        entry["lab"] = lab
        entries.append(entry)
    metrics = {
        "part": args.part,
        "flow": "out_of_context_implementation",
        "target_clock_period_ns": args.clock_period_ns,
        "target_clock_frequency_mhz": round(1000.0 / args.clock_period_ns, 3),
        "port_delays": "input and output delay 0 ns relative to the clock",
        "tops": entries,
    }
    metrics_path = output_dir / "block5_bpsk_vivado_ooc_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    for e in entries:
        u = e["post_route"]["utilization"]
        t = e["post_route"]["timing"]
        print(f"{e['top']:30s} LUT {u['lut']:5} FF {u['ff']:5} DSP {u['dsp']:3} BRAM {u['bram_tiles']:4} "
              f"WNS {t.get('wns_ns', '-')} Fmax~{t.get('fmax_est_mhz', '-')}")
    print(f"Metrics JSON: {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
