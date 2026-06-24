#!/usr/bin/env python3
"""Lab 11.23 - Focused runtime/PL RTL-SDR monitor sweep around the live BPSK point."""

from __future__ import annotations

import argparse
import itertools
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
if str(BLOCK11_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(BLOCK11_PYTHON_DIR))

from lab_11_13_stock_vs_runtime_rx_compare import try_reboot_to_stock  # noqa: E402
from lab_11_14_stock_shell_bpsk_ota import repo_relative_or_str  # noqa: E402
from lab_11_15_runtime_bridge_rx_host_tx_probe import (  # noqa: E402
    DEFAULT_CENTER_FREQUENCY_HZ,
    DEFAULT_HOST,
    DEFAULT_IIO_URI,
    DEFAULT_PASSWORD,
    DEFAULT_PORT,
    DEFAULT_REMOTE_FIRMWARE_NAME,
    DEFAULT_TIMEOUT_S,
    DEFAULT_USER,
)
from lab_11_21_capture_rtl_sdr_monitor_wav import DEFAULT_RTL_TUNER_GAIN_DB10  # noqa: E402
from lab_11_7_axi_lite_bpsk_bringup import ParamikoCommandRunner  # noqa: E402


DOC_ASSET_DIR = ROOT / "docs" / "assets"
DATASET_DIR = ROOT / "datasets" / "lab11_22_runtime_pl_rtl_monitor"
TMP_SWEEP_ROOT = ROOT / "tmp" / "lab1123_runtime_pl_rtl_monitor_sweep"
DEFAULT_JSON_STEM = "lab1123_runtime_pl_rtl_monitor_sweep"
DEFAULT_START_OFFSETS = "58,59,60"
DEFAULT_RX_GAINS_DB = "5,10"
DEFAULT_TX_ATTENUATIONS_DB = "-50,-45"
DEFAULT_STAGE2_TUNER_GAINS_DB10 = "120,166,200,250"
DEFAULT_START_OFFSET = 59
DEFAULT_RX_GAIN_DB = 5.0
DEFAULT_TX_ATTENUATION_DB = -50.0
DEFAULT_REBOOT_TIMEOUT_S = 120.0
DEFAULT_RUNTIME_REPEAT_COUNT = 3
DEFAULT_RUNTIME_REPEAT_GAP_MS = 100
DEFAULT_RUNTIME_BIT_BIN_PATH = ROOT / "tmp" / "bridge_txrx_mux.wordswap.bit.bin"


@dataclass(frozen=True)
class SweepConfig:
    ssh_host: str
    ssh_user: str
    ssh_port: int
    ssh_timeout_s: float
    ssh_password: str
    iio_uri: str
    bit_bin_path: str
    remote_firmware_name: str
    center_frequency_hz: int
    sample_rate_hz: int
    rf_bandwidth_hz: int
    start_offsets: list[int]
    rx_gains_db: list[float]
    tx_attenuations_db: list[float]
    stage1_rtl_tuner_gain_db10: int
    stage2_tuner_gains_db10: list[int]
    runtime_repeat_count: int
    runtime_repeat_gap_ms: int
    reboot_timeout_s: float
    keep_tmp: bool
    final_evidence: bool


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_run_tag() -> str:
    return f"live_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def parse_int_list(value: str) -> list[int]:
    items = [int(chunk.strip(), 0) for chunk in value.split(",") if chunk.strip()]
    if not items:
        raise argparse.ArgumentTypeError("Expected at least one integer value.")
    return items


def parse_float_list(value: str) -> list[float]:
    items = [float(chunk.strip()) for chunk in value.split(",") if chunk.strip()]
    if not items:
        raise argparse.ArgumentTypeError("Expected at least one float value.")
    return items


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-host", default=DEFAULT_HOST)
    parser.add_argument("--ssh-user", default=DEFAULT_USER)
    parser.add_argument("--ssh-password", default=DEFAULT_PASSWORD)
    parser.add_argument("--ssh-port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--ssh-timeout-s", type=float, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--iio-uri", default=DEFAULT_IIO_URI)
    parser.add_argument("--bit-bin-path", type=Path, default=DEFAULT_RUNTIME_BIT_BIN_PATH)
    parser.add_argument("--remote-firmware-name", default=DEFAULT_REMOTE_FIRMWARE_NAME)
    parser.add_argument("--center-frequency-hz", type=int, default=DEFAULT_CENTER_FREQUENCY_HZ)
    parser.add_argument("--sample-rate-hz", type=int, default=3_840_000)
    parser.add_argument("--rf-bandwidth-hz", type=int, default=2_000_000)
    parser.add_argument("--start-offsets", type=parse_int_list, default=parse_int_list(DEFAULT_START_OFFSETS))
    parser.add_argument("--rx-gains-db", type=parse_float_list, default=parse_float_list(DEFAULT_RX_GAINS_DB))
    parser.add_argument("--tx-attenuations-db", type=parse_float_list, default=parse_float_list(DEFAULT_TX_ATTENUATIONS_DB))
    parser.add_argument("--stage1-rtl-tuner-gain-db10", type=int, default=DEFAULT_RTL_TUNER_GAIN_DB10)
    parser.add_argument(
        "--stage2-tuner-gains-db10",
        type=parse_int_list,
        default=parse_int_list(DEFAULT_STAGE2_TUNER_GAINS_DB10),
    )
    parser.add_argument("--runtime-repeat-count", type=int, default=DEFAULT_RUNTIME_REPEAT_COUNT)
    parser.add_argument("--runtime-repeat-gap-ms", type=int, default=DEFAULT_RUNTIME_REPEAT_GAP_MS)
    parser.add_argument("--reboot-timeout-s", type=float, default=DEFAULT_REBOOT_TIMEOUT_S)
    parser.add_argument("--run-tag", default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--keep-tmp", action="store_true")
    parser.add_argument("--final-evidence", action=argparse.BooleanOptionalAction, default=True)
    return parser


def build_default_json_out(run_tag: str) -> Path:
    return DOC_ASSET_DIR / f"{DEFAULT_JSON_STEM}_{run_tag}.json"


def point_label(stage: str, index: int, total: int) -> str:
    width = max(len(str(total)), 2)
    return f"{stage}_p{index:0{width}d}"


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


def maybe_reboot_to_stock(cfg: SweepConfig) -> dict[str, Any]:
    runner = ParamikoCommandRunner(
        host=cfg.ssh_host,
        user=cfg.ssh_user,
        password=cfg.ssh_password,
        port=cfg.ssh_port,
        key_path=None,
        timeout_s=cfg.ssh_timeout_s,
    )
    try:
        return try_reboot_to_stock(
            runner,
            host=cfg.ssh_host,
            user=cfg.ssh_user,
            password=cfg.ssh_password,
            port=cfg.ssh_port,
            ssh_timeout_s=cfg.ssh_timeout_s,
            iio_uri=cfg.iio_uri,
            timeout_s=cfg.reboot_timeout_s,
        )
    finally:
        runner.close()


def point_dir(run_tag: str, label: str) -> Path:
    return TMP_SWEEP_ROOT / run_tag / label


def run_capture_and_analysis(
    *,
    cfg: SweepConfig,
    run_tag: str,
    label: str,
    start_offset: int,
    rx_gain_db: float,
    tx_attenuation_db: float,
    rtl_tuner_gain_db10: int,
    reboot_after: bool,
) -> dict[str, Any]:
    root_dir = point_dir(run_tag, label)
    analysis_dir = root_dir / "analysis"
    root_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)

    wav_out = root_dir / "capture.wav"
    manifest_out = root_dir / "manifest.yaml"
    capture_report_out = root_dir / "capture_report.json"
    runtime_json_out = root_dir / "runtime_report.json"

    capture_command = [
        sys.executable,
        str(BLOCK11_PYTHON_DIR / "lab_11_22_capture_runtime_pl_rtl_monitor_wav.py"),
        "--ssh-host",
        cfg.ssh_host,
        "--ssh-user",
        cfg.ssh_user,
        "--ssh-password",
        cfg.ssh_password,
        "--ssh-port",
        str(cfg.ssh_port),
        "--ssh-timeout-s",
        str(cfg.ssh_timeout_s),
        "--iio-uri",
        cfg.iio_uri,
        "--bit-bin-path",
        cfg.bit_bin_path,
        "--remote-firmware-name",
        cfg.remote_firmware_name,
        "--center-frequency-hz",
        str(cfg.center_frequency_hz),
        "--sample-rate-hz",
        str(cfg.sample_rate_hz),
        "--rf-bandwidth-hz",
        str(cfg.rf_bandwidth_hz),
        "--start-offset",
        str(start_offset),
        "--rx-gain-db",
        str(rx_gain_db),
        "--tx-attenuation-db",
        str(tx_attenuation_db),
        "--rtl-tuner-gain-db10",
        str(rtl_tuner_gain_db10),
        "--runtime-repeat-count",
        str(cfg.runtime_repeat_count),
        "--runtime-repeat-gap-ms",
        str(cfg.runtime_repeat_gap_ms),
        "--run-tag",
        label,
        "--wav-out",
        str(wav_out),
        "--manifest-out",
        str(manifest_out),
        "--capture-report-out",
        str(capture_report_out),
        "--runtime-json-out",
        str(runtime_json_out),
    ]
    capture_command.append("--reboot-after" if reboot_after else "--no-reboot-after")
    capture_completed = run_subprocess(capture_command, cwd=ROOT)

    row: dict[str, Any] = {
        "label": label,
        "start_offset": start_offset,
        "rx_gain_db": rx_gain_db,
        "tx_attenuation_db": tx_attenuation_db,
        "rtl_tuner_gain_db10": rtl_tuner_gain_db10,
        "capture_returncode": int(capture_completed.returncode),
        "capture_stdout_tail": capture_completed.stdout.splitlines()[-20:],
        "capture_stderr_tail": capture_completed.stderr.splitlines()[-20:],
        "manifest_path": str(manifest_out),
        "capture_report_path": str(capture_report_out),
        "runtime_json_path": str(runtime_json_out),
        "analysis_dir": str(analysis_dir),
        "analysis_ok": False,
        "capture_ok": False,
    }

    if capture_completed.returncode != 0:
        return row
    if not manifest_out.exists() or not runtime_json_out.exists():
        row["capture_error"] = "Capture finished without the expected manifest/runtime JSON outputs."
        return row

    runtime_payload = load_json(runtime_json_out)
    row["capture_ok"] = True
    row["runtime_summary"] = runtime_payload.get("summary")
    row["runtime_attempts"] = len(runtime_payload.get("runtime_attempts") or [])
    row["runtime_internal_best"] = runtime_payload.get("summary") or {}

    analysis_command = [
        sys.executable,
        str(BLOCK11_PYTHON_DIR / "lab_11_20_read_rtl_wav_ota_bpsk_ber.py"),
        "--manifest",
        str(manifest_out),
        "--out-dir",
        str(analysis_dir),
        "--run-tag",
        label,
    ]
    analysis_completed = run_subprocess(analysis_command, cwd=ROOT)
    row["analysis_returncode"] = int(analysis_completed.returncode)
    row["analysis_stdout_tail"] = analysis_completed.stdout.splitlines()[-20:]
    row["analysis_stderr_tail"] = analysis_completed.stderr.splitlines()[-20:]
    if analysis_completed.returncode != 0:
        return row

    metrics_path = first_metrics_json(analysis_dir)
    metrics = load_json(metrics_path)
    detection = metrics.get("detection") or {}
    row["analysis_ok"] = True
    row["analysis_metrics_path"] = str(metrics_path)
    row["analysis_detection"] = {
        "bit_errors_total": int(detection.get("bit_errors_total") or 0),
        "bit_errors_payload": int(detection.get("bit_errors_payload") or 0),
        "ber_total": float(detection.get("ber_total") or 0.0),
        "ber_payload": float(detection.get("ber_payload") or 0.0),
        "evm_percent": float(detection.get("evm_percent") or 0.0),
    }
    row["analysis_frequency_shift_hz"] = float(metrics.get("total_frequency_shift_hz") or 0.0)
    row["analysis_peak_level_dbfs"] = float(metrics.get("peak_level_dbfs") or 0.0)
    row["analysis_rms_level_dbfs"] = float(metrics.get("rms_level_dbfs") or 0.0)
    return row


def external_score(row: dict[str, Any]) -> tuple[int, int, int, int, int, float]:
    if not row.get("analysis_ok"):
        internal = row.get("runtime_internal_best") or {}
        return (
            0,
            int(internal.get("received_bits") or 0),
            -int(internal.get("payload_errors") or 10**9),
            -int(internal.get("total_errors") or 10**9),
            -10**9,
            -10**9,
            -10**9,
        )
    det = row.get("analysis_detection") or {}
    internal = row.get("runtime_internal_best") or {}
    return (
        1,
        -int(det.get("bit_errors_total") or 10**9),
        -int(det.get("bit_errors_payload") or 10**9),
        -int(internal.get("received_bits") or 0),
        -int(internal.get("payload_errors") or 10**9),
        -float(det.get("evm_percent") or 10**9),
    )


def choose_best(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    return max(rows, key=external_score)


def build_summary(
    *,
    stage1_rows: list[dict[str, Any]],
    stage2_rows: list[dict[str, Any]],
    best_final: dict[str, Any] | None,
) -> dict[str, Any]:
    best_stage1 = choose_best(stage1_rows)
    best_stage2 = choose_best(stage2_rows)
    best_overall = choose_best([*(stage1_rows or []), *(stage2_rows or [])])
    conclusion = "No runtime/RTL sweep point completed the external BER analysis."
    if best_overall is not None and best_overall.get("analysis_ok"):
        det = best_overall.get("analysis_detection") or {}
        conclusion = (
            "The focused runtime/RTL sweep reproduced external demodulation and ranked the best point by offline BER. "
            f"Best external result: total errors={int(det.get('bit_errors_total') or 0)}, "
            f"payload errors={int(det.get('bit_errors_payload') or 0)}."
        )
    return {
        "best_stage1": best_stage1,
        "best_stage2": best_stage2,
        "best_overall": best_overall,
        "best_final_evidence": best_final,
        "stage1_point_count": len(stage1_rows),
        "stage2_point_count": len(stage2_rows),
        "conclusion": conclusion,
    }


def rerun_best_point_for_evidence(
    *,
    cfg: SweepConfig,
    best_row: dict[str, Any],
    evidence_tag: str,
) -> dict[str, Any]:
    wav_out = ROOT / "tmp" / f"lab1122_runtime_pl_rtl_monitor_{evidence_tag}.wav"
    manifest_out = DATASET_DIR / f"manifest_{evidence_tag}.yaml"
    capture_report_out = DOC_ASSET_DIR / f"lab1122_runtime_pl_rtl_monitor_{evidence_tag}.json"
    runtime_json_out = DOC_ASSET_DIR / f"lab1122_runtime_bridge_txrx_self_timed_{evidence_tag}.json"

    capture_command = [
        sys.executable,
        str(BLOCK11_PYTHON_DIR / "lab_11_22_capture_runtime_pl_rtl_monitor_wav.py"),
        "--ssh-host",
        cfg.ssh_host,
        "--ssh-user",
        cfg.ssh_user,
        "--ssh-password",
        cfg.ssh_password,
        "--ssh-port",
        str(cfg.ssh_port),
        "--ssh-timeout-s",
        str(cfg.ssh_timeout_s),
        "--iio-uri",
        cfg.iio_uri,
        "--bit-bin-path",
        cfg.bit_bin_path,
        "--remote-firmware-name",
        cfg.remote_firmware_name,
        "--center-frequency-hz",
        str(cfg.center_frequency_hz),
        "--sample-rate-hz",
        str(cfg.sample_rate_hz),
        "--rf-bandwidth-hz",
        str(cfg.rf_bandwidth_hz),
        "--start-offset",
        str(best_row["start_offset"]),
        "--rx-gain-db",
        str(best_row["rx_gain_db"]),
        "--tx-attenuation-db",
        str(best_row["tx_attenuation_db"]),
        "--rtl-tuner-gain-db10",
        str(best_row["rtl_tuner_gain_db10"]),
        "--runtime-repeat-count",
        str(cfg.runtime_repeat_count),
        "--runtime-repeat-gap-ms",
        str(cfg.runtime_repeat_gap_ms),
        "--run-tag",
        evidence_tag,
        "--wav-out",
        str(wav_out),
        "--manifest-out",
        str(manifest_out),
        "--capture-report-out",
        str(capture_report_out),
        "--runtime-json-out",
        str(runtime_json_out),
        "--reboot-after",
    ]
    capture_completed = run_subprocess(capture_command, cwd=ROOT)
    result: dict[str, Any] = {
        "capture_returncode": int(capture_completed.returncode),
        "capture_stdout_tail": capture_completed.stdout.splitlines()[-20:],
        "capture_stderr_tail": capture_completed.stderr.splitlines()[-20:],
        "manifest_path": repo_relative_or_str(manifest_out),
        "runtime_json_path": repo_relative_or_str(runtime_json_out),
        "capture_report_path": repo_relative_or_str(capture_report_out),
        "wav_path": str(wav_out),
    }
    if capture_completed.returncode != 0:
        return result

    analysis_command = [
        sys.executable,
        str(BLOCK11_PYTHON_DIR / "lab_11_20_read_rtl_wav_ota_bpsk_ber.py"),
        "--manifest",
        str(manifest_out),
        "--out-dir",
        str(DOC_ASSET_DIR),
        "--run-tag",
        evidence_tag,
    ]
    analysis_completed = run_subprocess(analysis_command, cwd=ROOT)
    result["analysis_returncode"] = int(analysis_completed.returncode)
    result["analysis_stdout_tail"] = analysis_completed.stdout.splitlines()[-20:]
    result["analysis_stderr_tail"] = analysis_completed.stderr.splitlines()[-20:]
    if analysis_completed.returncode != 0:
        return result

    dataset_id = f"lab11_22_runtime_pl_rtl_monitor_{evidence_tag}"
    metrics_name = f"lab1120_{dataset_id}_{evidence_tag}_metrics.json"
    metrics_path = DOC_ASSET_DIR / metrics_name
    if metrics_path.exists():
        result["analysis_metrics_path"] = repo_relative_or_str(metrics_path)
        result["analysis_metrics"] = load_json(metrics_path)
    return result


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    run_tag = args.run_tag or default_run_tag()
    json_out = (args.json_out or build_default_json_out(run_tag)).resolve()
    json_out.parent.mkdir(parents=True, exist_ok=True)

    bit_bin_path = args.bit_bin_path.resolve()
    if not bit_bin_path.exists():
        raise SystemExit(f"Missing runtime payload: {bit_bin_path}")

    cfg = SweepConfig(
        ssh_host=args.ssh_host,
        ssh_user=args.ssh_user,
        ssh_port=args.ssh_port,
        ssh_timeout_s=args.ssh_timeout_s,
        ssh_password=args.ssh_password,
        iio_uri=args.iio_uri,
        bit_bin_path=str(bit_bin_path),
        remote_firmware_name=args.remote_firmware_name,
        center_frequency_hz=args.center_frequency_hz,
        sample_rate_hz=args.sample_rate_hz,
        rf_bandwidth_hz=args.rf_bandwidth_hz,
        start_offsets=list(args.start_offsets),
        rx_gains_db=list(args.rx_gains_db),
        tx_attenuations_db=list(args.tx_attenuations_db),
        stage1_rtl_tuner_gain_db10=args.stage1_rtl_tuner_gain_db10,
        stage2_tuner_gains_db10=list(args.stage2_tuner_gains_db10),
        runtime_repeat_count=args.runtime_repeat_count,
        runtime_repeat_gap_ms=args.runtime_repeat_gap_ms,
        reboot_timeout_s=args.reboot_timeout_s,
        keep_tmp=bool(args.keep_tmp),
        final_evidence=bool(args.final_evidence),
    )

    stage1_points = list(itertools.product(cfg.start_offsets, cfg.rx_gains_db, cfg.tx_attenuations_db))
    stage1_rows: list[dict[str, Any]] = []
    stage2_rows: list[dict[str, Any]] = []
    best_final: dict[str, Any] | None = None
    payload: dict[str, Any] = {
        "timestamp_utc": iso_now(),
        "run_tag": run_tag,
        "config": asdict(cfg),
        "stage1_points": [
            {
                "start_offset": start_offset,
                "rx_gain_db": rx_gain_db,
                "tx_attenuation_db": tx_attenuation_db,
                "rtl_tuner_gain_db10": cfg.stage1_rtl_tuner_gain_db10,
            }
            for start_offset, rx_gain_db, tx_attenuation_db in stage1_points
        ],
        "stage1_results": stage1_rows,
        "stage2_results": stage2_rows,
        "summary": None,
        "final_evidence": None,
        "reboot_after_sweep": None,
    }

    try:
        total_stage1 = len(stage1_points)
        for index, (start_offset, rx_gain_db, tx_attenuation_db) in enumerate(stage1_points, start=1):
            label = point_label("stage1", index, total_stage1)
            row = run_capture_and_analysis(
                cfg=cfg,
                run_tag=run_tag,
                label=label,
                start_offset=start_offset,
                rx_gain_db=rx_gain_db,
                tx_attenuation_db=tx_attenuation_db,
                rtl_tuner_gain_db10=cfg.stage1_rtl_tuner_gain_db10,
                reboot_after=False,
            )
            stage1_rows.append(row)
            payload["summary"] = build_summary(stage1_rows=stage1_rows, stage2_rows=stage2_rows, best_final=best_final)
            json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        best_stage1 = choose_best(stage1_rows)
        if best_stage1 is not None:
            total_stage2 = len(cfg.stage2_tuner_gains_db10)
            for index, tuner_gain_db10 in enumerate(cfg.stage2_tuner_gains_db10, start=1):
                label = point_label("stage2", index, total_stage2)
                row = run_capture_and_analysis(
                    cfg=cfg,
                    run_tag=run_tag,
                    label=label,
                    start_offset=int(best_stage1["start_offset"]),
                    rx_gain_db=float(best_stage1["rx_gain_db"]),
                    tx_attenuation_db=float(best_stage1["tx_attenuation_db"]),
                    rtl_tuner_gain_db10=tuner_gain_db10,
                    reboot_after=False,
                )
                stage2_rows.append(row)
                payload["summary"] = build_summary(
                    stage1_rows=stage1_rows,
                    stage2_rows=stage2_rows,
                    best_final=best_final,
                )
                json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        best_overall = choose_best([*stage1_rows, *stage2_rows])
        if cfg.final_evidence and best_overall is not None:
            evidence_tag = f"{run_tag}_best"
            best_final = rerun_best_point_for_evidence(
                cfg=cfg,
                best_row=best_overall,
                evidence_tag=evidence_tag,
            )
            payload["final_evidence"] = best_final
    finally:
        try:
            payload["reboot_after_sweep"] = maybe_reboot_to_stock(cfg)
        except Exception as exc:  # pragma: no cover - hardware dependent
            payload["reboot_after_sweep"] = {
                "ok": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }

    payload["summary"] = build_summary(stage1_rows=stage1_rows, stage2_rows=stage2_rows, best_final=best_final)
    payload["final_evidence"] = best_final
    json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    if not cfg.keep_tmp:
        shutil.rmtree(TMP_SWEEP_ROOT / run_tag, ignore_errors=True)
    print(f"Saved {repo_relative_or_str(json_out)}")
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
