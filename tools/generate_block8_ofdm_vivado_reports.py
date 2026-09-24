#!/usr/bin/env python3
"""Generate reproducible Vivado OOC implementation evidence for the Block 8 OFDM RTL."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from generate_block5_vivado_reports import detect_vivado, normalize_reports
from generate_block8_css_vivado_reports import _parse_stage_metrics, _search

ROOT = Path(__file__).resolve().parents[1]
TCL_SCRIPT = ROOT / "tools" / "vivado_block8_ofdm_ooc.tcl"
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "fpga" / "block8_ofdm_vivado_ooc_raw"
DEFAULT_PART = "xc7z020clg400-2"
DEFAULT_CLOCK_PERIOD_NS = 10.0

# (top module, clock port or None for purely combinational blocks)
TOPS: tuple[tuple[str, str | None], ...] = (
    ("ofdm_tx_cp16_path", "clk"),
    ("ofdm_cp16_remover", "clk"),
    ("ofdm_fft64_sequential", "clk"),
    ("ofdm_subcarrier_extractor", None),
    ("ofdm_one_tap_equalizer", "clk"),
    ("ofdm_pilot_phase_tracker", "clk"),
    ("ofdm_qpsk_demapper", None),
)


def run_vivado(vivado_bin: Path, output_dir: Path, part: str, period_ns: float, top: str, clock: str | None) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "cmd.exe", "/c", str(vivado_bin), "-mode", "batch", "-nojournal", "-nolog",
        "-source", str(TCL_SCRIPT), "-tclargs",
        str(output_dir), part, f"{period_ns:.3f}", top, clock or "none",
    ]
    # Vivado drops helper files (e.g. tight_setup_hold_pins.txt) into its working
    # directory; keep them with the reports instead of the repository root.
    subprocess.run(command, cwd=output_dir, check=True)


def parse_top(output_dir: Path, period_ns: float, top: str, clock: str | None) -> dict[str, object]:
    post_synth_util, post_synth_timing, util_text = _parse_stage_metrics(output_dir, "post_synthesis", period_ns, top)
    post_route_util, post_route_timing, _ = _parse_stage_metrics(output_dir, "post_route", period_ns, top)
    route_text = (output_dir / f"{top}_post_route_status.rpt").read_text(encoding="utf-8", errors="ignore")
    drc_text = (output_dir / f"{top}_post_route_drc.rpt").read_text(encoding="utf-8", errors="ignore")
    routable = _search(r"# of routable nets\.+\s*:\s*([0-9]+)", route_text)
    fully_routed = _search(r"# of fully routed nets\.+\s*:\s*([0-9]+)", route_text)
    routing_errors = _search(r"# of nets with routing errors\.+\s*:\s*([0-9]+)", route_text)
    drc_violations = _search(r"Violations found:\s*([0-9]+)", drc_text)
    drc_errors = len(re.findall(r"^\|\s*\S+\s*\|\s*Error\s*\|", drc_text, re.MULTILINE))
    tool = _search(r"\| Tool Version : ([^\r\n]+)", util_text)
    if clock is None:
        # No clock constraint: Vivado reports no WNS; keep only the resource numbers.
        post_synth_timing = post_route_timing = {"clocked": False}
    return {
        "top": top,
        "clock_port": clock,
        "tool_version": tool.group(1).strip() if tool else None,
        "post_synthesis": {"utilization": post_synth_util, "timing": post_synth_timing},
        "post_route": {
            "utilization": post_route_util,
            "timing": post_route_timing,
            "routable_nets": int(routable.group(1)) if routable else None,
            "fully_routed_nets": int(fully_routed.group(1)) if fully_routed else None,
            "nets_with_routing_errors": int(routing_errors.group(1)) if routing_errors else None,
            "drc_violations": int(drc_violations.group(1)) if drc_violations else None,
            "drc_errors": drc_errors,
        },
    }


def validate(entry: dict[str, object]) -> None:
    route = entry["post_route"]
    assert isinstance(route, dict)
    utilization = route["utilization"]
    assert isinstance(utilization, dict)
    missing = [k for k in ("lut", "ff", "bram_tiles", "dsp") if utilization.get(k) is None]
    if missing:
        raise ValueError(f"{entry['top']}: missing utilization {missing}")
    if route.get("nets_with_routing_errors") not in (0,):
        raise ValueError(f"{entry['top']}: routing errors or no route status")
    # A block with nothing to route (pure wiring) has no "fully routed" line at all.
    if (route.get("routable_nets") or 0) != (route.get("fully_routed_nets") or 0):
        raise ValueError(f"{entry['top']}: not fully routed")
    if route.get("drc_violations") is None or route.get("drc_errors"):
        raise ValueError(f"{entry['top']}: missing DRC report or DRC errors present")
    timing = route["timing"]
    assert isinstance(timing, dict)
    if entry["clock_port"] is not None and timing.get("wns_ns") is None:
        raise ValueError(f"{entry['top']}: missing post-route WNS")


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
        for top, clock in selected:
            run_vivado(vivado_bin, output_dir, args.part, args.clock_period_ns, top, clock)
    normalize_reports(output_dir)

    entries = []
    for top, clock in selected:
        entry = parse_top(output_dir, args.clock_period_ns, top, clock)
        validate(entry)
        entries.append(entry)
    metrics = {
        "part": args.part,
        "flow": "out_of_context_implementation",
        "target_clock_period_ns": args.clock_period_ns,
        "target_clock_frequency_mhz": round(1000.0 / args.clock_period_ns, 3),
        "tops": entries,
    }
    metrics_path = output_dir / "block8_ofdm_vivado_ooc_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    for e in entries:
        u = e["post_route"]["utilization"]
        t = e["post_route"]["timing"]
        print(f"{e['top']:28s} LUT {u['lut']:5} FF {u['ff']:5} DSP {u['dsp']:3} BRAM {u['bram_tiles']:4} "
              f"WNS {t.get('wns_ns', '-')} Fmax~{t.get('fmax_est_mhz', '-')}")
    print(f"Metrics JSON: {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
