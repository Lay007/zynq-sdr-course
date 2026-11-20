#!/usr/bin/env python3
"""Extract routed Vivado and Icarus results for the FIR comparison."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from run_fir_architectures import MODES, ROOT, SEED


def match(pattern: str, text: str) -> re.Match:
    result = re.search(pattern, text, re.MULTILINE)
    if result is None:
        raise ValueError(f"Missing report field: {pattern}")
    return result


def read_routed(reports: Path, name: str) -> tuple[dict, dict]:
    """Read a fully routed, constrained run using the common OOC XDC."""
    util = (reports / f"{name}_utilization.rpt").read_text(encoding="utf-8")
    timing = (reports / f"{name}_timing.rpt").read_text(encoding="utf-8")
    route = (reports / f"{name}_route.rpt").read_text(encoding="utf-8")

    match(r"^\| Design State\s*:\s*Routed\s*$", util)
    nets = int(match(r"# of routable nets\.+\s*:\s*(\d+)", route)[1])
    routed = int(match(r"# of fully routed nets\.+\s*:\s*(\d+)", route)[1])
    errors = int(match(r"# of nets with routing errors\.+\s*:\s*(\d+)", route)[1])
    if not nets or nets != routed or errors:
        raise ValueError(f"{name}: incomplete routing")
    for check in ("no_clock", "unconstrained_internal_endpoints", "no_input_delay",
                  "no_output_delay", "partial_input_delay", "partial_output_delay"):
        match(rf"checking {check} \(0\)", timing)

    period = float(match(r"^fir_clk\s+\{[^}]+\}\s+(\S+)", timing)[1])
    setup, tns, hold, ths = map(float, match(
        r"^fir_clk\s+(\S+)\s+(\S+)\s+\d+\s+\d+\s+(\S+)\s+(\S+)", timing,
    ).groups())
    metadata = {
        "tool_version": match(r"^\| Tool Version\s*:\s*(.+)$", util)[1].strip(),
        "device": match(r"^\| Device\s*:\s*(\S+)", util)[1],
        "clock_period_ns": period,
    }
    resources = {
        "slice_luts": int(match(r"^\| Slice LUTs\s*\|\s*(\d+)", util)[1]),
        "slice_flip_flops": int(match(r"^\|\s+Register as Flip Flop\s*\|\s*(\d+)", util)[1]),
        "dsp48e1": int(match(r"^\| DSPs\s*\|\s*(\d+)", util)[1]),
        "bram_tiles": float(match(r"^\| Block RAM Tile\s*\|\s*([\d.]+)", util)[1]),
        "wns_ns": setup, "tns_ns": tns, "whs_ns": hold, "ths_ns": ths,
        "routed_nets": routed,
    }
    return metadata, resources


def read_results(reports: Path, simulations: Path) -> dict:
    result = {"rtl_simulation": {"seed": SEED}, "post_route_ooc": {}, "variants": {}}
    for number, name in enumerate(MODES):
        metadata, resources = read_routed(reports, name)
        period = metadata["clock_period_ns"]
        sim = (simulations / f"{name}.txt").read_text(encoding="utf-8")
        if result["post_route_ooc"] and metadata != result["post_route_ooc"]:
            raise ValueError("Reports use different tools, devices or clocks")
        result["post_route_ooc"] = metadata
        expected = match(
            rf"^PASS ARCH={number} compared=([1-9]\d*) latency=(\d+) ii=(\d+) stalled_input_cycles=(\d+)$", sim,
        )
        compared, latency, ii, stalls = map(int, expected.groups())
        result["variants"][name] = {
            "compared_iq_samples": compared,
            "latency_clocks": latency,
            "initiation_interval_clocks": ii,
            "stalled_input_cycles": stalls,
            "scheduled_msps_at_target_clock": 1000 / (period * ii),
            **resources,
        }
    paths = (
        "blocks/block_05_fpga_hdl_flow/rtl/fir_iq_architectures.sv",
        "blocks/block_05_fpga_hdl_flow/tb/tb_fir_iq_architectures.sv",
        "tools/run_fir_architectures.py",
        "tools/vivado_fir_architectures.tcl",
        "tools/fir_architectures_ooc.xdc",
    )
    # Verilog, Python and constraint files are tracked with LF line endings.
    result["source_sha256"] = {
        path: hashlib.sha256((ROOT / path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for path in paths
    }
    return result


def plot_results(result: dict, path: Path, *, russian: bool = False) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    variants = result["variants"]
    labels = (["Параллельный", "С разделением\nпо времени", "Конвейерный"] if russian
              else [name.capitalize() for name in variants])
    colors = ["#226184", "#a04018", "#2e7555"]
    fig, axes = plt.subplots(1, 2, figsize=(8, 3), layout="constrained")
    clock = 1000 / result["post_route_ooc"]["clock_period_ns"]
    units = ("Блоки DSP48E1", "Запас по установке, нс") if russian else ("DSP48E1 blocks", "Setup slack (ns)")
    for axis, key, label in zip(axes, ("dsp48e1", "wns_ns"), units):
        values = [row[key] for row in variants.values()]
        bars = axis.bar(labels, values, color=colors, width=0.55)
        axis.bar_label(bars, fmt="%g", padding=3)
        axis.set_ylabel(label)
        axis.margins(y=0.22)
        axis.grid(axis="y", alpha=0.24)
        axis.set_axisbelow(True)
        axis.axhline(0, linewidth=0.8, color="#333333")
    fig.suptitle(f"FIR после трассировки на {clock:g} МГц (Zynq-7020, вне проекта)" if russian
                 else f"Routed FIR comparison at {clock:g} MHz (Zynq-7020, out of context)")
    fig.savefig(path, dpi=170)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", type=Path)
    parser.add_argument("simulations", type=Path)
    parser.add_argument("output", type=Path, help="Directory for metrics JSON and comparison plot")
    args = parser.parse_args()
    result = read_results(args.reports, args.simulations)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "lab513_fir_architectures.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n",
    )
    plot_results(result, args.output / "lab513_fir_architectures.png")
    plot_results(result, args.output / "lab513_fir_architectures_ru.png", russian=True)


if __name__ == "__main__":
    main()
