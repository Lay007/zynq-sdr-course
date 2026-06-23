#!/usr/bin/env python3
"""Lab 11.12 - Runtime fpga_manager reload for the AD9361 gpreg overlay."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shlex
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

from lab_11_7_axi_lite_bpsk_bringup import ParamikoCommandRunner, parse_int
from lab_11_8_axi_gpreg_bpsk_bringup import BringupConfig, REGS, SshDevMemRegisterIo, run_bringup


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BIT_BIN_PATH = ROOT / "tmp" / "bridge_txrx_mux.wordswap.bit.bin"
DEFAULT_JSON_OUT = ROOT / "docs" / "assets" / "lab118_runtime_fpga_manager_reload_live.json"
DEFAULT_HOST = "192.168.40.1"
DEFAULT_USER = "root"
DEFAULT_PASSWORD = "analog"
DEFAULT_PORT = 22
DEFAULT_TIMEOUT_S = 10.0
DEFAULT_IIO_URI = "ip:192.168.40.1"
DEFAULT_BASE_ADDR = 0x79040000
DEFAULT_EXPECTED_ID = 0x4250534B
DEFAULT_FRAME_BIT_COUNT = 281
DEFAULT_PREAMBLE_COUNT = 25
DEFAULT_START_OFFSET = 62
DEFAULT_START_HOLD_MS = 5
DEFAULT_POLL_LIMIT = 128
DEFAULT_POLL_DELAY_MS = 20
DEFAULT_REMOTE_FIRMWARE_NAME = "course_bpsk_fmcomms2_zc702_runtime.bit.bin"
DEFAULT_DMESG_LINE_COUNT = 60


@dataclass(frozen=True)
class RuntimeReloadConfig:
    ssh_host: str
    ssh_user: str
    ssh_port: int
    ssh_timeout_s: float
    iio_uri: str
    bit_bin_path: str
    remote_firmware_name: str
    base_addr: int
    expected_id: int
    frame_bit_count: int
    preamble_count: int
    start_offset: int
    start_hold_ms: int
    poll_limit: int
    poll_delay_ms: int
    dmesg_line_count: int


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def md5_bytes(payload: bytes) -> str:
    digest = hashlib.md5()
    digest.update(payload)
    return digest.hexdigest()


def run_remote(runner: ParamikoCommandRunner, command: str, *, context: str) -> str:
    returncode, stdout, stderr = runner(command)
    if returncode != 0:
        details = stderr.strip() or stdout.strip() or "no diagnostic output"
        raise RuntimeError(f"{context} failed with exit code {returncode}: {details}")
    return stdout.strip()


def upload_bytes_via_ssh_cat(
    runner: ParamikoCommandRunner,
    *,
    payload: bytes,
    remote_path: str,
) -> None:
    transport = runner.client.get_transport()
    if transport is None:
        raise RuntimeError("SSH transport is not available.")
    channel = transport.open_session()
    channel.exec_command(f"cat > {shlex.quote(remote_path)}")
    try:
        for offset in range(0, len(payload), 65536):
            channel.sendall(payload[offset : offset + 65536])
        channel.shutdown_write()
        while True:
            if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready():
                break
            if channel.recv_ready():
                channel.recv(65536)
            if channel.recv_stderr_ready():
                channel.recv_stderr(65536)
            time.sleep(0.01)
        exit_code = channel.recv_exit_status()
    finally:
        channel.close()
    if exit_code != 0:
        raise RuntimeError(f"Remote upload to {remote_path} failed with exit code {exit_code}.")


def read_remote_file_info(runner: ParamikoCommandRunner, remote_path: str) -> dict[str, Any]:
    md5_line = run_remote(runner, f"md5sum {shlex.quote(remote_path)}", context=f"md5 {remote_path}")
    size_line = run_remote(runner, f"wc -c {shlex.quote(remote_path)}", context=f"size {remote_path}")
    return {
        "path": remote_path,
        "md5": md5_line.split()[0],
        "size_bytes": int(size_line.split()[0]),
    }


def trigger_fpga_manager_reload(
    runner: ParamikoCommandRunner,
    *,
    remote_firmware_name: str,
) -> dict[str, Any]:
    run_remote(
        runner,
        "printf %s 0 > /sys/class/fpga_manager/fpga0/flags",
        context="write fpga_manager flags",
    )
    run_remote(
        runner,
        f"printf %s {shlex.quote(remote_firmware_name)} > /sys/class/fpga_manager/fpga0/firmware",
        context="trigger fpga_manager reload",
    )
    return {
        "state": run_remote(
            runner,
            "cat /sys/class/fpga_manager/fpga0/state",
            context="read fpga_manager state",
        ),
        "dmesg_tail": read_dmesg_tail(runner, line_count=DEFAULT_DMESG_LINE_COUNT),
    }


def read_dmesg_tail(runner: ParamikoCommandRunner, *, line_count: int) -> list[str]:
    output = run_remote(runner, f"dmesg | tail -n {line_count}", context="read dmesg tail")
    return output.splitlines()


def probe_gpreg_id(io: SshDevMemRegisterIo) -> dict[str, Any]:
    return {
        "core_id": f"0x{io.read32(REGS.core_id):08X}",
        "signature": f"0x{io.read32(REGS.gp_signature_in):08X}",
    }


def load_iio_probe_module() -> ModuleType:
    module_path = ROOT / "blocks" / "block_06_rf_frontend_and_ad9363" / "python" / "lab_6_3_probe_iio_context.py"
    spec = importlib.util.spec_from_file_location("lab_6_3_probe_iio_context", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load IIO probe module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def probe_iio_context(uri: str) -> dict[str, Any]:
    module = load_iio_probe_module()
    return module.probe_context(uri=uri, device_filter="ad9361", include_debug_attrs=False)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-host", default=DEFAULT_HOST)
    parser.add_argument("--ssh-user", default=DEFAULT_USER)
    parser.add_argument("--ssh-password", default=DEFAULT_PASSWORD)
    parser.add_argument("--ssh-port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--ssh-timeout-s", type=float, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--iio-uri", default=DEFAULT_IIO_URI)
    parser.add_argument("--bit-bin-path", type=Path, default=DEFAULT_BIT_BIN_PATH)
    parser.add_argument("--remote-firmware-name", default=DEFAULT_REMOTE_FIRMWARE_NAME)
    parser.add_argument("--base-addr", type=parse_int, default=DEFAULT_BASE_ADDR)
    parser.add_argument("--expected-id", type=parse_int, default=DEFAULT_EXPECTED_ID)
    parser.add_argument("--frame-bit-count", type=int, default=DEFAULT_FRAME_BIT_COUNT)
    parser.add_argument("--preamble-count", type=int, default=DEFAULT_PREAMBLE_COUNT)
    parser.add_argument("--start-offset", type=int, default=DEFAULT_START_OFFSET)
    parser.add_argument("--start-hold-ms", type=int, default=DEFAULT_START_HOLD_MS)
    parser.add_argument("--poll-limit", type=int, default=DEFAULT_POLL_LIMIT)
    parser.add_argument("--poll-delay-ms", type=int, default=DEFAULT_POLL_DELAY_MS)
    parser.add_argument("--dmesg-line-count", type=int, default=DEFAULT_DMESG_LINE_COUNT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    bit_bin_path = args.bit_bin_path.resolve()
    if not bit_bin_path.exists():
        raise SystemExit(f"Missing bitstream payload: {bit_bin_path}")

    cfg = RuntimeReloadConfig(
        ssh_host=args.ssh_host,
        ssh_user=args.ssh_user,
        ssh_port=args.ssh_port,
        ssh_timeout_s=args.ssh_timeout_s,
        iio_uri=args.iio_uri,
        bit_bin_path=str(bit_bin_path),
        remote_firmware_name=args.remote_firmware_name,
        base_addr=args.base_addr,
        expected_id=args.expected_id,
        frame_bit_count=args.frame_bit_count,
        preamble_count=args.preamble_count,
        start_offset=args.start_offset,
        start_hold_ms=args.start_hold_ms,
        poll_limit=args.poll_limit,
        poll_delay_ms=args.poll_delay_ms,
        dmesg_line_count=args.dmesg_line_count,
    )

    local_payload = bit_bin_path.read_bytes()
    local_info = {
        "path": str(bit_bin_path),
        "md5": md5_bytes(local_payload),
        "size_bytes": len(local_payload),
    }

    runner = ParamikoCommandRunner(
        host=args.ssh_host,
        user=args.ssh_user,
        password=args.ssh_password,
        port=args.ssh_port,
        key_path=None,
        timeout_s=args.ssh_timeout_s,
    )
    io = SshDevMemRegisterIo(args.base_addr, command_runner=runner)

    payload: dict[str, Any] = {
        "timestamp_utc": iso_now(),
        "config": asdict(cfg),
        "local_bit_bin": local_info,
        "baseline": {},
        "upload": {},
        "reload": {},
        "gpreg_after_reload": None,
        "iio_after_reload": None,
    }

    try:
        payload["baseline"]["fpga_manager_state"] = run_remote(
            runner,
            "cat /sys/class/fpga_manager/fpga0/state",
            context="read baseline fpga_manager state",
        )
        try:
            payload["baseline"]["gpreg"] = probe_gpreg_id(io)
        except Exception as exc:
            payload["baseline"]["gpreg_error"] = {
                "error_type": type(exc).__name__,
                "error": str(exc),
            }

        remote_path = f"/lib/firmware/{args.remote_firmware_name}"
        upload_bytes_via_ssh_cat(runner, payload=local_payload, remote_path=remote_path)
        payload["upload"] = read_remote_file_info(runner, remote_path)

        payload["reload"] = trigger_fpga_manager_reload(
            runner,
            remote_firmware_name=args.remote_firmware_name,
        )
        payload["reload"]["state"] = run_remote(
            runner,
            "cat /sys/class/fpga_manager/fpga0/state",
            context="read post-reload fpga_manager state",
        )
        payload["reload"]["dmesg_tail"] = read_dmesg_tail(
            runner,
            line_count=args.dmesg_line_count,
        )

        bringup_cfg = BringupConfig(
            backend="ssh-devmem",
            base_addr=args.base_addr,
            frame_bit_count=args.frame_bit_count,
            preamble_count=args.preamble_count,
            start_offset=args.start_offset,
            rx_decision_mode=0,
            start_hold_ms=args.start_hold_ms,
            poll_limit=args.poll_limit,
            poll_delay_ms=args.poll_delay_ms,
            expected_id=args.expected_id,
            clear_done=True,
            max_total_errors=None,
            max_payload_errors=None,
        )
        payload["gpreg_after_reload"] = asdict(run_bringup(io, bringup_cfg))
        try:
            payload["iio_after_reload"] = probe_iio_context(args.iio_uri)
        except Exception as exc:
            payload["iio_after_reload"] = {
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
    finally:
        io.close()

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    gpreg_result = payload["gpreg_after_reload"]
    iio_payload = payload["iio_after_reload"]
    print(f"Wrote {args.json_out}")
    print(f"Reload state: {payload['reload'].get('state')}")
    if gpreg_result is None:
        print("GPREG result: unavailable")
    else:
        print(
            "GPREG result:"
            f" id=0x{gpreg_result['id_word']:08X}"
            f" signature=0x{gpreg_result['signature_word']:08X}"
            f" tx_valid={gpreg_result['tx_valid_count']}"
            f" rx_valid={gpreg_result['rx_valid_count']}"
            f" received_bits={gpreg_result['received_bits']}"
        )
    if isinstance(iio_payload, dict) and "devices" in iio_payload:
        print(f"IIO devices after reload: {len(iio_payload['devices'])}")
    else:
        print(f"IIO probe error: {iio_payload}")


if __name__ == "__main__":
    main()
