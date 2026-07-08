#!/usr/bin/env python3
"""Capture, analyze, and aggregate a long multi-session RTL-SDR QPSK series."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CAPTURE = (
    ROOT
    / "blocks"
    / "block_11_integrated_sdr_project"
    / "python"
    / "lab_11_22_capture_runtime_pl_rtl_monitor_wav.py"
)
ANALYZE = (
    ROOT
    / "blocks"
    / "block_11_integrated_sdr_project"
    / "python"
    / "lab_11_28_read_rtl_wav_ota_qpsk.py"
)
AGGREGATE = ROOT / "tools" / "aggregate_lab11_28_sessions.py"
DATASET_DIR = ROOT / "datasets" / "lab11_22_runtime_pl_rtl_monitor"
ASSET_DIR = ROOT / "docs" / "assets"


def run(command: list[str]) -> None:
    print("RUN " + " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bit-bin-path", type=Path, required=True)
    parser.add_argument("--tag-stem", required=True)
    parser.add_argument("--session-count", type=int, default=10)
    parser.add_argument("--burst-count", type=int, default=100)
    parser.add_argument("--repeat-gap-ms", type=int, default=40)
    parser.add_argument("--rtl-max-capture-duration-s", type=float, default=None)
    parser.add_argument("--tx-attenuation-db", type=float, default=-50.0)
    parser.add_argument("--rtl-tuner-gain-db10", type=int, default=300)
    parser.add_argument("--rtl-read-mode", choices=["sync", "async"], default="async")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.session_count < 1 or args.burst_count < 1:
        raise ValueError("session and burst counts must be positive")
    bit_bin_path = args.bit_bin_path.resolve()
    if not bit_bin_path.is_file():
        raise FileNotFoundError(bit_bin_path)

    metrics_paths: list[Path] = []
    rtl_max_capture_duration_s = args.rtl_max_capture_duration_s or max(
        12.8,
        args.burst_count * 0.6,
    )
    for session_index in range(1, args.session_count + 1):
        tag = f"{args.tag_stem}_{session_index:02d}"
        manifest = DATASET_DIR / f"manifest_{tag}.yaml"
        metrics = (
            ASSET_DIR
            / f"lab1128_lab11_22_runtime_pl_rtl_monitor_{tag}_metrics.json"
        )
        print(
            f"SESSION {session_index}/{args.session_count}: {tag} "
            f"({args.burst_count} bursts)",
            flush=True,
        )
        run(
            [
                sys.executable,
                str(CAPTURE),
                "--modulation",
                "qpsk",
                "--bit-bin-path",
                str(bit_bin_path),
                "--center-frequency-hz",
                "868300000",
                "--sample-rate-hz",
                "3840000",
                "--rf-bandwidth-hz",
                "2000000",
                "--tx-attenuation-db",
                str(args.tx_attenuation_db),
                "--rtl-tuner-gain-db10",
                str(args.rtl_tuner_gain_db10),
                "--rtl-max-capture-duration-s",
                str(rtl_max_capture_duration_s),
                "--rtl-read-mode",
                args.rtl_read_mode,
                "--start-offset",
                "62",
                "--qpsk-symbol-count",
                "140",
                "--runtime-repeat-count",
                str(args.burst_count),
                "--runtime-repeat-gap-ms",
                str(args.repeat_gap_ms),
                "--capture-preroll-s",
                "0.4",
                "--capture-postroll-s",
                "0.4",
                "--rebind-runtime-dds-driver",
                "--rebind-runtime-adc-driver",
                "--runtime-dds-ratecntrl",
                "3",
                "--run-tag",
                tag,
            ]
        )
        run([sys.executable, str(ANALYZE), "--manifest", str(manifest)])
        if not metrics.is_file():
            raise FileNotFoundError(f"Analyzer did not create {metrics}")
        metrics_payload = json.loads(metrics.read_text(encoding="utf-8"))
        burst_summary = metrics_payload["burst_analysis"]["summary"]
        detected = int(burst_summary["detected_burst_count"])
        zero_error = int(burst_summary["zero_error_burst_count"])
        bit_errors = int(burst_summary["bit_errors_total"])
        if detected != args.burst_count or zero_error != args.burst_count or bit_errors != 0:
            raise RuntimeError(
                f"{tag}: strict qualification failed: detected={detected}/"
                f"{args.burst_count}, zero_error={zero_error}, bit_errors={bit_errors}"
            )
        metrics_paths.append(metrics)

    aggregate_json = ASSET_DIR / f"lab1128_{args.tag_stem}_qualification.json"
    aggregate_plot = ASSET_DIR / f"lab1128_{args.tag_stem}_summary.png"
    run(
        [
            sys.executable,
            str(AGGREGATE),
            *(str(path) for path in metrics_paths),
            "--json-out",
            str(aggregate_json),
            "--plot-out",
            str(aggregate_plot),
        ]
    )
    print(f"SERIES_DONE sessions={args.session_count} bursts={args.burst_count}", flush=True)
    print(f"AGGREGATE_JSON {aggregate_json}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
