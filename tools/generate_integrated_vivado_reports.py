#!/usr/bin/env python3
"""Build or promote routed Vivado evidence for the integrated Zynq design."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from generate_block5_vivado_reports import detect_vivado, normalize_report_text


ROOT = Path(__file__).resolve().parents[1]
DESIGN_DIR = ROOT / "hardware" / "7020_ad936x_sdr" / "hdl" / "course_bpsk_fmcomms2_zc702"
PROJECT_SCRIPT = DESIGN_DIR / "system_project.tcl"
BUILD_SCRIPT = DESIGN_DIR / "build_bitstream.tcl"
IMPL_DIR = DESIGN_DIR / "build" / "course_bpsk_fmcomms2_zc702.runs" / "impl_1"
OUTPUT_DIR = ROOT / "reports" / "fpga" / "integrated_zynq_raw"
SUMMARY_PATH = ROOT / "reports" / "fpga" / "integrated-zynq-implementation-summary.md"
SNAPSHOT_SCRIPT = ROOT / "hardware" / "7020_ad936x_sdr" / "rebuild_vendor_xpr_snapshot_course_overlay.tcl"
SNAPSHOT_IMPL_DIR = (
    ROOT / "tmp" / "vendor_xpr_course_overlay" / "zc702" / "zc702.runs" / "impl_1"
)
SNAPSHOT_OUTPUT_DIR = ROOT / "reports" / "fpga" / "integrated_zynq_snapshot_raw"
SNAPSHOT_SUMMARY_PATH = (
    ROOT / "reports" / "fpga" / "integrated-zynq-snapshot-implementation-summary.md"
)

REPORT_FILES = (
    "system_top_utilization_placed.rpt",
    "system_top_timing_summary_routed.rpt",
    "system_top_clock_utilization_routed.rpt",
    "system_top_route_status.rpt",
)


def run_vivado_script(
    vivado_bin: Path, script: Path, *, extra_environment: dict[str, str] | None = None
) -> None:
    command = ["cmd.exe", "/c", str(vivado_bin), "-mode", "batch", "-source", str(script)]
    environment = os.environ.copy()
    environment.update(extra_environment or {})
    subprocess.run(command, cwd=ROOT, check=True, env=environment)


def search(pattern: str, text: str) -> re.Match[str] | None:
    return re.search(pattern, text, re.MULTILINE | re.DOTALL)


def parse_integrated_metrics(util_text: str, timing_text: str, route_text: str) -> dict[str, Any]:
    tool = search(r"\| Tool Version : ([^\r\n]+)", util_text)
    device = search(r"\| Device\s+: ([^\r\n]+)", util_text)
    util_patterns = {
        "lut": r"\| Slice LUTs\*?\s*\|\s*([0-9<>.]+)\s*\|",
        "ff": r"\| Slice Registers\s*\|\s*([0-9<>.]+)\s*\|",
        "bram_tiles": r"\| Block RAM Tile\s*\|\s*([0-9<>.]+)\s*\|",
        "dsp": r"\| DSPs\s*\|\s*([0-9<>.]+)\s*\|",
    }
    utilization: dict[str, int | float | None] = {}
    for name, pattern in util_patterns.items():
        match = search(pattern, util_text)
        if match is None:
            utilization[name] = None
        elif name == "bram_tiles":
            utilization[name] = float(match.group(1))
        else:
            utilization[name] = int(match.group(1))

    summary = search(
        r"Design Timing Summary.*?\n\s*WNS\(ns\).*?\n\s*[- ]+\n\s*"
        r"([A-Z0-9.\-<>]+)\s+([A-Z0-9.\-<>]+)\s+([A-Z0-9.\-<>]+)\s+([A-Z0-9.\-<>]+)",
        timing_text,
    )
    route_match = search(r"# of Unrouted Nets\s*:\s*([0-9]+)", route_text)
    routable_match = search(r"# of routable nets\.*\s*:\s*([0-9]+)\s*:", route_text)
    fully_routed_match = search(r"# of fully routed nets\.*\s*:\s*([0-9]+)\s*:", route_text)
    routing_errors_match = search(r"# of nets with routing errors\.*\s*:\s*([0-9]+)\s*:", route_text)

    wns = None if summary is None or summary.group(1) == "NA" else float(summary.group(1))
    tns = None if summary is None or summary.group(2) == "NA" else float(summary.group(2))
    failing = None if summary is None or summary.group(3) == "NA" else int(summary.group(3))
    total = None if summary is None or summary.group(4) == "NA" else int(summary.group(4))
    routable = int(routable_match.group(1)) if routable_match else None
    fully_routed_nets = int(fully_routed_match.group(1)) if fully_routed_match else None
    routing_errors = int(routing_errors_match.group(1)) if routing_errors_match else None
    if route_match:
        unrouted = int(route_match.group(1))
    elif routable is not None and fully_routed_nets is not None:
        unrouted = routable - fully_routed_nets
    else:
        unrouted = None
    return {
        "tool_version": tool.group(1).strip() if tool else None,
        "device": device.group(1).strip() if device else None,
        "utilization": utilization,
        "timing": {
            "wns_ns": wns,
            "tns_ns": tns,
            "failing_endpoints": failing,
            "total_endpoints": total,
            "timing_met": wns is not None and wns >= 0.0 and (tns or 0.0) >= 0.0,
        },
        "route": {
            "routable_nets": routable,
            "fully_routed_nets": fully_routed_nets,
            "routing_errors": routing_errors,
            "unrouted_nets": unrouted,
            "fully_routed": (
                unrouted == 0 and routing_errors in (None, 0) if unrouted is not None else None
            ),
        },
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_integrated_metrics(metrics: dict[str, Any], *, require_timing: bool = True) -> None:
    """Reject incomplete or failing implementation evidence."""
    missing_resources = [
        name for name, value in metrics["utilization"].items() if value is None
    ]
    if missing_resources:
        raise ValueError(f"Could not parse utilization field(s): {', '.join(missing_resources)}")
    if metrics["timing"]["wns_ns"] is None or metrics["timing"]["tns_ns"] is None:
        raise ValueError("Could not parse routed timing summary")
    if require_timing and not metrics["timing"]["timing_met"]:
        raise ValueError("Routed design does not meet timing")
    if metrics["route"]["routing_errors"] is None:
        raise ValueError("Could not parse route status")
    if not metrics["route"]["fully_routed"]:
        raise ValueError("Design is not fully routed")


def promote_reports(
    *,
    impl_dir: Path = IMPL_DIR,
    output_dir: Path = OUTPUT_DIR,
    summary_path: Path = SUMMARY_PATH,
    flow_name: str = "standalone recreated project",
    require_timing: bool = True,
) -> dict[str, Any]:
    missing = [name for name in REPORT_FILES if not (impl_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing routed report(s): {', '.join(missing)}. Run with --build first.")

    output_dir.mkdir(parents=True, exist_ok=True)
    for name in REPORT_FILES:
        source = impl_dir / name
        target = output_dir / name
        text = source.read_text(encoding="utf-8", errors="ignore")
        target.write_text(normalize_report_text(text, impl_dir), encoding="utf-8")

    util_text = (output_dir / REPORT_FILES[0]).read_text(encoding="utf-8", errors="ignore")
    timing_text = (output_dir / REPORT_FILES[1]).read_text(encoding="utf-8", errors="ignore")
    route_text = (output_dir / REPORT_FILES[3]).read_text(encoding="utf-8", errors="ignore")
    metrics = parse_integrated_metrics(util_text, timing_text, route_text)
    metrics["flow"] = flow_name
    validate_integrated_metrics(metrics, require_timing=require_timing)

    bitstream = impl_dir / "system_top.bit"
    metrics["bitstream"] = {
        "file_name": bitstream.name,
        "size_bytes": bitstream.stat().st_size if bitstream.is_file() else None,
        "sha256": sha256_file(bitstream) if bitstream.is_file() else None,
        "committed": False,
    }
    metrics_path = output_dir / "integrated_zynq_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    write_summary(metrics, summary_path=summary_path, output_dir=output_dir)
    return metrics


def display(value: Any, suffix: str = "") -> str:
    return "N/A" if value is None else f"{value}{suffix}"


def write_summary(
    metrics: dict[str, Any], *, summary_path: Path = SUMMARY_PATH, output_dir: Path = OUTPUT_DIR
) -> None:
    utilization = metrics["utilization"]
    timing = metrics["timing"]
    route = metrics["route"]
    bitstream = metrics["bitstream"]
    lines = [
        "# Integrated Zynq implementation summary",
        "",
        f"This report is generated from the `{metrics['flow']}` flow after full Vivado synthesis, placement, routing and bitstream generation.",
        "",
        "## Build context",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Tool | {display(metrics['tool_version'])} |",
        f"| Device | {display(metrics['device'])} |",
        f"| Fully routed | {display(route['fully_routed'])} |",
        f"| Unrouted nets | {display(route['unrouted_nets'])} |",
        f"| Routing errors | {display(route['routing_errors'])} |",
        f"| Bitstream size | {display(bitstream['size_bytes'], ' bytes')} |",
        f"| Bitstream SHA256 | `{display(bitstream['sha256'])}` |",
        "",
        "## Utilization",
        "",
        "| LUT | FF | DSP | BRAM tiles |",
        "|---:|---:|---:|---:|",
        f"| {display(utilization['lut'])} | {display(utilization['ff'])} | {display(utilization['dsp'])} | {display(utilization['bram_tiles'])} |",
        "",
        "## Timing",
        "",
        "| WNS, ns | TNS, ns | Failing endpoints | Total endpoints | Timing met |",
        "|---:|---:|---:|---:|---|",
        f"| {display(timing['wns_ns'])} | {display(timing['tns_ns'])} | {display(timing['failing_endpoints'])} | {display(timing['total_endpoints'])} | {display(timing['timing_met'])} |",
        "",
        "## Interpretation",
        "",
        "This routed report applies only to the named build flow. Hardware compatibility, runtime clock activity and RF performance require separate board evidence.",
        "",
        f"Raw normalized reports are stored in `{output_dir.relative_to(ROOT).as_posix()}/`.",
        "",
    ]
    summary_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--build",
        action="store_true",
        help="Recreate the Vivado project and run full implementation before promoting reports.",
    )
    parser.add_argument(
        "--flow",
        choices=["standalone", "snapshot"],
        default="standalone",
        help="Select the recreated standalone project or hardware-correlated vendor snapshot flow.",
    )
    args = parser.parse_args()
    if args.build:
        vivado = detect_vivado()
        if args.flow == "snapshot":
            run_vivado_script(
                vivado,
                SNAPSHOT_SCRIPT,
                extra_environment={"COURSE_OVERLAY_MODE": "bridge_txrx_mux"},
            )
        else:
            run_vivado_script(vivado, PROJECT_SCRIPT)
            run_vivado_script(vivado, BUILD_SCRIPT)
    if args.flow == "snapshot":
        metrics = promote_reports(
            impl_dir=SNAPSHOT_IMPL_DIR,
            output_dir=SNAPSHOT_OUTPUT_DIR,
            summary_path=SNAPSHOT_SUMMARY_PATH,
            flow_name="vendor snapshot bridge_txrx_mux",
            require_timing=False,
        )
    else:
        metrics = promote_reports()
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
