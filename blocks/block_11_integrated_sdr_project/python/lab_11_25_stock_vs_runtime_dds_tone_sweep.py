#!/usr/bin/env python3
"""Lab 11.25 - Compare stock and runtime external DDS-tone visibility on RTL-SDR."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
BLOCK11_PYTHON_DIR = ROOT / "blocks" / "block_11_integrated_sdr_project" / "python"
BLOCK09_PYTHON_DIR = ROOT / "blocks" / "block_09_recording_and_analysis_tools" / "python"
if str(BLOCK11_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(BLOCK11_PYTHON_DIR))

from lab_11_14_stock_shell_bpsk_ota import repo_relative_or_str  # noqa: E402


DOC_ASSET_DIR = ROOT / "docs" / "assets"
TMP_SWEEP_ROOT = ROOT / "tmp" / "lab1125_stock_vs_runtime_dds_tone_sweep"
DEFAULT_JSON_STEM = "lab1125_stock_vs_runtime_dds_tone_sweep"
DEFAULT_CENTER_FREQUENCY_HZ = 915_000_000
DEFAULT_SAMPLE_RATE_HZ = 3_840_000
DEFAULT_RF_BANDWIDTH_HZ = 2_000_000
DEFAULT_TONE_OFFSETS_HZ = "50000,200000,700000"
DEFAULT_TONE_SCALE = 0.25
DEFAULT_RX_GAIN_DB = 10.0
DEFAULT_TX_ATTENUATION_DB = -40.0
DEFAULT_RTL_TUNER_GAIN_DB10 = 200
DEFAULT_MODES = "stock,runtime,runtime_bridge"


@dataclass(frozen=True)
class SweepConfig:
    center_frequency_hz: int
    sample_rate_hz: int
    rf_bandwidth_hz: int
    tone_offsets_hz: list[int]
    tone_scale: float
    rx_gain_db: float
    tx_attenuation_db: float
    rtl_tuner_gain_db10: int
    modes: list[str]
    dds_sync_start_enable: str | None
    keep_tmp: bool


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_run_tag() -> str:
    return f"live_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def parse_int_list(value: str) -> list[int]:
    items = [int(chunk.strip(), 0) for chunk in value.split(",") if chunk.strip()]
    if not items:
        raise argparse.ArgumentTypeError("Expected at least one integer value.")
    return items


def parse_mode_list(value: str) -> list[str]:
    items = [chunk.strip() for chunk in value.split(",") if chunk.strip()]
    valid = {"stock", "runtime", "runtime_bridge"}
    if not items:
        raise argparse.ArgumentTypeError("Expected at least one mode.")
    invalid = [item for item in items if item not in valid]
    if invalid:
        raise argparse.ArgumentTypeError(f"Unsupported modes: {', '.join(invalid)}")
    return items


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--center-frequency-hz", type=int, default=DEFAULT_CENTER_FREQUENCY_HZ)
    parser.add_argument("--sample-rate-hz", type=int, default=DEFAULT_SAMPLE_RATE_HZ)
    parser.add_argument("--rf-bandwidth-hz", type=int, default=DEFAULT_RF_BANDWIDTH_HZ)
    parser.add_argument("--tone-offsets-hz", type=parse_int_list, default=parse_int_list(DEFAULT_TONE_OFFSETS_HZ))
    parser.add_argument("--tone-scale", type=float, default=DEFAULT_TONE_SCALE)
    parser.add_argument("--rx-gain-db", type=float, default=DEFAULT_RX_GAIN_DB)
    parser.add_argument("--tx-attenuation-db", type=float, default=DEFAULT_TX_ATTENUATION_DB)
    parser.add_argument("--rtl-tuner-gain-db10", type=int, default=DEFAULT_RTL_TUNER_GAIN_DB10)
    parser.add_argument("--modes", type=parse_mode_list, default=parse_mode_list(DEFAULT_MODES))
    parser.add_argument("--dds-sync-start-enable", default=None)
    parser.add_argument("--run-tag", default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--keep-tmp", action="store_true")
    return parser


def build_default_json_out(run_tag: str) -> Path:
    return DOC_ASSET_DIR / f"{DEFAULT_JSON_STEM}_{run_tag}.json"


def point_dir(run_tag: str, label: str) -> Path:
    return TMP_SWEEP_ROOT / run_tag / label


def point_label(mode: str, tone_offset_hz: int) -> str:
    return f"{mode}_{tone_offset_hz // 1000:04d}k"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def first_metrics_json(path: Path) -> Path:
    matches = sorted(path.glob("*_metrics.json"))
    if not matches:
        raise FileNotFoundError(f"No metrics JSON found in {path}")
    return matches[0]


def run_subprocess(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=900_000,
    )


def stdout_tail(text: str, lines: int = 16) -> list[str]:
    rows = [row for row in text.splitlines() if row.strip()]
    return rows[-lines:]


def mode_capture_args(mode: str) -> tuple[list[str], bool]:
    if mode == "stock":
        return ["--mode", "stock", "--no-reboot-after"], False
    if mode == "runtime":
        return ["--mode", "runtime"], True
    if mode == "runtime_bridge":
        return ["--mode", "runtime", "--bridge-bursts"], True
    raise ValueError(f"Unsupported mode: {mode}")


def classify_peak(expected_offset_hz: float, measured_peak_hz: float) -> str:
    if abs(measured_peak_hz - expected_offset_hz) <= 25_000.0:
        return "near_expected"
    if abs(measured_peak_hz) <= 25_000.0:
        return "near_dc"
    return "other"


def extract_dds_summary(report: dict[str, Any]) -> dict[str, Any]:
    dds_after = report.get("dds_after_config") or {}
    return {
        "altvoltage0_frequency_hz": dds_after.get("altvoltage0", {}).get("frequency"),
        "altvoltage0_phase_mdeg": dds_after.get("altvoltage0", {}).get("phase"),
        "altvoltage0_scale": dds_after.get("altvoltage0", {}).get("scale"),
        "altvoltage2_frequency_hz": dds_after.get("altvoltage2", {}).get("frequency"),
        "altvoltage2_phase_mdeg": dds_after.get("altvoltage2", {}).get("phase"),
        "altvoltage2_scale": dds_after.get("altvoltage2", {}).get("scale"),
    }


def run_capture_and_analysis(
    *,
    cfg: SweepConfig,
    run_tag: str,
    mode: str,
    tone_offset_hz: int,
) -> dict[str, Any]:
    label = point_label(mode, tone_offset_hz)
    root_dir = point_dir(run_tag, label)
    analysis_dir = root_dir / "analysis"
    root_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)

    wav_out = root_dir / "capture.wav"
    manifest_out = root_dir / "manifest.yaml"
    report_out = root_dir / "capture_report.json"
    capture_mode_args, runtime_like = mode_capture_args(mode)

    capture_command = [
        sys.executable,
        str(BLOCK11_PYTHON_DIR / "lab_11_24_capture_dds_tone_rtl_monitor_wav.py"),
        *capture_mode_args,
        "--center-frequency-hz",
        str(cfg.center_frequency_hz),
        "--sample-rate-hz",
        str(cfg.sample_rate_hz),
        "--rf-bandwidth-hz",
        str(cfg.rf_bandwidth_hz),
        "--tone-offset-hz",
        str(tone_offset_hz),
        "--tone-scale",
        str(cfg.tone_scale),
        "--rx-gain-db",
        str(cfg.rx_gain_db),
        "--tx-attenuation-db",
        str(cfg.tx_attenuation_db),
        "--rtl-tuner-gain-db10",
        str(cfg.rtl_tuner_gain_db10),
        "--run-tag",
        label,
        "--wav-out",
        str(wav_out),
        "--manifest-out",
        str(manifest_out),
        "--report-out",
        str(report_out),
    ]
    if cfg.dds_sync_start_enable is not None:
        capture_command.extend(["--dds-sync-start-enable", cfg.dds_sync_start_enable])
    capture_result = run_subprocess(capture_command, cwd=ROOT)
    capture_ok = capture_result.returncode == 0 and manifest_out.exists() and report_out.exists()

    analysis_result: subprocess.CompletedProcess[str] | None = None
    metrics_path: Path | None = None
    metrics: dict[str, Any] | None = None
    if capture_ok:
        analysis_command = [
            sys.executable,
            str(BLOCK09_PYTHON_DIR / "lab_9_4_read_wav_iq_and_analyze.py"),
            "--manifest",
            str(manifest_out),
            "--out-dir",
            str(analysis_dir),
        ]
        analysis_result = run_subprocess(analysis_command, cwd=ROOT)
        if analysis_result.returncode == 0:
            metrics_path = first_metrics_json(analysis_dir)
            metrics = load_json(metrics_path)

    report = load_json(report_out) if report_out.exists() else {}
    rtl_capture = report.get("rtl_capture") or {}
    summary = report.get("summary") or {}
    case_payload: dict[str, Any] = {
        "label": label,
        "mode": mode,
        "runtime_like": runtime_like,
        "tone_offset_hz": tone_offset_hz,
        "capture_ok": capture_ok,
        "capture_returncode": capture_result.returncode,
        "capture_stdout_tail": stdout_tail(capture_result.stdout),
        "capture_stderr_tail": stdout_tail(capture_result.stderr),
        "manifest_path": repo_relative_or_str(manifest_out),
        "capture_report_path": repo_relative_or_str(report_out),
        "analysis_dir": str(analysis_dir),
        "analysis_ok": bool(metrics is not None),
        "analysis_returncode": analysis_result.returncode if analysis_result is not None else None,
        "analysis_stdout_tail": stdout_tail(analysis_result.stdout) if analysis_result is not None else [],
        "analysis_stderr_tail": stdout_tail(analysis_result.stderr) if analysis_result is not None else [],
        "analysis_metrics_path": repo_relative_or_str(metrics_path) if metrics_path is not None else None,
        "runtime_summary": summary,
        "rtl_capture": {
            "raw_u8_mean": rtl_capture.get("raw_u8_mean"),
            "raw_u8_std": rtl_capture.get("raw_u8_std"),
            "raw_u8_min": rtl_capture.get("raw_u8_min"),
            "raw_u8_max": rtl_capture.get("raw_u8_max"),
            "rtl_device_name": rtl_capture.get("rtl_device_name"),
            "bytes_captured": rtl_capture.get("bytes_captured"),
        },
        "dds_after_config": extract_dds_summary(report),
        "dds_device_after_config": report.get("dds_device_after_config"),
        "bitstream_md5": (report.get("upload") or {}).get("md5"),
        "metrics": metrics,
    }
    if metrics is not None:
        case_payload["peak_class"] = classify_peak(
            float(metrics["expected_offset_hz"]),
            float(metrics["measured_peak_hz"]),
        )
    else:
        case_payload["peak_class"] = "analysis_failed"
    return case_payload


def comparison_against_stock(stock_case: dict[str, Any] | None, other_case: dict[str, Any] | None) -> dict[str, Any] | None:
    if stock_case is None or other_case is None:
        return None
    stock_metrics = stock_case.get("metrics")
    other_metrics = other_case.get("metrics")
    if stock_metrics is None or other_metrics is None:
        return None
    stock_capture = stock_case.get("rtl_capture") or {}
    other_capture = other_case.get("rtl_capture") or {}
    stock_std = stock_capture.get("raw_u8_std")
    other_std = other_capture.get("raw_u8_std")
    return {
        "stock_mode": stock_case["mode"],
        "other_mode": other_case["mode"],
        "stock_quality_pass": stock_metrics["quality_pass"],
        "other_quality_pass": other_metrics["quality_pass"],
        "stock_peak_class": stock_case["peak_class"],
        "other_peak_class": other_case["peak_class"],
        "measured_peak_delta_hz": float(other_metrics["measured_peak_hz"]) - float(stock_metrics["measured_peak_hz"]),
        "frequency_error_delta_hz": float(other_metrics["frequency_error_hz"]) - float(stock_metrics["frequency_error_hz"]),
        "peak_dbfs_delta": float(other_metrics["peak_dbfs"]) - float(stock_metrics["peak_dbfs"]),
        "snr_db_delta": float(other_metrics["snr_db"]) - float(stock_metrics["snr_db"]),
        "dc_offset_delta": float(other_metrics["dc_offset_magnitude"]) - float(stock_metrics["dc_offset_magnitude"]),
        "raw_u8_std_ratio": (
            float(other_std) / float(stock_std)
            if stock_std not in (None, 0.0) and other_std is not None
            else None
        ),
    }


def summarize_by_offset(results: list[dict[str, Any]]) -> dict[str, Any]:
    offsets = sorted({int(item["tone_offset_hz"]) for item in results})
    summary: dict[str, Any] = {}
    for tone_offset_hz in offsets:
        offset_cases = [item for item in results if int(item["tone_offset_hz"]) == tone_offset_hz]
        by_mode = {item["mode"]: item for item in offset_cases}
        stock_case = by_mode.get("stock")
        summary[str(tone_offset_hz)] = {
            "modes": {
                mode: {
                    "capture_ok": item["capture_ok"],
                    "analysis_ok": item["analysis_ok"],
                    "peak_class": item["peak_class"],
                    "raw_u8_std": (item.get("rtl_capture") or {}).get("raw_u8_std"),
                    "measured_peak_hz": (item.get("metrics") or {}).get("measured_peak_hz"),
                    "frequency_error_hz": (item.get("metrics") or {}).get("frequency_error_hz"),
                    "peak_dbfs": (item.get("metrics") or {}).get("peak_dbfs"),
                    "snr_db": (item.get("metrics") or {}).get("snr_db"),
                    "quality_pass": (item.get("metrics") or {}).get("quality_pass"),
                    "bitstream_md5": item.get("bitstream_md5"),
                }
                for mode, item in by_mode.items()
            },
            "runtime_vs_stock": comparison_against_stock(stock_case, by_mode.get("runtime")),
            "runtime_bridge_vs_stock": comparison_against_stock(stock_case, by_mode.get("runtime_bridge")),
        }
    return summary


def build_conclusion(results: list[dict[str, Any]]) -> str:
    stock_ok = [
        item for item in results
        if item["mode"] == "stock" and item.get("metrics", {}).get("quality_pass") is True
    ]
    runtime_fail = [
        item for item in results
        if item["mode"] == "runtime" and item.get("metrics", {}).get("quality_pass") is False
    ]
    runtime_bridge_fail = [
        item for item in results
        if item["mode"] == "runtime_bridge" and item.get("metrics", {}).get("quality_pass") is False
    ]
    near_dc_runtime = [
        item for item in results
        if item["mode"].startswith("runtime") and item.get("peak_class") == "near_dc"
    ]
    if stock_ok and runtime_fail:
        if runtime_bridge_fail:
            return (
                "Stock-shell DDS tone remains externally visible, while both runtime idle and "
                "runtime bridge-burst cases still fail the external tone quality gate."
            )
        if near_dc_runtime:
            return (
                "Stock-shell DDS tone remains externally visible, while the runtime overlay "
                "still collapses the dominant external peak toward DC."
            )
    return "The sweep completed and produced per-mode external DDS-tone evidence."


def main() -> int:
    args = build_arg_parser().parse_args()
    run_tag = args.run_tag or default_run_tag()
    json_out = args.json_out.resolve() if args.json_out is not None else build_default_json_out(run_tag)
    cfg = SweepConfig(
        center_frequency_hz=args.center_frequency_hz,
        sample_rate_hz=args.sample_rate_hz,
        rf_bandwidth_hz=args.rf_bandwidth_hz,
        tone_offsets_hz=args.tone_offsets_hz,
        tone_scale=args.tone_scale,
        rx_gain_db=args.rx_gain_db,
        tx_attenuation_db=args.tx_attenuation_db,
        rtl_tuner_gain_db10=args.rtl_tuner_gain_db10,
        modes=args.modes,
        dds_sync_start_enable=args.dds_sync_start_enable,
        keep_tmp=bool(args.keep_tmp),
    )

    results: list[dict[str, Any]] = []
    for tone_offset_hz in cfg.tone_offsets_hz:
        for mode in cfg.modes:
            results.append(
                run_capture_and_analysis(
                    cfg=cfg,
                    run_tag=run_tag,
                    mode=mode,
                    tone_offset_hz=tone_offset_hz,
                )
            )

    payload = {
        "timestamp_utc": iso_now(),
        "run_tag": run_tag,
        "config": asdict(cfg),
        "results": results,
        "summary_by_offset_hz": summarize_by_offset(results),
        "conclusion": build_conclusion(results),
    }

    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if not cfg.keep_tmp:
        sweep_tmp_root = TMP_SWEEP_ROOT / run_tag
        if sweep_tmp_root.exists():
            shutil.rmtree(sweep_tmp_root)

    print("Lab 11.25 - Stock vs runtime DDS-tone external visibility sweep")
    print(f"Summary JSON: {repo_relative_or_str(json_out)}")
    print(f"Conclusion: {payload['conclusion']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
