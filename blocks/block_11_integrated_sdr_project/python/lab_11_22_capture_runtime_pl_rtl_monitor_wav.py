#!/usr/bin/env python3
"""Lab 11.22 - Capture RTL-SDR monitor WAV during runtime/PL BPSK bring-up."""

from __future__ import annotations

import argparse
import ctypes
import json
import sys
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import yaml


ROOT = Path(__file__).resolve().parents[3]
BLOCK11_PYTHON_DIR = ROOT / "blocks" / "block_11_integrated_sdr_project" / "python"
if str(BLOCK11_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(BLOCK11_PYTHON_DIR))

from lab_11_12_runtime_fpga_manager_reload import (  # noqa: E402
    md5_bytes,
    probe_gpreg_id,
    read_remote_file_info,
    trigger_fpga_manager_reload,
    upload_bytes_via_ssh_cat,
)
from lab_11_13_stock_vs_runtime_rx_compare import probe_iio_context_summary, try_reboot_to_stock  # noqa: E402
from lab_11_14_stock_shell_bpsk_ota import (  # noqa: E402
    configure_ad9361_bpsk,
    enforce_safe_tx_restore_over_ssh,
    load_iio_module,
    repo_relative_or_str,
    restore_ad9361_state,
    snapshot_ad9361_state,
)
from lab_11_15_runtime_bridge_rx_host_tx_probe import (  # noqa: E402
    DEFAULT_BASE_ADDR,
    DEFAULT_BIT_BIN_PATH,
    DEFAULT_CENTER_FREQUENCY_HZ,
    DEFAULT_EXPECTED_ID,
    DEFAULT_FRAME_BIT_COUNT,
    DEFAULT_HOST,
    DEFAULT_IIO_URI,
    DEFAULT_PASSWORD,
    DEFAULT_POLL_DELAY_MS,
    DEFAULT_POLL_LIMIT,
    DEFAULT_PORT,
    DEFAULT_PREAMBLE_COUNT,
    DEFAULT_RF_BANDWIDTH_HZ,
    DEFAULT_REMOTE_FIRMWARE_NAME,
    DEFAULT_SETTLE_MS,
    DEFAULT_START_HOLD_MS,
    DEFAULT_TIMEOUT_S,
    DEFAULT_TX_REFERENCE_PATH,
    DEFAULT_USER,
    RuntimeBridgeRxHostTxProbeConfig,
    attempt_runtime_bringup,
    load_reference_config,
    make_waveform_config,
    safe_probe,
)
from lab_11_21_capture_rtl_sdr_monitor_wav import (  # noqa: E402
    DEFAULT_RTL_CAPTURE_DURATION_S,
    DEFAULT_RTL_DLL_PATH,
    DEFAULT_RTL_SAMPLE_RATE_HZ,
    DEFAULT_RTL_SYNC_BLOCK_BYTES,
    DEFAULT_RTL_TUNER_GAIN_DB10,
    load_rtlsdr_library,
    write_wav_iq,
)
from lab_11_7_axi_lite_bpsk_bringup import ParamikoCommandRunner, parse_int  # noqa: E402
from lab_11_8_axi_gpreg_bpsk_bringup import (  # noqa: E402
    DEFAULT_RX_DECISION_MODE,
    SshDevMemRegisterIo,
    parse_rx_decision_mode,
    rx_decision_mode_name,
)
from runtime_rx_common import force_rx_common_ctrl_request  # noqa: E402


DOC_ASSET_DIR = ROOT / "docs" / "assets"
TMP_DIR = ROOT / "tmp"
DATASET_DIR = ROOT / "datasets" / "lab11_22_runtime_pl_rtl_monitor"
REFERENCE_CONFIG_JSON = (
    ROOT / "blocks" / "block_11_integrated_sdr_project" / "assets" / "end_to_end_bpsk_reference" / "config.json"
)
DEFAULT_RUN_TAG_STEM = "lab1122_runtime_pl_rtl_monitor"
DEFAULT_START_OFFSET = 59
DEFAULT_RUNTIME_RX_GAIN_DB = 5.0
DEFAULT_RUNTIME_TX_ATTENUATION_DB = -50.0
DEFAULT_RUNTIME_REBOOT_TIMEOUT_S = 120.0
DEFAULT_CAPTURE_PREROLL_S = 0.25
DEFAULT_CAPTURE_POSTROLL_S = 0.50
DEFAULT_RUNTIME_REPEAT_COUNT = 3
DEFAULT_RUNTIME_REPEAT_GAP_MS = 100


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_run_tag() -> str:
    return f"live_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-host", default=DEFAULT_HOST)
    parser.add_argument("--ssh-user", default=DEFAULT_USER)
    parser.add_argument("--ssh-password", default=DEFAULT_PASSWORD)
    parser.add_argument("--ssh-port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--ssh-timeout-s", type=float, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--iio-uri", default=DEFAULT_IIO_URI)
    parser.add_argument("--bit-bin-path", type=Path, default=DEFAULT_BIT_BIN_PATH)
    parser.add_argument("--remote-firmware-name", default=DEFAULT_REMOTE_FIRMWARE_NAME)
    parser.add_argument("--gpreg-base-addr", type=parse_int, default=DEFAULT_BASE_ADDR)
    parser.add_argument("--expected-id", type=parse_int, default=DEFAULT_EXPECTED_ID)
    parser.add_argument("--frame-bit-count", type=int, default=DEFAULT_FRAME_BIT_COUNT)
    parser.add_argument("--preamble-count", type=int, default=DEFAULT_PREAMBLE_COUNT)
    parser.add_argument("--center-frequency-hz", type=int, default=DEFAULT_CENTER_FREQUENCY_HZ)
    parser.add_argument("--sample-rate-hz", type=int, default=3_840_000)
    parser.add_argument("--rf-bandwidth-hz", type=int, default=DEFAULT_RF_BANDWIDTH_HZ)
    parser.add_argument("--tx-attenuation-db", type=float, default=DEFAULT_RUNTIME_TX_ATTENUATION_DB)
    parser.add_argument("--rx-gain-db", type=float, default=DEFAULT_RUNTIME_RX_GAIN_DB)
    parser.add_argument("--settle-ms", type=int, default=DEFAULT_SETTLE_MS)
    parser.add_argument("--rx-rf-port-select", default="A_BALANCED")
    parser.add_argument("--tx-rf-port-select", default="A")
    parser.add_argument("--start-offset", type=int, default=DEFAULT_START_OFFSET)
    parser.add_argument(
        "--rx-decision-mode",
        type=parse_rx_decision_mode,
        default=parse_rx_decision_mode(DEFAULT_RX_DECISION_MODE),
    )
    parser.add_argument("--start-hold-ms", type=int, default=DEFAULT_START_HOLD_MS)
    parser.add_argument("--poll-limit", type=int, default=DEFAULT_POLL_LIMIT)
    parser.add_argument("--poll-delay-ms", type=int, default=DEFAULT_POLL_DELAY_MS)
    parser.add_argument("--rx-common-ctrl-value", type=parse_int, default=parse_int("0x3"))
    parser.add_argument("--runtime-repeat-count", type=int, default=DEFAULT_RUNTIME_REPEAT_COUNT)
    parser.add_argument("--runtime-repeat-gap-ms", type=int, default=DEFAULT_RUNTIME_REPEAT_GAP_MS)
    parser.add_argument("--rtl-device-index", type=int, default=0)
    parser.add_argument("--rtl-sample-rate-hz", type=int, default=DEFAULT_RTL_SAMPLE_RATE_HZ)
    parser.add_argument("--rtl-max-capture-duration-s", type=float, default=DEFAULT_RTL_CAPTURE_DURATION_S * 8.0)
    parser.add_argument("--rtl-tuner-gain-db10", type=int, default=DEFAULT_RTL_TUNER_GAIN_DB10)
    parser.add_argument("--rtl-auto-gain", action="store_true")
    parser.add_argument("--rtl-sync-block-bytes", type=int, default=DEFAULT_RTL_SYNC_BLOCK_BYTES)
    parser.add_argument("--rtl-dll-path", type=Path, default=DEFAULT_RTL_DLL_PATH)
    parser.add_argument("--capture-preroll-s", type=float, default=DEFAULT_CAPTURE_PREROLL_S)
    parser.add_argument("--capture-postroll-s", type=float, default=DEFAULT_CAPTURE_POSTROLL_S)
    parser.add_argument("--reboot-after", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--reboot-timeout-s", type=float, default=DEFAULT_RUNTIME_REBOOT_TIMEOUT_S)
    parser.add_argument("--run-tag", default=None)
    parser.add_argument("--wav-out", type=Path, default=None)
    parser.add_argument("--manifest-out", type=Path, default=None)
    parser.add_argument("--capture-report-out", type=Path, default=None)
    parser.add_argument("--runtime-json-out", type=Path, default=None)
    return parser.parse_args()


def build_output_paths(args: argparse.Namespace) -> dict[str, Path]:
    run_tag = args.run_tag or default_run_tag()
    wav_out = args.wav_out or (TMP_DIR / f"{DEFAULT_RUN_TAG_STEM}_{run_tag}.wav")
    manifest_out = args.manifest_out or (DATASET_DIR / f"manifest_{run_tag}.yaml")
    capture_report_out = args.capture_report_out or (DOC_ASSET_DIR / f"{DEFAULT_RUN_TAG_STEM}_{run_tag}.json")
    runtime_json_out = args.runtime_json_out or (DOC_ASSET_DIR / f"lab1122_runtime_bridge_txrx_self_timed_{run_tag}.json")
    return {
        "run_tag": Path(run_tag),
        "wav_out": wav_out.resolve(),
        "manifest_out": manifest_out.resolve(),
        "capture_report_out": capture_report_out.resolve(),
        "runtime_json_out": runtime_json_out.resolve(),
    }


def capture_rtlsdr_unsigned_iq(
    *,
    args: argparse.Namespace,
    started_event: threading.Event,
    stop_event: threading.Event,
    result_box: dict[str, Any],
) -> None:
    rtl = load_rtlsdr_library(args.rtl_dll_path.resolve())
    device_count = int(rtl.rtlsdr_get_device_count())
    if device_count <= args.rtl_device_index:
        result_box["error"] = (
            f"RTL-SDR device index {args.rtl_device_index} is not available; device_count={device_count}."
        )
        started_event.set()
        return

    device_name = rtl.rtlsdr_get_device_name(args.rtl_device_index).decode("utf-8", errors="replace")
    rtl_dev = ctypes.c_void_p()
    raw_parts: list[np.ndarray] = []
    bytes_captured = 0
    max_bytes = int(args.rtl_sample_rate_hz * args.rtl_max_capture_duration_s * 2)

    try:
        rc = rtl.rtlsdr_open(ctypes.byref(rtl_dev), args.rtl_device_index)
        if rc != 0:
            raise RuntimeError(f"rtlsdr_open failed with rc={rc}")

        operations = [
            ("set_center_freq", rtl.rtlsdr_set_center_freq(rtl_dev, args.center_frequency_hz)),
            ("set_sample_rate", rtl.rtlsdr_set_sample_rate(rtl_dev, args.rtl_sample_rate_hz)),
            ("set_agc_mode", rtl.rtlsdr_set_agc_mode(rtl_dev, 1 if args.rtl_auto_gain else 0)),
            ("set_tuner_gain_mode", rtl.rtlsdr_set_tuner_gain_mode(rtl_dev, 0 if args.rtl_auto_gain else 1)),
        ]
        if not args.rtl_auto_gain:
            operations.append(("set_tuner_gain", rtl.rtlsdr_set_tuner_gain(rtl_dev, args.rtl_tuner_gain_db10)))
        operations.append(("reset_buffer", rtl.rtlsdr_reset_buffer(rtl_dev)))

        for label, code in operations:
            if code != 0:
                raise RuntimeError(f"{label} failed with rc={code}")

        started_event.set()
        while bytes_captured < max_bytes:
            if stop_event.is_set() and bytes_captured > 0:
                break
            block = min(args.rtl_sync_block_bytes, max_bytes - bytes_captured)
            buf = (ctypes.c_ubyte * block)()
            n_read = ctypes.c_int()
            rc = rtl.rtlsdr_read_sync(rtl_dev, buf, block, ctypes.byref(n_read))
            if rc != 0:
                raise RuntimeError(f"rtlsdr_read_sync failed with rc={rc} after {bytes_captured} bytes")
            if n_read.value <= 0:
                raise RuntimeError("rtlsdr_read_sync returned no bytes")
            raw = np.ctypeslib.as_array(buf)[: n_read.value].copy()
            raw_parts.append(raw)
            bytes_captured += n_read.value
    except Exception as exc:
        result_box["error"] = str(exc)
    finally:
        if rtl_dev.value:
            try:
                rtl.rtlsdr_close(rtl_dev)
            except Exception:
                pass
        if raw_parts:
            raw_u8 = np.concatenate(raw_parts)
            result_box["raw_u8"] = raw_u8
            result_box["bytes_captured"] = int(raw_u8.size)
            result_box["rtl_device_name"] = device_name
        started_event.set()


def build_runtime_probe_config(args: argparse.Namespace, waveform_cfg: Any) -> RuntimeBridgeRxHostTxProbeConfig:
    return RuntimeBridgeRxHostTxProbeConfig(
        ssh_host=args.ssh_host,
        ssh_user=args.ssh_user,
        ssh_port=args.ssh_port,
        ssh_timeout_s=args.ssh_timeout_s,
        iio_uri=args.iio_uri,
        raw_bit_path="",
        bit_bin_path=str(args.bit_bin_path.resolve()),
        tx_reference_path=str(DEFAULT_TX_REFERENCE_PATH),
        remote_firmware_name=args.remote_firmware_name,
        gpreg_base_addr=args.gpreg_base_addr,
        expected_id=args.expected_id,
        frame_bit_count=args.frame_bit_count,
        preamble_count=args.preamble_count,
        start_offset=args.start_offset,
        rx_decision_mode=args.rx_decision_mode,
        start_hold_ms=args.start_hold_ms,
        poll_limit=args.poll_limit,
        poll_delay_ms=args.poll_delay_ms,
        center_frequency_hz=waveform_cfg.center_frequency_hz,
        sample_rate_hz=waveform_cfg.sample_rate_hz,
        symbol_rate_hz=waveform_cfg.symbol_rate_hz,
        samples_per_symbol=waveform_cfg.samples_per_symbol,
        rf_bandwidth_hz=waveform_cfg.rf_bandwidth_hz,
        tx_attenuation_db=waveform_cfg.tx_attenuation_db,
        rx_gain_db=waveform_cfg.rx_gain_db,
        settle_ms=waveform_cfg.settle_ms,
        tx_settle_ms=0,
        rx_rf_port_select=waveform_cfg.rx_rf_port_select,
        tx_rf_port_select=waveform_cfg.tx_rf_port_select,
        rx_common_reinit=True,
        rx_common_ctrl_value=args.rx_common_ctrl_value,
        reboot_after=False,
        reboot_timeout_s=args.reboot_timeout_s,
        dmesg_line_count=80,
    )


def attempt_rank_key(attempt: dict[str, Any]) -> tuple[int, int, int, int]:
    if not attempt.get("ok"):
        return (0, 0, -1_000_000, -1_000_000)
    result = attempt.get("result") or {}
    return (
        1,
        int(result.get("received_bits") or 0),
        -int(result.get("total_errors") or 0),
        -int(result.get("payload_errors") or 0),
    )


def build_attempt_summary(attempts: list[dict[str, Any]], frame_bit_count: int) -> dict[str, Any]:
    if not attempts:
        return {
            "attempt_count": 0,
            "any_ok": False,
            "conclusion": "No runtime bring-up attempts were executed during the RTL-SDR capture window.",
        }

    best_index = max(range(len(attempts)), key=lambda idx: attempt_rank_key(attempts[idx]))
    best_attempt = attempts[best_index]
    if not best_attempt.get("ok"):
        return {
            "attempt_count": len(attempts),
            "any_ok": False,
            "best_attempt_index": best_index,
            "conclusion": "All runtime bring-up attempts failed before a valid GPREG result was reported.",
        }

    result = best_attempt.get("result") or {}
    received_bits = int(result.get("received_bits") or 0)
    total_errors = int(result.get("total_errors") or 0)
    payload_errors = int(result.get("payload_errors") or 0)
    if received_bits == frame_bit_count and total_errors == 0 and payload_errors == 0:
        conclusion = "The runtime/PL BPSK path reached a full zero-error frame during the external monitor capture."
    elif received_bits == frame_bit_count:
        conclusion = "The runtime/PL BPSK path reached a full frame during the external monitor capture."
    else:
        conclusion = "The runtime/PL BPSK path emitted a partial frame during the external monitor capture."
    return {
        "attempt_count": len(attempts),
        "any_ok": True,
        "best_attempt_index": best_index,
        "received_bits": received_bits,
        "total_errors": total_errors,
        "payload_errors": payload_errors,
        "ber_total": result.get("ber_total"),
        "ber_payload": result.get("ber_payload"),
        "timed_out_observed": bool(result.get("timed_out_observed")),
        "conclusion": conclusion,
    }


def write_manifest(
    *,
    manifest_path: Path,
    dataset_id: str,
    wav_path: Path,
    runtime_json_out: Path,
    capture_report_out: Path,
    waveform_cfg: Any,
    args: argparse.Namespace,
) -> None:
    manifest = {
        "dataset_id": dataset_id,
        "title": "RTL-SDR monitor capture for runtime bridge_txrx_mux OTA BPSK",
        "description": (
            "Fresh local RTL-SDR stereo WAV IQ capture recorded after the runtime bridge_txrx_mux "
            "overlay had already been loaded and AD9361 configured, with the capture window centered "
            "on repeated PL-owned start pulses."
        ),
        "storage": "local-workstation",
        "url": None,
        "local_path_hint_windows": str(wav_path),
        "format": "wav",
        "i_first": True,
        "sample_rate_hz": args.rtl_sample_rate_hz,
        "center_frequency_hz": args.center_frequency_hz,
        "analysis_command": (
            "python blocks/block_11_integrated_sdr_project/python/lab_11_20_read_rtl_wav_ota_bpsk_ber.py "
            f"--manifest {repo_relative_or_str(manifest_path)}"
        ),
        "analysis": {
            "reference_config_json": repo_relative_or_str(REFERENCE_CONFIG_JSON),
            "reference_sample_rate_hz": waveform_cfg.sample_rate_hz,
            "runtime_bringup_json": repo_relative_or_str(runtime_json_out),
            "capture_report_json": repo_relative_or_str(capture_report_out),
        },
        "hardware": {
            "transmitter": "Zynq-7020 + AD9361 board, runtime bridge_txrx_mux PL-owned BPSK TX path",
            "monitor_receiver": "RTL-SDR V3 Pro",
            "context_uri": args.iio_uri,
            "tx_attenuation_db": args.tx_attenuation_db,
            "rx_gain_db": args.rx_gain_db,
            "start_offset": args.start_offset,
            "rx_decision_mode": rx_decision_mode_name(args.rx_decision_mode),
            "rtl_tuner_gain_db10": args.rtl_tuner_gain_db10,
            "rtl_auto_gain": bool(args.rtl_auto_gain),
        },
        "signal": {
            "modulation": "BPSK",
            "symbol_rate_hz": waveform_cfg.symbol_rate_hz,
            "samples_per_symbol": waveform_cfg.samples_per_symbol,
            "rolloff": waveform_cfg.rolloff,
            "payload_bit_count": waveform_cfg.payload_bit_count,
            "reference_sample_rate_hz": waveform_cfg.sample_rate_hz,
            "expected_signal_offset_hz": 0.0,
        },
        "notes": [
            "This capture is intended for offline BER validation through the external RTL-SDR monitor path.",
            "The runtime bridge_txrx_mux overlay uses the shared end_to_end_bpsk_reference bit package with seed=20260619 and samples_per_symbol=8.",
            f"The PL start pulse was repeated {max(args.runtime_repeat_count, 1)} times to improve external-monitor observability.",
            "Keep the local WAV outside Git or move it into Git LFS before sharing the raw recording.",
        ],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=False), encoding="utf-8")


def maybe_reboot_to_stock(args: argparse.Namespace) -> dict[str, Any] | None:
    if not args.reboot_after:
        return None
    runner = ParamikoCommandRunner(
        host=args.ssh_host,
        user=args.ssh_user,
        password=args.ssh_password,
        port=args.ssh_port,
        key_path=None,
        timeout_s=args.ssh_timeout_s,
    )
    try:
        return try_reboot_to_stock(
            runner,
            host=args.ssh_host,
            user=args.ssh_user,
            password=args.ssh_password,
            port=args.ssh_port,
            ssh_timeout_s=args.ssh_timeout_s,
            iio_uri=args.iio_uri,
            timeout_s=args.reboot_timeout_s,
        )
    finally:
        try:
            runner.close()
        except Exception:
            pass


def main() -> int:
    args = parse_args()
    outputs = build_output_paths(args)
    dataset_id = f"lab11_22_runtime_pl_rtl_monitor_{outputs['run_tag'].name}"
    bit_bin_path = args.bit_bin_path.resolve()
    if not bit_bin_path.exists():
        raise SystemExit(f"Missing runtime payload: {bit_bin_path}")

    reference_cfg = load_reference_config()
    waveform_cfg = make_waveform_config(
        reference_cfg=reference_cfg,
        center_frequency_hz=args.center_frequency_hz,
        sample_rate_hz=args.sample_rate_hz,
        rf_bandwidth_hz=args.rf_bandwidth_hz,
        tx_attenuation_db=args.tx_attenuation_db,
        rx_gain_db=args.rx_gain_db,
        settle_ms=args.settle_ms,
        rx_rf_port_select=args.rx_rf_port_select,
        tx_rf_port_select=args.tx_rf_port_select,
    )
    probe_cfg = build_runtime_probe_config(args, waveform_cfg)
    bit_payload = bit_bin_path.read_bytes()

    runner = ParamikoCommandRunner(
        host=args.ssh_host,
        user=args.ssh_user,
        password=args.ssh_password,
        port=args.ssh_port,
        key_path=None,
        timeout_s=args.ssh_timeout_s,
    )
    io = SshDevMemRegisterIo(args.gpreg_base_addr, command_runner=runner)
    capture_box: dict[str, Any] = {}
    started_event = threading.Event()
    stop_event = threading.Event()
    capture_thread: threading.Thread | None = None
    iio = None
    context = None
    phy = None
    phy_snapshot: dict[str, str | None] = {}

    payload: dict[str, Any] = {
        "timestamp_utc": iso_now(),
        "run_tag": outputs["run_tag"].name,
        "dataset_id": dataset_id,
        "config": {
            "ssh_host": args.ssh_host,
            "ssh_user": args.ssh_user,
            "ssh_port": args.ssh_port,
            "iio_uri": args.iio_uri,
            "bit_bin_path": str(bit_bin_path),
            "remote_firmware_name": args.remote_firmware_name,
            "gpreg_base_addr": f"0x{args.gpreg_base_addr:08X}",
            "expected_id": f"0x{args.expected_id:08X}",
            "frame_bit_count": args.frame_bit_count,
            "preamble_count": args.preamble_count,
            "start_offset": args.start_offset,
            "rx_decision_mode": rx_decision_mode_name(args.rx_decision_mode),
            "runtime_repeat_count": args.runtime_repeat_count,
            "runtime_repeat_gap_ms": args.runtime_repeat_gap_ms,
            "center_frequency_hz": args.center_frequency_hz,
            "sample_rate_hz": args.sample_rate_hz,
            "rf_bandwidth_hz": args.rf_bandwidth_hz,
            "tx_attenuation_db": args.tx_attenuation_db,
            "rx_gain_db": args.rx_gain_db,
            "rtl_sample_rate_hz": args.rtl_sample_rate_hz,
            "rtl_tuner_gain_db10": args.rtl_tuner_gain_db10,
            "rtl_auto_gain": bool(args.rtl_auto_gain),
        },
        "waveform_config": asdict(waveform_cfg),
        "bitstream": {
            "path": str(bit_bin_path),
            "size_bytes": len(bit_payload),
            "md5": md5_bytes(bit_payload),
        },
        "stock_context_before": None,
        "upload": None,
        "reload": None,
        "gpreg_after_reload": None,
        "post_reload_context": None,
        "rx_common_reinit": None,
        "phy_before": None,
        "phy_after_config": None,
        "runtime_attempts": [],
        "summary": None,
        "rtl_capture": None,
        "capture_wave_path": str(outputs["wav_out"]),
        "manifest_path": repo_relative_or_str(outputs["manifest_out"]),
        "reboot_after": None,
        "cleanup_errors": [],
        "fatal_error": None,
    }

    fatal_error: Exception | None = None
    try:
        payload["stock_context_before"] = safe_probe(
            "probe_iio_context_before",
            lambda: probe_iio_context_summary(args.iio_uri),
        )

        remote_path = f"/lib/firmware/{args.remote_firmware_name}"
        upload_bytes_via_ssh_cat(runner, payload=bit_payload, remote_path=remote_path)
        payload["upload"] = read_remote_file_info(runner, remote_path)
        payload["reload"] = trigger_fpga_manager_reload(
            runner,
            remote_firmware_name=args.remote_firmware_name,
        )
        payload["gpreg_after_reload"] = probe_gpreg_id(io)
        payload["post_reload_context"] = safe_probe(
            "probe_iio_context_after_reload",
            lambda: probe_iio_context_summary(args.iio_uri),
        )
        payload["rx_common_reinit"] = force_rx_common_ctrl_request(
            runner,
            value=args.rx_common_ctrl_value,
        )

        iio = load_iio_module()
        context = iio.Context(args.iio_uri)
        phy = next((device for device in context.devices if device.name == "ad9361-phy"), None)
        if phy is None:
            raise RuntimeError("Expected `ad9361-phy` after runtime reload.")

        phy_snapshot = snapshot_ad9361_state(phy)
        payload["phy_before"] = phy_snapshot
        payload["phy_after_config"] = configure_ad9361_bpsk(phy, waveform_cfg)

        capture_thread = threading.Thread(
            target=capture_rtlsdr_unsigned_iq,
            kwargs={
                "args": args,
                "started_event": started_event,
                "stop_event": stop_event,
                "result_box": capture_box,
            },
            daemon=True,
        )
        capture_thread.start()
        started_event.wait(timeout=10.0)
        if "error" in capture_box:
            raise RuntimeError(capture_box["error"])

        time.sleep(max(args.capture_preroll_s, 0.0))
        attempt_count = max(args.runtime_repeat_count, 1)
        for attempt_index in range(attempt_count):
            payload["runtime_attempts"].append(attempt_runtime_bringup(io, probe_cfg))
            if attempt_index + 1 < attempt_count and args.runtime_repeat_gap_ms > 0:
                time.sleep(args.runtime_repeat_gap_ms / 1000.0)
        time.sleep(max(args.capture_postroll_s, 0.0))
        stop_event.set()
        capture_thread.join(timeout=max(args.rtl_max_capture_duration_s + 2.0, 5.0))

        if "error" in capture_box:
            raise RuntimeError(capture_box["error"])
        raw_u8 = capture_box.get("raw_u8")
        if raw_u8 is None or not len(raw_u8):
            raise RuntimeError("RTL-SDR monitor capture returned no data.")

        write_wav_iq(outputs["wav_out"], raw_u8, args.rtl_sample_rate_hz)
        write_manifest(
            manifest_path=outputs["manifest_out"],
            dataset_id=dataset_id,
            wav_path=outputs["wav_out"],
            runtime_json_out=outputs["runtime_json_out"],
            capture_report_out=outputs["capture_report_out"],
            waveform_cfg=waveform_cfg,
            args=args,
        )

        payload["summary"] = build_attempt_summary(payload["runtime_attempts"], args.frame_bit_count)
        payload["rtl_capture"] = {
            "rtl_device_index": args.rtl_device_index,
            "rtl_device_name": str(capture_box.get("rtl_device_name", "")),
            "rtl_sample_rate_hz": args.rtl_sample_rate_hz,
            "rtl_capture_duration_s": float(raw_u8.size / 2 / args.rtl_sample_rate_hz),
            "rtl_tuner_gain_db10": args.rtl_tuner_gain_db10,
            "bytes_captured": int(raw_u8.size),
            "wav_path": str(outputs["wav_out"]),
            "raw_u8_mean": float(raw_u8.mean()),
            "raw_u8_std": float(raw_u8.std()),
            "raw_u8_min": int(raw_u8.min()),
            "raw_u8_max": int(raw_u8.max()),
        }
    except Exception as exc:
        fatal_error = exc
        payload["fatal_error"] = {
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    finally:
        stop_event.set()
        if capture_thread is not None and capture_thread.is_alive():
            capture_thread.join(timeout=max(args.rtl_max_capture_duration_s + 2.0, 5.0))
        try:
            if phy is not None and phy_snapshot:
                restore_ad9361_state(phy, phy_snapshot)
        except Exception as exc:
            payload["cleanup_errors"].append({"stage": "restore_ad9361_state", "error": str(exc)})
        try:
            if phy_snapshot:
                enforce_safe_tx_restore_over_ssh(phy_snapshot, args)
        except Exception as exc:
            payload["cleanup_errors"].append({"stage": "enforce_safe_tx_restore_over_ssh", "error": str(exc)})

        try:
            payload["reboot_after"] = maybe_reboot_to_stock(args)
        except Exception as exc:
            payload["cleanup_errors"].append({"stage": "try_reboot_to_stock", "error": str(exc)})
        try:
            io.close()
        except Exception as exc:
            payload["cleanup_errors"].append({"stage": "io.close", "error": str(exc)})
        try:
            runner.close()
        except Exception as exc:
            payload["cleanup_errors"].append({"stage": "runner.close", "error": str(exc)})

    outputs["runtime_json_out"].parent.mkdir(parents=True, exist_ok=True)
    outputs["runtime_json_out"].write_text(json.dumps(payload, indent=2), encoding="utf-8")
    outputs["capture_report_out"].parent.mkdir(parents=True, exist_ok=True)
    outputs["capture_report_out"].write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("Lab 11.22 - Capture RTL-SDR monitor WAV during runtime/PL BPSK bring-up")
    print(f"Runtime JSON: {repo_relative_or_str(outputs['runtime_json_out'])}")
    print(f"Capture report: {repo_relative_or_str(outputs['capture_report_out'])}")
    if outputs["wav_out"].exists():
        print(f"WAV IQ: {outputs['wav_out']}")
    if outputs["manifest_out"].exists():
        print(f"Manifest: {repo_relative_or_str(outputs['manifest_out'])}")
    if payload.get("summary") is not None:
        print(f"Summary: {json.dumps(payload['summary'], ensure_ascii=False)}")
    if fatal_error is not None:
        raise SystemExit(f"{type(fatal_error).__name__}: {fatal_error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
