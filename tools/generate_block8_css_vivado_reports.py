#!/usr/bin/env python3
"""Generate reproducible Vivado OOC evidence for the Block 8 CSS detector."""

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


def _search(pattern: str, text: str) -> re.Match[str] | None:
    return re.search(pattern, text, re.MULTILINE | re.DOTALL)


def run_vivado(
    vivado_bin: Path,
    output_dir: Path,
    part_name: str,
    clock_period_ns: float,
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
    ]
    subprocess.run(command, cwd=ROOT, check=True)


def parse_metrics(
    output_dir: Path,
    part_name: str,
    clock_period_ns: float,
) -> dict[str, object]:
    """Extract stable resource and post-synthesis timing metrics."""
    utilization = (output_dir / f"{TOP_NAME}_utilization.rpt").read_text(
        encoding="utf-8", errors="ignore"
    )
    timing = (output_dir / f"{TOP_NAME}_timing_summary.rpt").read_text(
        encoding="utf-8", errors="ignore"
    )

    tool = _search(r"\| Tool Version : ([^\r\n]+)", utilization)
    device = _search(r"\| Device\s*: ([^\r\n]+)", utilization)
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

    wns_ns = None if summary is None or summary.group(1) == "NA" else float(summary.group(1))
    period_ns = float(clock.group(2)) if clock else clock_period_ns
    critical_period_ns = period_ns - wns_ns if wns_ns is not None else None
    fmax_est_mhz = (
        round(1000.0 / critical_period_ns, 3)
        if critical_period_ns is not None and critical_period_ns > 0
        else None
    )

    return {
        "tool_version": tool.group(1).strip() if tool else None,
        "device": device.group(1).strip() if device else None,
        "part": part_name,
        "top": TOP_NAME,
        "flow": "out_of_context_post_synthesis",
        "target_clock_period_ns": clock_period_ns,
        "target_clock_frequency_mhz": round(1000.0 / clock_period_ns, 3),
        "utilization": {
            "lut": int(lut.group(1)) if lut else None,
            "ff": int(ff.group(1)) if ff else None,
            "bram_tiles": float(bram.group(1)) if bram else None,
            "dsp": int(dsp.group(1)) if dsp else None,
        },
        "timing": {
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
            "post_synthesis_fmax_est_mhz": fmax_est_mhz,
        },
    }


def validate_metrics(metrics: dict[str, object]) -> None:
    """Reject incomplete evidence packages while allowing an honest timing miss."""
    utilization = metrics["utilization"]
    timing = metrics["timing"]
    assert isinstance(utilization, dict)
    assert isinstance(timing, dict)

    missing_utilization = [
        name for name in ("lut", "ff", "bram_tiles", "dsp")
        if utilization.get(name) is None
    ]
    if missing_utilization:
        raise ValueError(
            "Missing utilization metrics: " + ", ".join(missing_utilization)
        )
    if timing.get("wns_ns") is None:
        raise ValueError("Missing post-synthesis WNS")
    if timing.get("total_endpoints") is None:
        raise ValueError("Missing timing endpoint count")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--part", default=DEFAULT_PART)
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
    run_vivado(vivado_bin, output_dir, args.part, args.clock_period_ns)
    normalize_reports(output_dir)
    metrics = parse_metrics(output_dir, args.part, args.clock_period_ns)
    validate_metrics(metrics)

    metrics_path = output_dir / "block8_css_vivado_ooc_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print(f"Metrics JSON: {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
