#!/usr/bin/env python3
"""Run independent Vivado placement/routing variants from the post-opt snapshot."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from generate_block5_vivado_reports import detect_vivado


ROOT = Path(__file__).resolve().parents[1]
TCL_SCRIPT = (
    ROOT / "hardware" / "7020_ad936x_sdr" / "run_snapshot_implementation_variant.tcl"
)
DEFAULT_OUTPUT_DIR = ROOT / "tmp" / "snapshot_impl_sweep"


@dataclass(frozen=True)
class Variant:
    name: str
    strategy: str
    place_directive: str
    phys_directive: str
    route_directive: str
    tns_cleanup: bool = False
    post_route_phys: str = "none"


VARIANTS = (
    Variant("impl_perf_explore_repeat", "Performance_Explore", "Explore", "Explore", "Explore"),
    Variant(
        "impl_perf_postroute",
        "Performance_ExplorePostRoutePhysOpt",
        "Explore",
        "Explore",
        "Explore",
        tns_cleanup=True,
        post_route_phys="Explore",
    ),
    Variant(
        "impl_perf_netdelay_high",
        "Performance_NetDelay_high",
        "ExtraNetDelay_high",
        "AggressiveExplore",
        "NoTimingRelaxation",
    ),
    Variant(
        "impl_perf_extra_timing",
        "Performance_ExtraTimingOpt",
        "ExtraTimingOpt",
        "Explore",
        "NoTimingRelaxation",
    ),
    Variant(
        "impl_perf_refine",
        "Performance_RefinePlacement",
        "ExtraPostPlacementOpt",
        "Explore",
        "Explore",
    ),
)


def run_variant(vivado: Path, variant: Variant, output_dir: Path) -> tuple[str, int]:
    run_dir = output_dir / variant.name
    run_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = run_dir / "driver_stdout.log"
    log_path = run_dir / "vivado.log"
    journal_path = run_dir / "vivado.jou"
    command = [
        "cmd.exe",
        "/d",
        "/c",
        str(vivado),
        "-mode",
        "batch",
        "-source",
        str(TCL_SCRIPT),
        "-log",
        str(log_path),
        "-journal",
        str(journal_path),
        "-tclargs",
        variant.name,
        variant.place_directive,
        variant.phys_directive,
        variant.route_directive,
        "1" if variant.tns_cleanup else "0",
        variant.post_route_phys,
    ]
    print(f"START {variant.name}: {variant.strategy}", flush=True)
    with stdout_path.open("w", encoding="utf-8") as stdout:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            stdout=stdout,
            stderr=subprocess.STDOUT,
            check=False,
        )
    print(f"DONE {variant.name}: exit={completed.returncode}", flush=True)
    return variant.name, completed.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--keep-existing", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.jobs < 1:
        raise ValueError("--jobs must be positive")
    output_dir = args.output_dir.resolve()
    if output_dir.exists() and not args.keep_existing:
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    vivado = detect_vivado()
    print(f"Vivado: {vivado}", flush=True)
    print(f"Output: {output_dir}", flush=True)
    results: dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = {
            executor.submit(run_variant, vivado, variant, output_dir): variant
            for variant in VARIANTS
        }
        for future in as_completed(futures):
            name, return_code = future.result()
            results[name] = return_code

    failed = [name for name, return_code in results.items() if return_code != 0]
    if failed:
        print(f"FAILED: {', '.join(sorted(failed))}", flush=True)
        return 1
    print("SWEEP_DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
