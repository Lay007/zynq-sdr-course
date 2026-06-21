#!/usr/bin/env python3
"""Lab 11.11 - Reproduce contention between host IIO capture and gpreg/devmem burst control."""

from __future__ import annotations

import argparse
import json
import subprocess
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lab_11_7_axi_lite_bpsk_bringup import ParamikoCommandRunner, parse_int
from lab_11_8_axi_gpreg_bpsk_bringup import BringupConfig, SshDevMemRegisterIo, run_bringup
from lab_11_9_rf_discovery_sweep import configure_ad9361, read_ad9361_state
from lab_11_10_iio_burst_capture import find_iio_readdev_bin, restore_rf_state


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_JSON_OUT = ROOT / "docs" / "assets" / "lab111_iio_gpreg_contention_probe_live.json"
DEFAULT_IIO_URI = "ip:192.168.40.1"
DEFAULT_HOST = "192.168.40.1"
DEFAULT_USER = "root"
DEFAULT_PASSWORD = "analog"
DEFAULT_PORT = 22
DEFAULT_TIMEOUT_S = 10.0
DEFAULT_GPREG_BASE_ADDR = 0x79040000
DEFAULT_ADC_DMA_BASE_ADDR = 0x7C400000
DEFAULT_FRAME_BIT_COUNT = 281
DEFAULT_PREAMBLE_COUNT = 25
DEFAULT_START_OFFSET = 62
DEFAULT_START_HOLD_MS = 5
DEFAULT_POLL_LIMIT = 128
DEFAULT_POLL_DELAY_MS = 20
DEFAULT_RX_GAIN_DB = 30.0
DEFAULT_TX_ATTENUATION_DB = -60.0
DEFAULT_SETTLE_MS = 50
DEFAULT_BUFFER_SIZE = 8192
DEFAULT_CAPTURE_TIMEOUT_S = 20.0

DMAC_REGS = {
    "VERSION": 0x000,
    "ID": 0x004,
    "SCRATCH": 0x008,
    "IDENT": 0x00C,
    "INTF_DESC": 0x010,
    "COHERENCY": 0x014,
    "IRQ_MASK": 0x080,
    "IRQ_PENDING": 0x084,
    "IRQ_SOURCE": 0x088,
    "CTRL": 0x400,
    "TRANSFER_ID": 0x404,
    "TRANSFER_SUBMIT": 0x408,
    "FLAGS": 0x40C,
    "DEST_ADDRESS": 0x410,
    "SRC_ADDRESS": 0x414,
    "X_LENGTH": 0x418,
    "Y_LENGTH": 0x41C,
    "DEST_STRIDE": 0x420,
    "SRC_STRIDE": 0x424,
    "TRANSFER_DONE": 0x428,
    "DBG_DEST_ADDR": 0x434,
    "DBG_SRC_ADDR": 0x438,
    "DBG_STATUS": 0x43C,
    "DBG_IDS0": 0x440,
    "DBG_IDS1": 0x444,
}


@dataclass(frozen=True)
class Scenario:
    name: str
    sample_count: int
    trigger_delay_ms: float | None


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_devmem_output(stdout: str) -> int:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("devmem returned no output.")
    return int(lines[-1], 0)


def read_dmac_snapshot(runner: ParamikoCommandRunner, base_addr: int) -> dict[str, dict[str, Any]]:
    snapshot: dict[str, dict[str, Any]] = {}
    for name, offset in DMAC_REGS.items():
        address = base_addr + offset
        rc, stdout, stderr = runner(f"/sbin/devmem 0x{address:X} 32")
        if rc != 0:
            snapshot[name] = {
                "address": f"0x{address:08X}",
                "error": stderr.strip() or stdout.strip() or f"exit code {rc}",
            }
            continue
        snapshot[name] = {
            "address": f"0x{address:08X}",
            "value": parse_devmem_output(stdout),
        }
    return snapshot


def read_dmesg_tail(runner: ParamikoCommandRunner, line_count: int = 40) -> list[str]:
    rc, stdout, stderr = runner(f"dmesg | tail -n {line_count}")
    if rc != 0:
        details = stderr.strip() or stdout.strip() or f"exit code {rc}"
        return [f"<dmesg read failed: {details}>"]
    return stdout.splitlines()


def run_iio_capture(
    *,
    iio_readdev_bin: Path,
    uri: str,
    buffer_size: int,
    sample_count: int,
    timeout_s: float,
) -> dict[str, Any]:
    proc = subprocess.run(
        [
            str(iio_readdev_bin),
            "-u",
            uri,
            "-b",
            str(buffer_size),
            "-s",
            str(sample_count),
            "cf-ad9361-lpc",
            "voltage0",
            "voltage1",
        ],
        capture_output=True,
        timeout=timeout_s,
    )
    return {
        "returncode": proc.returncode,
        "stdout_len": len(proc.stdout),
        "stderr": proc.stderr.decode("utf-8", errors="replace").strip(),
    }


def run_overlap_capture(
    *,
    iio_readdev_bin: Path,
    uri: str,
    buffer_size: int,
    sample_count: int,
    timeout_s: float,
    trigger_delay_ms: float,
    gpreg_base_addr: int,
    host: str,
    user: str,
    password: str,
    port: int,
    ssh_timeout_s: float,
    frame_bit_count: int,
    preamble_count: int,
    start_offset: int,
    start_hold_ms: int,
    poll_limit: int,
    poll_delay_ms: int,
) -> dict[str, Any]:
    runner = ParamikoCommandRunner(
        host=host,
        user=user,
        password=password,
        port=port,
        key_path=None,
        timeout_s=ssh_timeout_s,
    )
    io = SshDevMemRegisterIo(gpreg_base_addr, command_runner=runner)
    burst: dict[str, Any] = {
        "ok": None,
        "error_type": None,
        "error": None,
        "result": None,
        "started_utc": None,
        "finished_utc": None,
    }

    def burst_worker() -> None:
        time.sleep(max(trigger_delay_ms, 0.0) / 1000.0)
        burst["started_utc"] = iso_now()
        cfg = BringupConfig(
            backend="ssh-devmem",
            base_addr=gpreg_base_addr,
            frame_bit_count=frame_bit_count,
            preamble_count=preamble_count,
            start_offset=start_offset,
            start_hold_ms=start_hold_ms,
            poll_limit=poll_limit,
            poll_delay_ms=poll_delay_ms,
            expected_id=0x4250534B,
            clear_done=True,
            max_total_errors=None,
            max_payload_errors=None,
        )
        try:
            burst["result"] = asdict(run_bringup(io, cfg))
            burst["ok"] = True
        except Exception as exc:  # pragma: no cover - hardware dependent
            burst["ok"] = False
            burst["error_type"] = type(exc).__name__
            burst["error"] = str(exc)
        finally:
            burst["finished_utc"] = iso_now()

    worker = threading.Thread(target=burst_worker, daemon=True)
    worker.start()
    capture = None
    capture_error = None
    try:
        capture = run_iio_capture(
            iio_readdev_bin=iio_readdev_bin,
            uri=uri,
            buffer_size=buffer_size,
            sample_count=sample_count,
            timeout_s=timeout_s,
        )
    except Exception as exc:  # pragma: no cover - hardware dependent
        capture_error = {
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    worker.join(timeout=max(timeout_s, 5.0))
    io.close()
    return {
        "capture": capture,
        "capture_error": capture_error,
        "burst": burst,
    }


def build_summary(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for scenario in scenarios:
        name = scenario["scenario"]["name"]
        capture = scenario.get("capture")
        burst = scenario.get("burst")
        summary[name] = {
            "capture_stdout_len": None if capture is None else capture.get("stdout_len"),
            "capture_stderr": None if capture is None else capture.get("stderr"),
            "capture_error": scenario.get("capture_error"),
            "burst_ok": None if burst is None else burst.get("ok"),
            "burst_error": None if burst is None else burst.get("error"),
            "received_bits": None
            if burst is None or burst.get("result") is None
            else burst["result"].get("received_bits"),
        }
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-host", default=DEFAULT_HOST)
    parser.add_argument("--ssh-user", default=DEFAULT_USER)
    parser.add_argument("--ssh-password", default=DEFAULT_PASSWORD)
    parser.add_argument("--ssh-port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--ssh-timeout-s", type=float, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--iio-uri", default=DEFAULT_IIO_URI)
    parser.add_argument("--iio-readdev-bin", default=None)
    parser.add_argument("--gpreg-base-addr", type=parse_int, default=DEFAULT_GPREG_BASE_ADDR)
    parser.add_argument("--adc-dma-base-addr", type=parse_int, default=DEFAULT_ADC_DMA_BASE_ADDR)
    parser.add_argument("--frame-bit-count", type=int, default=DEFAULT_FRAME_BIT_COUNT)
    parser.add_argument("--preamble-count", type=int, default=DEFAULT_PREAMBLE_COUNT)
    parser.add_argument("--start-offset", type=int, default=DEFAULT_START_OFFSET)
    parser.add_argument("--start-hold-ms", type=int, default=DEFAULT_START_HOLD_MS)
    parser.add_argument("--poll-limit", type=int, default=DEFAULT_POLL_LIMIT)
    parser.add_argument("--poll-delay-ms", type=int, default=DEFAULT_POLL_DELAY_MS)
    parser.add_argument("--rx-gain-db", type=float, default=DEFAULT_RX_GAIN_DB)
    parser.add_argument("--tx-attenuation-db", type=float, default=DEFAULT_TX_ATTENUATION_DB)
    parser.add_argument("--settle-ms", type=int, default=DEFAULT_SETTLE_MS)
    parser.add_argument("--buffer-size", type=int, default=DEFAULT_BUFFER_SIZE)
    parser.add_argument("--capture-timeout-s", type=float, default=DEFAULT_CAPTURE_TIMEOUT_S)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    iio_readdev_bin = find_iio_readdev_bin(args.iio_readdev_bin)

    control_runner = ParamikoCommandRunner(
        host=args.ssh_host,
        user=args.ssh_user,
        password=args.ssh_password,
        port=args.ssh_port,
        key_path=None,
        timeout_s=args.ssh_timeout_s,
    )

    board_before = read_ad9361_state(control_runner)
    configure_ad9361(
        control_runner,
        rx_gain_db=args.rx_gain_db,
        tx_attenuation_db=args.tx_attenuation_db,
        settle_ms=args.settle_ms,
    )
    board_ready = read_ad9361_state(control_runner)

    scenario_defs = [
        Scenario(name="standalone_capture_262144", sample_count=262144, trigger_delay_ms=None),
        Scenario(name="overlap_capture_8192_delay_1ms", sample_count=8192, trigger_delay_ms=1.0),
        Scenario(name="overlap_capture_262144_delay_5ms", sample_count=262144, trigger_delay_ms=5.0),
    ]
    scenario_results: list[dict[str, Any]] = []
    try:
        for scenario in scenario_defs:
            before = read_dmac_snapshot(control_runner, args.adc_dma_base_addr)
            if scenario.trigger_delay_ms is None:
                capture = run_iio_capture(
                    iio_readdev_bin=iio_readdev_bin,
                    uri=args.iio_uri,
                    buffer_size=args.buffer_size,
                    sample_count=scenario.sample_count,
                    timeout_s=args.capture_timeout_s,
                )
                result = {
                    "scenario": asdict(scenario),
                    "capture": capture,
                    "capture_error": None,
                    "burst": None,
                    "adc_dma_before": before,
                    "adc_dma_after": read_dmac_snapshot(control_runner, args.adc_dma_base_addr),
                    "dmesg_tail": read_dmesg_tail(control_runner),
                }
            else:
                overlap = run_overlap_capture(
                    iio_readdev_bin=iio_readdev_bin,
                    uri=args.iio_uri,
                    buffer_size=args.buffer_size,
                    sample_count=scenario.sample_count,
                    timeout_s=args.capture_timeout_s,
                    trigger_delay_ms=scenario.trigger_delay_ms,
                    gpreg_base_addr=args.gpreg_base_addr,
                    host=args.ssh_host,
                    user=args.ssh_user,
                    password=args.ssh_password,
                    port=args.ssh_port,
                    ssh_timeout_s=args.ssh_timeout_s,
                    frame_bit_count=args.frame_bit_count,
                    preamble_count=args.preamble_count,
                    start_offset=args.start_offset,
                    start_hold_ms=args.start_hold_ms,
                    poll_limit=args.poll_limit,
                    poll_delay_ms=args.poll_delay_ms,
                )
                result = {
                    "scenario": asdict(scenario),
                    "capture": overlap["capture"],
                    "capture_error": overlap["capture_error"],
                    "burst": overlap["burst"],
                    "adc_dma_before": before,
                    "adc_dma_after": read_dmac_snapshot(control_runner, args.adc_dma_base_addr),
                    "dmesg_tail": read_dmesg_tail(control_runner),
                }
            scenario_results.append(result)
    finally:
        restore_error = None
        try:
            restore_rf_state(control_runner, board_before)
        except Exception as exc:  # pragma: no cover - best effort only
            restore_error = f"{type(exc).__name__}: {exc}"
        board_after = read_ad9361_state(control_runner)
        control_runner.close()

    payload = {
        "timestamp_utc": iso_now(),
        "iio_readdev_bin": str(iio_readdev_bin),
        "board_before": board_before,
        "board_ready": board_ready,
        "board_after": board_after,
        "restore_error": restore_error,
        "summary": build_summary(scenario_results),
        "scenarios": scenario_results,
    }
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Wrote {args.json_out}")
    print(json.dumps(payload["summary"], indent=2))


if __name__ == "__main__":
    main()
