#!/usr/bin/env python3
"""Generate reproducible Vivado OOC evidence for the Block 8 CSS AXI top."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from generate_block5_vivado_reports import detect_vivado, normalize_reports
from generate_block8_css_vivado_reports import (
    DEFAULT_CLOCK_PERIOD_NS,
    DEFAULT_PART,
    parse_metrics,
    run_vivado,
    validate_metrics,
)


ROOT = Path(__file__).resolve().parents[1]
TOP_NAME = "css_sf7_axi_accelerator"
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "fpga" / "block8_css_axi_vivado_ooc_raw"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--part", default=DEFAULT_PART)
    parser.add_argument("--clock-period-ns", type=float, default=DEFAULT_CLOCK_PERIOD_NS)
    parser.add_argument(
        "--reuse",
        action="store_true",
        help="Parse and normalize an existing report directory without rerunning Vivado.",
    )
    args = parser.parse_args()

    vivado_bin = detect_vivado()
    output_dir = Path(args.output_dir).resolve()
    print(f"Vivado: {vivado_bin}")
    print(f"Output directory: {output_dir}")
    if not args.reuse:
        run_vivado(
            vivado_bin,
            output_dir,
            args.part,
            args.clock_period_ns,
            TOP_NAME,
        )
    normalize_reports(output_dir)
    metrics = parse_metrics(
        output_dir,
        args.part,
        args.clock_period_ns,
        TOP_NAME,
    )
    validate_metrics(metrics)

    latency = metrics["latency_cycles"]
    assert isinstance(latency, dict)
    latency["final_input_to_axis_result"] = latency.pop("final_input_to_done")
    latency["first_input_to_axis_result"] = latency.pop("first_input_to_done")
    latency["final_input_to_axi_lite_irq"] = (
        int(latency["final_input_to_axis_result"]) + 1
    )

    metrics_path = output_dir / "block8_css_axi_vivado_ooc_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print(f"Metrics JSON: {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
