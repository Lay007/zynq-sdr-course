#!/usr/bin/env python3
"""Generate reproducible Vivado OOC implementation evidence for Block 8 CSS."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from generate_block5_vivado_reports import detect_vivado, normalize_reports


ROOT = Path(__file__).resolve().parents[1]
TCL_SCRIPT = ROOT / "tools" / "vivado_block8_css_ooc.tcl"
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "fpga" / "block8_css_vivado_ooc_raw"
DEFAULT_PART = "xc7z020clg400-2"
DEFAULT_CLOCK_PERIOD_NS = 10.0
TOP_NAME = "css_sf7_sequential_detector"
DFT_TRANSFORM_CYCLES = 16_640
FINAL_INPUT_TO_DONE_CYCLES = 16_644
FIRST_INPUT_TO_DONE_CYCLES = 127 + FINAL_INPUT_TO_DONE_CYCLES
SYMBOL_INITIATION_INTERVAL_CYCLES = FIRST_INPUT_TO_DONE_CYCLES + 1


def _search(pattern: str, text: str) -> re.Match[str] | None:
    return re.search(pattern, text, re.MULTILINE | re.DOTALL)


def _parse_stage_metrics(
    output_dir: Path,
    stage: str,
    clock_period_ns: float,
    top_name: str = TOP_NAME,
    clock_port: str = "clk",
) -> tuple[dict[str, object], dict[str, object], str]:
    utilization = (
        output_dir / f"{top_name}_{stage}_utilization.rpt"
    ).read_text(encoding="utf-8", errors="ignore")
    timing = (
        output_dir / f"{top_name}_{stage}_timing_summary.rpt"
    ).read_text(encoding="utf-8", errors="ignore")

    lut = _search(r"\| Slice LUTs\*?\s*\|\s*([0-9<>.]+)\s*\|", utilization)
    ff = _search(r"\| Slice Registers\s*\|\s*([0-9<>.]+)\s*\|", utilization)
    bram = _search(r"\| Block RAM Tile\s*\|\s*([0-9<>.]+)\s*\|", utilization)
    dsp = _search(r"\| DSPs\s*\|\s*([0-9<>.]+)\s*\|", utilization)
    summary = _search(
        r"Design Timing Summary.*?\n\s*WNS\(ns\).*?\n\s*[- ]+\n\s*"
        r"([A-Z0-9.\-<>]+)\s+([A-Z0-9.\-<>]+)\s+"
        r"([A-Z0-9.\-<>]+)\s+([A-Z0-9.\-<>]+)",
        timing,
    )
    clock = _search(r"\n(\w+)\s+\{[^}]+\}\s+([0-9.]+)\s+([0-9.]+)", timing)
    data_path = _search(r"Data Path Delay:\s+([0-9.]+)ns", timing)
    logic_levels = _search(r"Logic Levels:\s+([0-9]+)", timing)

    wns_ns = (
        None if summary is None or summary.group(1) == "NA" else float(summary.group(1))
    )
    period_ns = float(clock.group(2)) if clock else clock_period_ns
    critical_period_ns = period_ns - wns_ns if wns_ns is not None else None
    fmax_est_mhz = (
        round(1000.0 / critical_period_ns, 3)
        if critical_period_ns is not None and critical_period_ns > 0
        else None
    )

    return (
        {
            "lut": int(lut.group(1)) if lut else None,
            "ff": int(ff.group(1)) if ff else None,
            "bram_tiles": float(bram.group(1)) if bram else None,
            "dsp": int(dsp.group(1)) if dsp else None,
        },
        {
            "wns_ns": wns_ns,
            "tns_ns": (
                None
                if summary is None or summary.group(2) == "NA"
                else float(summary.group(2))
            ),
            "failing_endpoints": (
                None
                if summary is None or summary.group(3) == "NA"
                else int(summary.group(3))
            ),
            "total_endpoints": (
                None
                if summary is None or summary.group(4) == "NA"
                else int(summary.group(4))
            ),
            "timing_met": wns_ns is not None and wns_ns >= 0.0,
            "clock_name": clock.group(1) if clock else None,
            "clock_period_ns": period_ns,
            "data_path_delay_ns": float(data_path.group(1)) if data_path else None,
            "logic_levels": int(logic_levels.group(1)) if logic_levels else None,
            "fmax_est_mhz": fmax_est_mhz,
        },
        utilization,
    )


def run_vivado(
    vivado_bin: Path,
    output_dir: Path,
    part_name: str,
    clock_period_ns: float,
    top_name: str = TOP_NAME,
) -> None:
    """Run the source-only batch flow without creating a persistent project."""
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "cmd.exe",
        "/c",
        str(vivado_bin),
        "-mode",
        "batch",
        "-nojournal",
        "-nolog",
        "-source",
        str(TCL_SCRIPT),
        "-tclargs",
        str(output_dir),
        part_name,
        f"{clock_period_ns:.3f}",
        top_name,
        clock_port,
    ]
    subprocess.run(command, cwd=ROOT, check=True)


def parse_metrics(
    output_dir: Path,
    part_name: str,
    clock_period_ns: float,
    top_name: str = TOP_NAME,
) -> dict[str, object]:
    """Extract stable post-synthesis and post-route implementation metrics."""
    post_synth_utilization, post_synth_timing, utilization_text = (
        _parse_stage_metrics(output_dir, "post_synthesis", clock_period_ns, top_name)
    )
    post_route_utilization, post_route_timing, _ = _parse_stage_metrics(
        output_dir, "post_route", clock_period_ns, top_name
    )
    route_status_text = (output_dir / f"{top_name}_post_route_status.rpt").read_text(
        encoding="utf-8", errors="ignore"
    )
    drc_text = (output_dir / f"{top_name}_post_route_drc.rpt").read_text(
        encoding="utf-8", errors="ignore"
    )

    tool = _search(r"\| Tool Version : ([^\r\n]+)", utilization_text)
    device = _search(r"\| Device\s*: ([^\r\n]+)", utilization_text)
    routable = _search(r"# of routable nets\.+\s*:\s*([0-9]+)", route_status_text)
    routing_errors = _search(
        r"# of nets with routing errors\.+\s*:\s*([0-9]+)", route_status_text
    )
    fully_routed = _search(
        r"# of fully routed nets\.+\s*:\s*([0-9]+)", route_status_text
    )
    design_state = _search(r"\| Design State\s*:\s*([^\r\n]+)", drc_text)
    drc_violations = _search(r"Violations found:\s*([0-9]+)", drc_text)
    drc_errors = sum(
        int(count)
        for count in re.findall(
            r"^\|\s*\S+\s*\|\s*Error\s*\|.*?\|\s*([0-9]+)\s*\|\s*$",
            drc_text,
            re.MULTILINE,
        )
    )
    unrouted_nets = (
        int(routable.group(1)) - int(fully_routed.group(1))
        if routable is not None and fully_routed is not None
        else None
    )

    target_clock_frequency_hz = 1_000_000_000.0 / clock_period_ns

    return {
        "tool_version": tool.group(1).strip() if tool else None,
        "device": device.group(1).strip() if device else None,
        "part": part_name,
        "top": top_name,
        "flow": "out_of_context_implementation",
        "target_clock_period_ns": clock_period_ns,
        "target_clock_frequency_mhz": round(1000.0 / clock_period_ns, 3),
        "latency_cycles": {
            "dft_transform": DFT_TRANSFORM_CYCLES,
            "final_input_to_done": FINAL_INPUT_TO_DONE_CYCLES,
            "first_input_to_done": FIRST_INPUT_TO_DONE_CYCLES,
            "symbol_initiation_interval": SYMBOL_INITIATION_INTERVAL_CYCLES,
        },
        "throughput_at_target_clock": {
            "symbol_decisions_per_second": round(
                target_clock_frequency_hz / SYMBOL_INITIATION_INTERVAL_CYCLES,
                3,
            ),
            "sustained_input_samples_per_second": round(
                128.0
                * target_clock_frequency_hz
                / SYMBOL_INITIATION_INTERVAL_CYCLES,
                3,
            ),
        },
        "post_synthesis": {
            "utilization": post_synth_utilization,
            "timing": post_synth_timing,
        },
        "post_route": {
            "utilization": post_route_utilization,
            "timing": post_route_timing,
            "route_status": {
                "design_state": design_state.group(1).strip() if design_state else None,
                "routable_nets": int(routable.group(1)) if routable else None,
                "fully_routed_nets": int(fully_routed.group(1)) if fully_routed else None,
                "unrouted_nets": unrouted_nets,
                "nets_with_routing_errors": (
                    int(routing_errors.group(1)) if routing_errors else None
                ),
                "fully_routed": (
                    design_state is not None
                    and design_state.group(1).strip() == "Fully Routed"
                    and unrouted_nets == 0
                    and routing_errors is not None
                    and int(routing_errors.group(1)) == 0
                ),
            },
            "drc": {
                "violations": int(drc_violations.group(1)) if drc_violations else None,
                "error_violations": drc_errors,
                "errors_present": drc_errors > 0,
            },
        },
    }


def validate_metrics(metrics: dict[str, object]) -> None:
    """Reject incomplete evidence packages while allowing an honest timing miss."""
    for stage_name in ("post_synthesis", "post_route"):
        stage = metrics[stage_name]
        assert isinstance(stage, dict)
        utilization = stage["utilization"]
        timing = stage["timing"]
        assert isinstance(utilization, dict)
        assert isinstance(timing, dict)

        missing_utilization = [
            name for name in ("lut", "ff", "bram_tiles", "dsp")
            if utilization.get(name) is None
        ]
        if missing_utilization:
            raise ValueError(
                f"Missing {stage_name} utilization metrics: "
                + ", ".join(missing_utilization)
            )
        if timing.get("wns_ns") is None:
            raise ValueError(f"Missing {stage_name} WNS")
        if timing.get("total_endpoints") is None:
            raise ValueError(f"Missing {stage_name} timing endpoint count")

    post_route = metrics["post_route"]
    assert isinstance(post_route, dict)
    route_status = post_route["route_status"]
    assert isinstance(route_status, dict)
    missing_route_status = [
        name
        for name in (
            "design_state",
            "routable_nets",
            "fully_routed_nets",
            "unrouted_nets",
            "nets_with_routing_errors",
        )
        if route_status.get(name) is None
    ]
    if missing_route_status:
        raise ValueError(
            "Missing route status metrics: " + ", ".join(missing_route_status)
        )
    if not route_status.get("fully_routed"):
        raise ValueError("Vivado implementation is not fully routed")
    drc = post_route["drc"]
    assert isinstance(drc, dict)
    if drc.get("violations") is None:
        raise ValueError("Missing post_route DRC violation count")
    if drc.get("errors_present"):
        raise ValueError("Vivado post-route DRC contains errors")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--part", default=DEFAULT_PART)
    parser.add_argument(
        "--reuse",
        action="store_true",
        help="Parse and normalize an existing report directory without rerunning Vivado.",
    )
    parser.add_argument(
        "--clock-period-ns",
        type=float,
        default=DEFAULT_CLOCK_PERIOD_NS,
    )
    args = parser.parse_args()

    vivado_bin = detect_vivado()
    output_dir = Path(args.output_dir).resolve()
    print(f"Vivado: {vivado_bin}")
    print(f"Output directory: {output_dir}")
    if not args.reuse:
        run_vivado(vivado_bin, output_dir, args.part, args.clock_period_ns, TOP_NAME)
    normalize_reports(output_dir)
    metrics = parse_metrics(output_dir, args.part, args.clock_period_ns, TOP_NAME)
    validate_metrics(metrics)

    metrics_path = output_dir / "block8_css_vivado_ooc_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print(f"Metrics JSON: {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
