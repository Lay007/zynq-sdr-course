#!/usr/bin/env python3
"""Summarize and optionally promote the Zynq snapshot implementation sweep."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from generate_integrated_vivado_reports import (
    REPORT_FILES,
    SNAPSHOT_OUTPUT_DIR,
    SNAPSHOT_SUMMARY_PATH,
    parse_integrated_metrics,
    promote_reports,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNS_ROOT = ROOT / "tmp" / "snapshot_impl_sweep"
DEFAULT_BASELINE_DIR = (
    ROOT / "tmp" / "vendor_xpr_course_overlay" / "zc702" / "zc702.runs" / "impl_1"
)
DEFAULT_JSON = ROOT / "reports" / "fpga" / "integrated-zynq-snapshot-implementation-sweep.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "fpga" / "integrated-zynq-snapshot-implementation-sweep.md"
DEFAULT_PLOT = ROOT / "docs" / "assets" / "integrated_zynq_snapshot_timing_sweep.png"

RUN_SPECS = (
    ("impl_1", "Performance_Explore"),
    ("impl_perf_explore_repeat", "Performance_Explore"),
    ("impl_perf_postroute", "Performance_ExplorePostRoutePhysOpt"),
    ("impl_perf_netdelay_high", "Performance_NetDelay_high"),
    ("impl_perf_extra_timing", "Performance_ExtraTimingOpt"),
    ("impl_perf_refine", "Performance_RefinePlacement"),
)


def repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def markdown_relative_link(target: Path, source_markdown: Path) -> str:
    return Path(os.path.relpath(target.resolve(), source_markdown.resolve().parent)).as_posix()


def run_status(run_dir: Path) -> str:
    if (run_dir / ".vivado.error.rst").exists():
        return "failed"
    if (run_dir / "system_top.bit").exists() and all(
        (run_dir / name).exists() for name in REPORT_FILES
    ):
        return "complete"
    if (run_dir / ".vivado.end.rst").exists():
        return "complete"
    if run_dir.exists():
        return "incomplete"
    return "missing"


def load_run(
    run_name: str,
    strategy: str,
    runs_root: Path,
    *,
    run_dir: Path | None = None,
) -> dict[str, Any]:
    run_dir = run_dir or (runs_root / run_name)
    record: dict[str, Any] = {
        "run_name": run_name,
        "strategy": strategy,
        "status": run_status(run_dir),
        "run_directory": repo_relative(run_dir),
    }
    missing = [name for name in REPORT_FILES if not (run_dir / name).is_file()]
    if missing:
        record["missing_reports"] = missing
        return record

    util_text = (run_dir / REPORT_FILES[0]).read_text(encoding="utf-8", errors="ignore")
    timing_text = (run_dir / REPORT_FILES[1]).read_text(encoding="utf-8", errors="ignore")
    route_text = (run_dir / REPORT_FILES[3]).read_text(encoding="utf-8", errors="ignore")
    record["metrics"] = parse_integrated_metrics(util_text, timing_text, route_text)
    bitstream = run_dir / "system_top.bit"
    record["bitstream"] = {
        "path": repo_relative(bitstream),
        "size_bytes": bitstream.stat().st_size if bitstream.is_file() else None,
        "sha256": sha256_file(bitstream) if bitstream.is_file() else None,
    }
    return record


def eligible_run(record: dict[str, Any]) -> bool:
    metrics = record.get("metrics")
    bitstream = record.get("bitstream", {})
    return bool(
        record.get("status") == "complete"
        and metrics
        and metrics["timing"]["timing_met"]
        and metrics["route"]["fully_routed"]
        and bitstream.get("sha256")
    )


def choose_best(runs: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [record for record in runs if eligible_run(record)]
    if not eligible:
        raise ValueError("No complete, fully routed, timing-clean sweep run with a bitstream")
    return max(eligible, key=lambda record: record["metrics"]["timing"]["wns_ns"])


def write_markdown(summary: dict[str, Any], path: Path, plot_path: Path) -> None:
    best_name = summary["selected_run"]
    lines = [
        "# Integrated Zynq snapshot implementation sweep",
        "",
        "All runs use the same synthesized `bridge_txrx_mux` snapshot and overlay timing constraints. Only the implementation strategy changes.",
        "",
        "| Run | Strategy | Status | WNS, ns | TNS, ns | Timing | Routed | Selected |",
        "|---|---|---|---:|---:|---|---|---|",
    ]
    for record in summary["runs"]:
        metrics = record.get("metrics", {})
        timing = metrics.get("timing", {})
        route = metrics.get("route", {})
        wns = timing.get("wns_ns")
        tns = timing.get("tns_ns")
        lines.append(
            "| {run} | `{strategy}` | {status} | {wns} | {tns} | {timing} | {routed} | {selected} |".format(
                run=record["run_name"],
                strategy=record["strategy"],
                status=record["status"],
                wns="N/A" if wns is None else f"{wns:.3f}",
                tns="N/A" if tns is None else f"{tns:.3f}",
                timing="PASS" if timing.get("timing_met") else "FAIL",
                routed="yes" if route.get("fully_routed") else "no",
                selected="yes" if record["run_name"] == best_name else "",
            )
        )
    lines.extend(
        [
            "",
            f"Selected implementation: `{best_name}` with WNS `{summary['selected_wns_ns']:.3f} ns`.",
            "",
            f"Timing-clean runs: `{summary['timing_clean_runs']}/{summary['completed_runs']}` completed runs.",
            "",
            "Selection by timing does not replace board qualification. The selected payload must still pass the runtime QPSK fabric and RF checks.",
            "",
            f"![Zynq snapshot timing sweep]({markdown_relative_link(plot_path, path)})",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_plot(summary: dict[str, Any], path: Path) -> None:
    plotted = [record for record in summary["runs"] if record.get("metrics")]
    labels = [record["run_name"].removeprefix("impl_perf_") for record in plotted]
    values = [record["metrics"]["timing"]["wns_ns"] for record in plotted]
    colors = ["#2f7d32" if value >= 0.0 else "#b23a33" for value in values]
    selected_index = next(
        index for index, record in enumerate(plotted) if record["run_name"] == summary["selected_run"]
    )
    colors[selected_index] = "#1565c0"

    fig, axis = plt.subplots(figsize=(10, 4.8))
    bars = axis.bar(labels, values, color=colors)
    axis.axhline(0.0, color="black", linewidth=0.8)
    axis.set_ylabel("Post-route WNS, ns")
    axis.set_title("Zynq snapshot implementation strategy sweep")
    axis.tick_params(axis="x", rotation=24)
    axis.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, values, strict=True):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            value,
            f"{value:+.3f}",
            ha="center",
            va="bottom" if value >= 0 else "top",
            fontsize=9,
        )
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    parser.add_argument("--baseline-dir", type=Path, default=DEFAULT_BASELINE_DIR)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--plot-out", type=Path, default=DEFAULT_PLOT)
    parser.add_argument(
        "--promote-best",
        action="store_true",
        help="Promote the best run into the canonical snapshot report set.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runs_root = args.runs_root.resolve()
    runs = [
        load_run(name, strategy, runs_root, run_dir=args.baseline_dir.resolve())
        if name == "impl_1"
        else load_run(name, strategy, runs_root)
        for name, strategy in RUN_SPECS
    ]
    best = choose_best(runs)
    completed = [record for record in runs if record["status"] == "complete"]
    timing_clean = [record for record in completed if eligible_run(record)]
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "runs_root": repo_relative(runs_root),
        "selected_run": best["run_name"],
        "selected_strategy": best["strategy"],
        "selected_wns_ns": best["metrics"]["timing"]["wns_ns"],
        "completed_runs": len(completed),
        "timing_clean_runs": len(timing_clean),
        "runs": runs,
    }
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_markdown(summary, args.markdown_out, args.plot_out)
    write_plot(summary, args.plot_out)

    if args.promote_best:
        promote_reports(
            impl_dir=runs_root / best["run_name"],
            output_dir=SNAPSHOT_OUTPUT_DIR,
            summary_path=SNAPSHOT_SUMMARY_PATH,
            flow_name=f"vendor snapshot bridge_txrx_mux / {best['strategy']}",
            require_timing=True,
        )

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
