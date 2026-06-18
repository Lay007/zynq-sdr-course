#!/usr/bin/env python3
"""Run reproducible Vivado OOC reports for Block 5 RTL modules."""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TCL_SCRIPT = ROOT / "tools" / "vivado_block5_ooc.tcl"
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "fpga" / "vivado_ooc_raw"
DEFAULT_PART = "xc7z020clg400-2"
DEFAULT_CLOCK_PERIOD_NS = 10.0
MODULE_NAMES = (
    "iq_passthrough",
    "fir_iq_4tap",
    "nco_mixer_iq",
    "axis_iq_passthrough",
)


def iter_vivado_candidates() -> list[Path]:
    candidates: list[Path] = []

    env_candidate = os.environ.get("VIVADO_BIN")
    if env_candidate:
        candidates.append(Path(env_candidate))

    for executable_name in ("vivado.bat", "vivado"):
        resolved = shutil.which(executable_name)
        if resolved:
            candidates.append(Path(resolved))

    for pattern in (
        f"{ROOT.drive}\\Xilinx\\Vivado\\*\\bin\\vivado.bat",
        "G:\\Xilinx\\Vivado\\*\\bin\\vivado.bat",
        "C:\\Xilinx\\Vivado\\*\\bin\\vivado.bat",
    ):
        for path in sorted(glob.glob(pattern)):
            candidates.append(Path(path))

    unique_candidates: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in seen and resolved.exists():
            unique_candidates.append(resolved)
            seen.add(resolved)

    return unique_candidates


def detect_vivado() -> Path:
    candidates = iter_vivado_candidates()
    if not candidates:
        raise FileNotFoundError(
            "Vivado executable not found. Set VIVADO_BIN or install Vivado under a standard Xilinx path."
        )
    return candidates[0]


def run_vivado(vivado_bin: Path, output_dir: Path, part_name: str, clock_period_ns: float) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "cmd.exe",
        "/c",
        str(vivado_bin),
        "-mode",
        "batch",
        "-source",
        str(TCL_SCRIPT),
        "-tclargs",
        str(output_dir),
        part_name,
        f"{clock_period_ns:.3f}",
    ]
    subprocess.run(command, cwd=ROOT, check=True)


def _search(pattern: str, text: str) -> re.Match[str] | None:
    return re.search(pattern, text, re.MULTILINE | re.DOTALL)


def parse_metrics(output_dir: Path, part_name: str, clock_period_ns: float) -> dict[str, object]:
    modules: dict[str, object] = {}
    tool_version: str | None = None

    for module_name in MODULE_NAMES:
        util_text = (output_dir / f"{module_name}_utilization.rpt").read_text(encoding="utf-8", errors="ignore")
        timing_text = (output_dir / f"{module_name}_timing_summary.rpt").read_text(
            encoding="utf-8", errors="ignore"
        )

        tool_match = _search(r"\| Tool Version : ([^\r\n]+)", util_text)
        if tool_match and tool_version is None:
            tool_version = tool_match.group(1).strip()

        util_lut = _search(r"\| Slice LUTs\*?\s*\|\s*([0-9<>.]+)\s*\|", util_text)
        util_ff = _search(r"\| Slice Registers\s*\|\s*([0-9<>.]+)\s*\|", util_text)
        util_bram = _search(r"\| Block RAM Tile\s*\|\s*([0-9<>.]+)\s*\|", util_text)
        util_dsp = _search(r"\| DSPs\s*\|\s*([0-9<>.]+)\s*\|", util_text)

        summary = _search(
            r"Design Timing Summary.*?\n\s*WNS\(ns\).*?\n\s*[- ]+\n\s*"
            r"([A-Z0-9.\-<>]+)\s+([A-Z0-9.\-<>]+)\s+([A-Z0-9.\-<>]+)\s+([A-Z0-9.\-<>]+)",
            timing_text,
        )
        clock = _search(r"\n(\w+)\s+\{[^}]+\}\s+([0-9.]+)\s+([0-9.]+)", timing_text)
        data_path = _search(r"Data Path Delay:\s+([0-9.]+)ns", timing_text)
        logic_levels = _search(r"Logic Levels:\s+([0-9]+)", timing_text)

        wns_value = summary.group(1) if summary else None
        period_ns = float(clock.group(2)) if clock else None
        data_path_delay_ns = float(data_path.group(1)) if data_path else None

        fmax_est_mhz: float | None = None
        if data_path_delay_ns:
            fmax_est_mhz = 1000.0 / data_path_delay_ns
        elif wns_value not in (None, "NA") and period_ns is not None:
            fmax_est_mhz = 1000.0 / (period_ns - float(wns_value))

        modules[module_name] = {
            "lut": int(util_lut.group(1)) if util_lut else None,
            "ff": int(util_ff.group(1)) if util_ff else None,
            "dsp": int(util_dsp.group(1)) if util_dsp else None,
            "bram_tiles": float(util_bram.group(1)) if util_bram else None,
            "wns_ns": None if wns_value in (None, "NA") else float(wns_value),
            "tns_ns": None if summary is None or summary.group(2) == "NA" else float(summary.group(2)),
            "failing_endpoints": None if summary is None or summary.group(3) == "NA" else int(summary.group(3)),
            "total_endpoints": None if summary is None or summary.group(4) == "NA" else int(summary.group(4)),
            "clock_name": clock.group(1) if clock else None,
            "clock_period_ns": period_ns,
            "clock_frequency_mhz": float(clock.group(3)) if clock else None,
            "data_path_delay_ns": data_path_delay_ns,
            "logic_levels": int(logic_levels.group(1)) if logic_levels else None,
            "fmax_est_mhz": round(fmax_est_mhz, 3) if fmax_est_mhz is not None else None,
        }

    return {
        "tool_version": tool_version,
        "part": part_name,
        "target_clock_period_ns": clock_period_ns,
        "target_clock_frequency_mhz": round(1000.0 / clock_period_ns, 3),
        "modules": modules,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Vivado OOC reports for Block 5 RTL modules.")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Directory for raw Vivado report artifacts. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--part",
        default=DEFAULT_PART,
        help=f"FPGA part for OOC synthesis. Default: {DEFAULT_PART}",
    )
    parser.add_argument(
        "--clock-period-ns",
        type=float,
        default=DEFAULT_CLOCK_PERIOD_NS,
        help=f"Clock constraint period in ns. Default: {DEFAULT_CLOCK_PERIOD_NS}",
    )
    args = parser.parse_args()

    vivado_bin = detect_vivado()
    output_dir = Path(args.output_dir).resolve()

    print(f"Vivado: {vivado_bin}")
    print(f"Output directory: {output_dir}")
    run_vivado(vivado_bin, output_dir, args.part, args.clock_period_ns)
    metrics = parse_metrics(output_dir, args.part, args.clock_period_ns)
    metrics_path = output_dir / "block5_vivado_ooc_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print("Vivado OOC report generation completed.")
    print(f"Metrics JSON: {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
