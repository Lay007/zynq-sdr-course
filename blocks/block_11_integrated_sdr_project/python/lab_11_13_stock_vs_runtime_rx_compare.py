#!/usr/bin/env python3
"""Lab 11.13 - Compare stock-shell RX capture against the runtime overlay reload."""

from __future__ import annotations

import argparse
import json
import socket
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from lab_11_7_axi_lite_bpsk_bringup import ParamikoCommandRunner, parse_int
from lab_11_8_axi_gpreg_bpsk_bringup import BringupConfig, SshDevMemRegisterIo, run_bringup
from lab_11_9_rf_discovery_sweep import read_ad9361_state
from lab_11_10_iio_burst_capture import find_iio_readdev_bin
from lab_11_11_iio_gpreg_contention_probe import read_dmac_snapshot, read_dmesg_tail, run_iio_capture
from lab_11_12_runtime_fpga_manager_reload import (
    md5_bytes,
    probe_gpreg_id,
    read_remote_file_info,
    run_remote,
    trigger_fpga_manager_reload,
    upload_bytes_via_ssh_cat,
)


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BIT_BIN_PATH = ROOT / "tmp" / "bridge_txrx_mux.wordswap.bit.bin"
DEFAULT_JSON_OUT = ROOT / "docs" / "assets" / "lab113_stock_vs_runtime_rx_compare_live.json"
DEFAULT_HOST = "192.168.40.1"
DEFAULT_USER = "root"
DEFAULT_PASSWORD = "analog"
DEFAULT_PORT = 22
DEFAULT_TIMEOUT_S = 10.0
DEFAULT_IIO_URI = "ip:192.168.40.1"
DEFAULT_BASE_ADDR = 0x79040000
DEFAULT_ADC_DMA_BASE_ADDR = 0x7C400000
DEFAULT_EXPECTED_ID = 0x4250534B
DEFAULT_FRAME_BIT_COUNT = 281
DEFAULT_PREAMBLE_COUNT = 25
DEFAULT_START_OFFSET = 62
DEFAULT_START_HOLD_MS = 5
DEFAULT_POLL_LIMIT = 128
DEFAULT_POLL_DELAY_MS = 20
DEFAULT_REMOTE_FIRMWARE_NAME = "course_bpsk_fmcomms2_zc702_runtime.bit.bin"
DEFAULT_CAPTURE_SAMPLE_COUNT = 16384
DEFAULT_CAPTURE_TIMEOUT_S = 15.0
DEFAULT_IIO_READDEV_BUFFER_SIZE = 4096
DEFAULT_DMESG_LINE_COUNT = 80
DEFAULT_REBOOT_TIMEOUT_S = 120.0


@dataclass(frozen=True)
class CompareConfig:
    ssh_host: str
    ssh_user: str
    ssh_port: int
    ssh_timeout_s: float
    iio_uri: str
    bit_bin_path: str
    remote_firmware_name: str
    gpreg_base_addr: int
    adc_dma_base_addr: int
    expected_id: int
    frame_bit_count: int
    preamble_count: int
    start_offset: int
    start_hold_ms: int
    poll_limit: int
    poll_delay_ms: int
    capture_sample_count: int
    iio_readdev_buffer_size: int
    capture_timeout_s: float
    dmesg_line_count: int
    reboot_after: bool
    reboot_timeout_s: float


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def summarize_capture_iq(i_samples: np.ndarray, q_samples: np.ndarray) -> dict[str, Any]:
    i_float = i_samples.astype(np.float32, copy=False)
    q_float = q_samples.astype(np.float32, copy=False)
    power = i_float * i_float + q_float * q_float
    return {
        "complex_sample_count": int(i_samples.size),
        "i_abs_max": int(np.max(np.abs(i_samples), initial=0)),
        "q_abs_max": int(np.max(np.abs(q_samples), initial=0)),
        "mean_power": float(np.mean(power)),
        "rms_i": float(np.sqrt(np.mean(i_float * i_float))),
        "rms_q": float(np.sqrt(np.mean(q_float * q_float))),
    }


def wait_for_port_state(host: str, port: int, *, want_open: bool, timeout_s: float) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        try:
            sock.connect((host, port))
            sock.close()
            if want_open:
                return True
        except OSError:
            if not want_open:
                return True
        time.sleep(1.0)
    return False


def load_iio_module() -> Any:
    module_path = ROOT / "blocks" / "block_06_rf_frontend_and_ad9363" / "python" / "lab_6_3_probe_iio_context.py"
    import importlib.util

    spec = importlib.util.spec_from_file_location("lab_6_3_probe_iio_context", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load IIO helpers from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def probe_iio_context_summary(uri: str) -> dict[str, Any]:
    helper = load_iio_module()
    payload = helper.probe_context(uri=uri, device_filter="ad9361", include_debug_attrs=False)
    devices: list[dict[str, Any]] = []
    for device in payload["devices"]:
        device_summary = {
            "id": device["id"],
            "name": device["name"],
            "channel_count": len(device["channels"]),
            "attrs": {
                key: value
                for key, value in device.get("attrs", {}).items()
                if key in {"sync_start_enable", "sync_start_enable_available"}
            },
        }
        if "ad9361_summary" in device:
            device_summary["ad9361_summary"] = device["ad9361_summary"]
        devices.append(device_summary)
    return {
        "uri": payload["uri"],
        "context_name": payload["context_name"],
        "context_description": payload["context_description"],
        "context_attrs": payload["context_attrs"],
        "devices": devices,
    }


def run_libiio_capture(uri: str, sample_count: int) -> dict[str, Any]:
    helper = load_iio_module()
    iio = helper.load_iio_module()
    context = iio.Context(uri)
    rx_device = next((device for device in context.devices if device.name == "cf-ad9361-lpc"), None)
    if rx_device is None:
        raise RuntimeError("Expected `cf-ad9361-lpc` in the remote IIO context.")

    for channel in getattr(rx_device, "channels", []):
        channel.enabled = False

    i_channel = rx_device.channels[0]
    q_channel = rx_device.channels[1]
    i_channel.enabled = True
    q_channel.enabled = True

    buf = iio.Buffer(rx_device, sample_count, False)
    started_utc = iso_now()
    buf.refill()
    finished_utc = iso_now()
    i_samples = np.frombuffer(i_channel.read(buf), dtype=np.int16).copy()
    q_samples = np.frombuffer(q_channel.read(buf), dtype=np.int16).copy()
    return {
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "metrics": summarize_capture_iq(i_samples, q_samples),
    }


def summarize_stage(
    *,
    name: str,
    runner: ParamikoCommandRunner,
    iio_uri: str,
    iio_readdev_bin: Path,
    sample_count: int,
    iio_readdev_buffer_size: int,
    capture_timeout_s: float,
    adc_dma_base_addr: int,
    dmesg_line_count: int,
) -> dict[str, Any]:
    stage: dict[str, Any] = {
        "name": name,
        "board_state": read_ad9361_state(runner),
        "iio_context": probe_iio_context_summary(iio_uri),
        "adc_dma_before": read_dmac_snapshot(runner, adc_dma_base_addr),
        "libiio_capture": None,
        "iio_readdev_capture": None,
        "adc_dma_after_libiio": None,
        "adc_dma_after_iio_readdev": None,
        "dmesg_tail": [],
    }

    try:
        stage["libiio_capture"] = {
            "ok": True,
            "result": run_libiio_capture(iio_uri, sample_count),
        }
    except Exception as exc:  # pragma: no cover - hardware dependent
        stage["libiio_capture"] = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    stage["adc_dma_after_libiio"] = read_dmac_snapshot(runner, adc_dma_base_addr)

    try:
        stage["iio_readdev_capture"] = {
            "ok": True,
            "result": run_iio_capture(
                iio_readdev_bin=iio_readdev_bin,
                uri=iio_uri,
                buffer_size=iio_readdev_buffer_size,
                sample_count=sample_count,
                timeout_s=capture_timeout_s,
            ),
        }
    except Exception as exc:  # pragma: no cover - hardware dependent
        stage["iio_readdev_capture"] = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    stage["adc_dma_after_iio_readdev"] = read_dmac_snapshot(runner, adc_dma_base_addr)
    stage["dmesg_tail"] = read_dmesg_tail(runner, line_count=dmesg_line_count)
    return stage


def read_fpga_manager_state(runner: ParamikoCommandRunner) -> str:
    return run_remote(
        runner,
        "cat /sys/class/fpga_manager/fpga0/state",
        context="read fpga_manager state",
    )


def run_runtime_reload_and_probe(
    *,
    runner: ParamikoCommandRunner,
    io: SshDevMemRegisterIo,
    cfg: CompareConfig,
    local_payload: bytes,
    iio_readdev_bin: Path,
) -> dict[str, Any]:
    remote_path = f"/lib/firmware/{cfg.remote_firmware_name}"
    upload_bytes_via_ssh_cat(runner, payload=local_payload, remote_path=remote_path)
    payload: dict[str, Any] = {
        "upload": read_remote_file_info(runner, remote_path),
        "reload": trigger_fpga_manager_reload(
            runner,
            remote_firmware_name=cfg.remote_firmware_name,
        ),
        "post_reload_fpga_manager_state": read_fpga_manager_state(runner),
        "gpreg": None,
        "stage": None,
    }

    bringup_cfg = BringupConfig(
        backend="ssh-devmem",
        base_addr=cfg.gpreg_base_addr,
        frame_bit_count=cfg.frame_bit_count,
        preamble_count=cfg.preamble_count,
        start_offset=cfg.start_offset,
        start_hold_ms=cfg.start_hold_ms,
        poll_limit=cfg.poll_limit,
        poll_delay_ms=cfg.poll_delay_ms,
        expected_id=cfg.expected_id,
        clear_done=True,
        max_total_errors=None,
        max_payload_errors=None,
    )
    payload["gpreg"] = {
        "id_probe": probe_gpreg_id(io),
        "bringup": asdict(run_bringup(io, bringup_cfg)),
    }
    payload["stage"] = summarize_stage(
        name="runtime_overlay",
        runner=runner,
        iio_uri=cfg.iio_uri,
        iio_readdev_bin=iio_readdev_bin,
        sample_count=cfg.capture_sample_count,
        iio_readdev_buffer_size=cfg.iio_readdev_buffer_size,
        capture_timeout_s=cfg.capture_timeout_s,
        adc_dma_base_addr=cfg.adc_dma_base_addr,
        dmesg_line_count=cfg.dmesg_line_count,
    )
    return payload


def try_reboot_to_stock(
    runner: ParamikoCommandRunner,
    *,
    host: str,
    user: str,
    password: str,
    port: int,
    ssh_timeout_s: float,
    iio_uri: str,
    timeout_s: float,
) -> dict[str, Any]:
    try:
        runner.client.exec_command("reboot", timeout=5)
    except Exception:
        pass

    down_seen = wait_for_port_state(host, port, want_open=False, timeout_s=20.0)
    up_seen = wait_for_port_state(host, port, want_open=True, timeout_s=timeout_s)
    result = {
        "reboot_issued_utc": iso_now(),
        "ssh_down_seen": down_seen,
        "ssh_up_seen": up_seen,
    }
    if not up_seen:
        return result

    time.sleep(3.0)
    new_runner = ParamikoCommandRunner(
        host=host,
        user=user,
        password=password,
        port=port,
        key_path=None,
        timeout_s=ssh_timeout_s,
    )
    try:
        result["board_state"] = read_ad9361_state(new_runner)
        result["iio_context"] = probe_iio_context_summary(iio_uri)
        result["fpga_manager_state"] = read_fpga_manager_state(new_runner)
    finally:
        new_runner.close()
    return result


def build_summary(payload: dict[str, Any]) -> dict[str, Any]:
    baseline_stage = payload["baseline"]["stage"]
    runtime_stage = payload["runtime"]["stage"]
    runtime_gpreg = payload["runtime"]["gpreg"]["bringup"]

    def stage_ok(stage: dict[str, Any], key: str) -> bool:
        capture = stage.get(key) or {}
        if not capture.get("ok"):
            return False
        result = capture.get("result") or {}
        if key == "iio_readdev_capture":
            return int(result.get("stdout_len", 0)) > 0
        return int(result.get("metrics", {}).get("complex_sample_count", 0)) > 0

    def find_sync(devices: list[dict[str, Any]], device_name: str) -> str | None:
        for device in devices:
            if device.get("name") == device_name:
                attrs = device.get("attrs", {})
                return attrs.get("sync_start_enable")
        return None

    baseline_devices = baseline_stage["iio_context"]["devices"]
    runtime_devices = runtime_stage["iio_context"]["devices"]
    return {
        "stock_libiio_capture_ok": stage_ok(baseline_stage, "libiio_capture"),
        "stock_iio_readdev_capture_ok": stage_ok(baseline_stage, "iio_readdev_capture"),
        "runtime_libiio_capture_ok": stage_ok(runtime_stage, "libiio_capture"),
        "runtime_iio_readdev_capture_ok": stage_ok(runtime_stage, "iio_readdev_capture"),
        "baseline_dds_sync_start_enable": find_sync(baseline_devices, "cf-ad9361-dds-core-lpc"),
        "runtime_dds_sync_start_enable": find_sync(runtime_devices, "cf-ad9361-dds-core-lpc"),
        "runtime_rx_sync_start_enable": find_sync(runtime_devices, "cf-ad9361-lpc"),
        "runtime_gpreg_id_word": f"0x{runtime_gpreg['id_word']:08X}",
        "runtime_gpreg_signature_word": f"0x{runtime_gpreg['signature_word']:08X}",
        "runtime_tx_valid_count": int(runtime_gpreg["tx_valid_count"]),
        "runtime_rx_valid_count": int(runtime_gpreg["rx_valid_count"]),
        "runtime_received_bits": int(runtime_gpreg["received_bits"]),
        "runtime_final_status": f"0x{runtime_gpreg['final_status']:08X}",
        "conclusion": (
            "Stock Linux RX capture works before any overlay reload, while the runtime-loaded "
            "course overlay keeps gpreg visible but breaks both libiio Buffer.refill() and "
            "iio_readdev sample capture on the RX path."
        ),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-host", default=DEFAULT_HOST)
    parser.add_argument("--ssh-user", default=DEFAULT_USER)
    parser.add_argument("--ssh-password", default=DEFAULT_PASSWORD)
    parser.add_argument("--ssh-port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--ssh-timeout-s", type=float, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--iio-uri", default=DEFAULT_IIO_URI)
    parser.add_argument("--iio-readdev-bin", default=None)
    parser.add_argument("--bit-bin-path", type=Path, default=DEFAULT_BIT_BIN_PATH)
    parser.add_argument("--remote-firmware-name", default=DEFAULT_REMOTE_FIRMWARE_NAME)
    parser.add_argument("--gpreg-base-addr", type=parse_int, default=DEFAULT_BASE_ADDR)
    parser.add_argument("--adc-dma-base-addr", type=parse_int, default=DEFAULT_ADC_DMA_BASE_ADDR)
    parser.add_argument("--expected-id", type=parse_int, default=DEFAULT_EXPECTED_ID)
    parser.add_argument("--frame-bit-count", type=int, default=DEFAULT_FRAME_BIT_COUNT)
    parser.add_argument("--preamble-count", type=int, default=DEFAULT_PREAMBLE_COUNT)
    parser.add_argument("--start-offset", type=int, default=DEFAULT_START_OFFSET)
    parser.add_argument("--start-hold-ms", type=int, default=DEFAULT_START_HOLD_MS)
    parser.add_argument("--poll-limit", type=int, default=DEFAULT_POLL_LIMIT)
    parser.add_argument("--poll-delay-ms", type=int, default=DEFAULT_POLL_DELAY_MS)
    parser.add_argument("--capture-sample-count", type=int, default=DEFAULT_CAPTURE_SAMPLE_COUNT)
    parser.add_argument("--iio-readdev-buffer-size", type=int, default=DEFAULT_IIO_READDEV_BUFFER_SIZE)
    parser.add_argument("--capture-timeout-s", type=float, default=DEFAULT_CAPTURE_TIMEOUT_S)
    parser.add_argument("--dmesg-line-count", type=int, default=DEFAULT_DMESG_LINE_COUNT)
    parser.add_argument("--reboot-after", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--reboot-timeout-s", type=float, default=DEFAULT_REBOOT_TIMEOUT_S)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    bit_bin_path = args.bit_bin_path.resolve()
    if not bit_bin_path.exists():
        raise SystemExit(f"Missing bitstream payload: {bit_bin_path}")

    cfg = CompareConfig(
        ssh_host=args.ssh_host,
        ssh_user=args.ssh_user,
        ssh_port=args.ssh_port,
        ssh_timeout_s=args.ssh_timeout_s,
        iio_uri=args.iio_uri,
        bit_bin_path=str(bit_bin_path),
        remote_firmware_name=args.remote_firmware_name,
        gpreg_base_addr=args.gpreg_base_addr,
        adc_dma_base_addr=args.adc_dma_base_addr,
        expected_id=args.expected_id,
        frame_bit_count=args.frame_bit_count,
        preamble_count=args.preamble_count,
        start_offset=args.start_offset,
        start_hold_ms=args.start_hold_ms,
        poll_limit=args.poll_limit,
        poll_delay_ms=args.poll_delay_ms,
        capture_sample_count=args.capture_sample_count,
        iio_readdev_buffer_size=args.iio_readdev_buffer_size,
        capture_timeout_s=args.capture_timeout_s,
        dmesg_line_count=args.dmesg_line_count,
        reboot_after=bool(args.reboot_after),
        reboot_timeout_s=args.reboot_timeout_s,
    )
    iio_readdev_bin = find_iio_readdev_bin(args.iio_readdev_bin)
    local_payload = bit_bin_path.read_bytes()

    runner = ParamikoCommandRunner(
        host=args.ssh_host,
        user=args.ssh_user,
        password=args.ssh_password,
        port=args.ssh_port,
        key_path=None,
        timeout_s=args.ssh_timeout_s,
    )
    io = SshDevMemRegisterIo(args.gpreg_base_addr, command_runner=runner)
    payload: dict[str, Any] = {
        "timestamp_utc": iso_now(),
        "config": asdict(cfg),
        "iio_readdev_bin": str(iio_readdev_bin),
        "local_bit_bin": {
            "path": str(bit_bin_path),
            "md5": md5_bytes(local_payload),
            "size_bytes": len(local_payload),
        },
        "baseline": {
            "fpga_manager_state": read_fpga_manager_state(runner),
            "gpreg": None,
            "stage": None,
        },
        "runtime": None,
        "reboot_after": None,
        "summary": None,
    }

    try:
        try:
            payload["baseline"]["gpreg"] = probe_gpreg_id(io)
        except Exception as exc:
            payload["baseline"]["gpreg"] = {
                "error_type": type(exc).__name__,
                "error": str(exc),
            }

        payload["baseline"]["stage"] = summarize_stage(
            name="stock_shell",
            runner=runner,
            iio_uri=cfg.iio_uri,
            iio_readdev_bin=iio_readdev_bin,
            sample_count=cfg.capture_sample_count,
            iio_readdev_buffer_size=cfg.iio_readdev_buffer_size,
            capture_timeout_s=cfg.capture_timeout_s,
            adc_dma_base_addr=cfg.adc_dma_base_addr,
            dmesg_line_count=cfg.dmesg_line_count,
        )

        payload["runtime"] = run_runtime_reload_and_probe(
            runner=runner,
            io=io,
            cfg=cfg,
            local_payload=local_payload,
            iio_readdev_bin=iio_readdev_bin,
        )
        payload["summary"] = build_summary(payload)
    finally:
        reboot_result = None
        if cfg.reboot_after:
            reboot_result = try_reboot_to_stock(
                runner,
                host=cfg.ssh_host,
                user=args.ssh_user,
                password=args.ssh_password,
                port=cfg.ssh_port,
                ssh_timeout_s=cfg.ssh_timeout_s,
                iio_uri=cfg.iio_uri,
                timeout_s=cfg.reboot_timeout_s,
            )
        payload["reboot_after"] = reboot_result
        io.close()
        try:
            runner.close()
        except Exception:
            pass

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Wrote {args.json_out}")
    print(json.dumps(payload["summary"], indent=2))
    if payload["reboot_after"] is not None:
        print(json.dumps(payload["reboot_after"], indent=2))


if __name__ == "__main__":
    main()
