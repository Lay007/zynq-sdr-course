#!/usr/bin/env python3
"""Lab 11.16 - Probe RX host capture before and after runtime RX common re-init."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bench_config import (
    DEFAULT_HOST,
    DEFAULT_IIO_URI,
    DEFAULT_PASSWORD,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT_S,
    DEFAULT_USER,
)
from lab_11_7_axi_lite_bpsk_bringup import ParamikoCommandRunner, parse_int
from lab_11_8_axi_gpreg_bpsk_bringup import SshDevMemRegisterIo, register_snapshot
from lab_11_10_iio_burst_capture import find_iio_readdev_bin
from lab_11_11_iio_gpreg_contention_probe import read_dmesg_tail
from lab_11_12_runtime_fpga_manager_reload import (
    md5_bytes,
    read_remote_file_info,
    run_remote,
    trigger_fpga_manager_reload,
    upload_bytes_via_ssh_cat,
)
from lab_11_13_stock_vs_runtime_rx_compare import (
    iso_now,
    summarize_stage,
    try_reboot_to_stock,
)
from runtime_rx_common import force_rx_common_ctrl_request


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BIT_BIN_PATH = ROOT / "tmp" / "bridge_rx_only.wordswap.bit.bin"
DEFAULT_GPREG_BASE_ADDR = 0x79040000
DEFAULT_ADC_DMA_BASE_ADDR = 0x7C400000
DEFAULT_REMOTE_FIRMWARE_NAME = "course_bpsk_fmcomms2_zc702_runtime.bit.bin"
DEFAULT_CAPTURE_SAMPLE_COUNT = 4096
DEFAULT_CAPTURE_TIMEOUT_S = 15.0
DEFAULT_IIO_READDEV_BUFFER_SIZE = 4096
DEFAULT_DMESG_LINE_COUNT = 80
DEFAULT_REBOOT_TIMEOUT_S = 120.0
DEFAULT_RX_COMMON_CTRL_VALUE = 0x00000003


@dataclass(frozen=True)
class RxCommonReinitProbeConfig:
    ssh_host: str
    ssh_user: str
    ssh_port: int
    ssh_timeout_s: float
    iio_uri: str
    bit_bin_path: str
    remote_firmware_name: str
    gpreg_base_addr: int
    adc_dma_base_addr: int
    capture_sample_count: int
    iio_readdev_buffer_size: int
    capture_timeout_s: float
    dmesg_line_count: int
    rx_common_ctrl_value: int
    reboot_after: bool
    reboot_timeout_s: float


def default_run_tag() -> str:
    return f"live_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def build_default_json_out(run_tag: str) -> Path:
    return ROOT / "docs" / "assets" / f"lab116_runtime_rx_common_reinit_probe_{run_tag}.json"


def safe_probe(label: str, fn: Any) -> dict[str, Any]:
    try:
        return {"ok": True, "result": fn()}
    except Exception as exc:  # pragma: no cover - hardware dependent
        return {
            "ok": False,
            "label": label,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def build_summary(payload: dict[str, Any]) -> dict[str, Any]:
    before = payload["stage_before_reinit"]
    after = payload["stage_after_reinit"]
    reinit = payload["rx_common_reinit"] or {}
    before_ctrl = (reinit.get("before") or {}).get("rx_common_ctrl_req")
    after_ctrl = (reinit.get("after") or {}).get("rx_common_ctrl_req")
    after_clk = (reinit.get("after") or {}).get("rx_common_clk_count")

    def stage_ok(stage: dict[str, Any], key: str) -> bool:
        capture = stage.get(key) or {}
        if not capture.get("ok"):
            return False
        result = capture.get("result") or {}
        if key == "iio_readdev_capture":
            return int(result.get("stdout_len", 0)) > 0
        return int(result.get("metrics", {}).get("complex_sample_count", 0)) > 0

    host_capture_before = {
        "libiio_ok": stage_ok(before, "libiio_capture"),
        "iio_readdev_ok": stage_ok(before, "iio_readdev_capture"),
    }
    host_capture_after = {
        "libiio_ok": stage_ok(after, "libiio_capture"),
        "iio_readdev_ok": stage_ok(after, "iio_readdev_capture"),
    }

    if after_ctrl == "0x00000003" and after_clk not in {None, "0x00000000"} and not any(host_capture_after.values()):
        conclusion = (
            "The manual RX common re-init restores the fabric-side RX clock/reset path, "
            "but host libiio/iio_readdev capture still times out after the runtime reload."
        )
    elif any(host_capture_after.values()):
        conclusion = (
            "The manual RX common re-init restores both the fabric-side RX path and at least one host RX capture path."
        )
    else:
        conclusion = (
            "The runtime overlay still leaves the RX host-capture path unusable in this probe."
        )

    return {
        "rx_common_ctrl_before": before_ctrl,
        "rx_common_ctrl_after": after_ctrl,
        "rx_common_clk_count_after": after_clk,
        "host_capture_before": host_capture_before,
        "host_capture_after": host_capture_after,
        "conclusion": conclusion,
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
    parser.add_argument("--gpreg-base-addr", type=parse_int, default=DEFAULT_GPREG_BASE_ADDR)
    parser.add_argument("--adc-dma-base-addr", type=parse_int, default=DEFAULT_ADC_DMA_BASE_ADDR)
    parser.add_argument("--capture-sample-count", type=int, default=DEFAULT_CAPTURE_SAMPLE_COUNT)
    parser.add_argument("--iio-readdev-buffer-size", type=int, default=DEFAULT_IIO_READDEV_BUFFER_SIZE)
    parser.add_argument("--capture-timeout-s", type=float, default=DEFAULT_CAPTURE_TIMEOUT_S)
    parser.add_argument("--dmesg-line-count", type=int, default=DEFAULT_DMESG_LINE_COUNT)
    parser.add_argument("--rx-common-ctrl-value", type=parse_int, default=DEFAULT_RX_COMMON_CTRL_VALUE)
    parser.add_argument("--reboot-after", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--reboot-timeout-s", type=float, default=DEFAULT_REBOOT_TIMEOUT_S)
    parser.add_argument("--run-tag", default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    run_tag = args.run_tag or default_run_tag()
    json_out = (args.json_out or build_default_json_out(run_tag)).resolve()
    json_out.parent.mkdir(parents=True, exist_ok=True)

    bit_bin_path = args.bit_bin_path.resolve()
    if not bit_bin_path.exists():
        raise SystemExit(f"Missing bitstream payload: {bit_bin_path}")

    cfg = RxCommonReinitProbeConfig(
        ssh_host=args.ssh_host,
        ssh_user=args.ssh_user,
        ssh_port=args.ssh_port,
        ssh_timeout_s=args.ssh_timeout_s,
        iio_uri=args.iio_uri,
        bit_bin_path=str(bit_bin_path),
        remote_firmware_name=args.remote_firmware_name,
        gpreg_base_addr=args.gpreg_base_addr,
        adc_dma_base_addr=args.adc_dma_base_addr,
        capture_sample_count=args.capture_sample_count,
        iio_readdev_buffer_size=args.iio_readdev_buffer_size,
        capture_timeout_s=args.capture_timeout_s,
        dmesg_line_count=args.dmesg_line_count,
        rx_common_ctrl_value=args.rx_common_ctrl_value,
        reboot_after=bool(args.reboot_after),
        reboot_timeout_s=args.reboot_timeout_s,
    )

    iio_readdev_bin = find_iio_readdev_bin(args.iio_readdev_bin)
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

    payload: dict[str, Any] = {
        "timestamp_utc": iso_now(),
        "run_tag": run_tag,
        "config": asdict(cfg),
        "iio_readdev_bin": str(iio_readdev_bin),
        "local_bit_bin": {
            "path": str(bit_bin_path),
            "md5": md5_bytes(bit_payload),
            "size_bytes": len(bit_payload),
        },
        "baseline_fpga_manager_state": None,
        "upload": None,
        "reload": None,
        "post_reload_fpga_manager_state": None,
        "gpreg_before_reinit": None,
        "rx_common_reinit": None,
        "gpreg_after_reinit": None,
        "stage_before_reinit": None,
        "stage_after_reinit": None,
        "summary": None,
        "reboot_after": None,
    }

    try:
        payload["baseline_fpga_manager_state"] = run_remote(
            runner,
            "cat /sys/class/fpga_manager/fpga0/state",
            context="read baseline fpga_manager state",
        )

        remote_path = f"/lib/firmware/{cfg.remote_firmware_name}"
        upload_bytes_via_ssh_cat(runner, payload=bit_payload, remote_path=remote_path)
        payload["upload"] = read_remote_file_info(runner, remote_path)
        payload["reload"] = trigger_fpga_manager_reload(
            runner,
            remote_firmware_name=cfg.remote_firmware_name,
        )
        payload["post_reload_fpga_manager_state"] = run_remote(
            runner,
            "cat /sys/class/fpga_manager/fpga0/state",
            context="read post-reload fpga_manager state",
        )

        payload["gpreg_before_reinit"] = safe_probe(
            "gpreg_before_reinit",
            lambda: register_snapshot(io, cfg.gpreg_base_addr),
        )
        payload["stage_before_reinit"] = summarize_stage(
            name="runtime_overlay_before_rx_common_reinit",
            runner=runner,
            iio_uri=cfg.iio_uri,
            iio_readdev_bin=iio_readdev_bin,
            sample_count=cfg.capture_sample_count,
            iio_readdev_buffer_size=cfg.iio_readdev_buffer_size,
            capture_timeout_s=cfg.capture_timeout_s,
            adc_dma_base_addr=cfg.adc_dma_base_addr,
            dmesg_line_count=cfg.dmesg_line_count,
        )
        payload["rx_common_reinit"] = force_rx_common_ctrl_request(
            runner,
            value=cfg.rx_common_ctrl_value,
        )
        payload["gpreg_after_reinit"] = safe_probe(
            "gpreg_after_reinit",
            lambda: register_snapshot(io, cfg.gpreg_base_addr),
        )
        payload["stage_after_reinit"] = summarize_stage(
            name="runtime_overlay_after_rx_common_reinit",
            runner=runner,
            iio_uri=cfg.iio_uri,
            iio_readdev_bin=iio_readdev_bin,
            sample_count=cfg.capture_sample_count,
            iio_readdev_buffer_size=cfg.iio_readdev_buffer_size,
            capture_timeout_s=cfg.capture_timeout_s,
            adc_dma_base_addr=cfg.adc_dma_base_addr,
            dmesg_line_count=cfg.dmesg_line_count,
        )
        payload["summary"] = build_summary(payload)
    finally:
        if cfg.reboot_after:
            payload["reboot_after"] = try_reboot_to_stock(
                runner,
                host=args.ssh_host,
                user=args.ssh_user,
                password=args.ssh_password,
                port=args.ssh_port,
                ssh_timeout_s=args.ssh_timeout_s,
                iio_uri=args.iio_uri,
                timeout_s=args.reboot_timeout_s,
            )
        else:
            payload["reboot_after"] = {
                "skipped": True,
                "final_dmesg_tail": read_dmesg_tail(runner, line_count=cfg.dmesg_line_count),
            }
        io.close()
        runner.close()

    json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {json_out}")
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
