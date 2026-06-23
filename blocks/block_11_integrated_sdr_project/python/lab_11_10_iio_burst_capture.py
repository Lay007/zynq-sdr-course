#!/usr/bin/env python3
"""Lab 11.10 - Capture a timed RX snapshot around the AD9361 gpreg discovery burst."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from lab_11_7_axi_lite_bpsk_bringup import ParamikoCommandRunner, parse_int
from lab_11_8_axi_gpreg_bpsk_bringup import BringupConfig, SshDevMemRegisterIo, run_bringup
from lab_11_9_rf_discovery_sweep import configure_ad9361, read_ad9361_state


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_JSON_OUT = ROOT / "docs" / "assets" / "lab110_iio_burst_capture_live.json"
DEFAULT_IIO_READDEV = Path("C:/Program Files/IIO Oscilloscope/bin/iio_readdev.exe")
DEFAULT_IIO_URI = "ip:192.168.40.1"
DEFAULT_HOST = "192.168.40.1"
DEFAULT_USER = "root"
DEFAULT_PASSWORD = "analog"
DEFAULT_PORT = 22
DEFAULT_TIMEOUT_S = 10.0
DEFAULT_BASE_ADDR = 0x79040000
DEFAULT_FRAME_BIT_COUNT = 281
DEFAULT_PREAMBLE_COUNT = 25
DEFAULT_START_OFFSET = 62
DEFAULT_POLL_LIMIT = 128
DEFAULT_POLL_DELAY_MS = 20
DEFAULT_START_HOLD_MS = 5
DEFAULT_RX_GAIN_DB = 30.0
DEFAULT_TX_ATTENUATION_DB = -60.0
DEFAULT_SETTLE_MS = 50
DEFAULT_SAMPLE_RATE_HZ = 30_720_000
DEFAULT_SAMPLE_COUNT = 2_097_152
DEFAULT_BUFFER_SIZE = 131_072
DEFAULT_TRIGGER_DELAY_MS = 10.0
DEFAULT_CAPTURE_TIMEOUT_S = 30.0
DEFAULT_WINDOW_SAMPLES = 30_720


@dataclass(frozen=True)
class CaptureConfig:
    ssh_host: str
    ssh_user: str
    ssh_port: int
    iio_uri: str
    base_addr: int
    frame_bit_count: int
    preamble_count: int
    start_offset: int
    start_hold_ms: int
    poll_limit: int
    poll_delay_ms: int
    rx_gain_db: float
    tx_attenuation_db: float
    settle_ms: int
    sample_rate_hz: int
    sample_count: int
    buffer_size: int
    trigger_delay_ms: float
    capture_timeout_s: float
    capture_device: str
    capture_channels: list[str]
    configure_rf: bool
    restore_rf: bool


class CaptureReadError(RuntimeError):
    """Capture failed but may still include burst-side evidence."""

    def __init__(
        self,
        message: str,
        *,
        stdout_bytes: bytes,
        stderr_text: str,
        burst_payload: dict[str, Any],
    ) -> None:
        super().__init__(message)
        self.stdout_bytes = stdout_bytes
        self.stderr_text = stderr_text
        self.burst_payload = burst_payload


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_iio_readdev_bin(candidate: str | None) -> Path:
    if candidate:
        path = Path(candidate).expanduser()
        if path.exists():
            return path.resolve()
    resolved = shutil.which("iio_readdev.exe") or shutil.which("iio_readdev")
    if resolved:
        return Path(resolved).resolve()
    if DEFAULT_IIO_READDEV.exists():
        return DEFAULT_IIO_READDEV.resolve()
    raise RuntimeError(
        "Unable to locate iio_readdev. Install Analog Devices IIO tools or pass --iio-readdev-bin."
    )


def parse_capture_bytes(raw_bytes: bytes) -> np.ndarray:
    samples = np.frombuffer(raw_bytes, dtype="<i2")
    if samples.size < 2:
        raise RuntimeError("Capture returned fewer than one complex sample.")
    usable_count = samples.size - (samples.size % 2)
    if usable_count != samples.size:
        samples = samples[:usable_count]
    return samples.reshape(-1, 2)


def analyze_capture(
    iq_pairs: np.ndarray,
    *,
    sample_rate_hz: int,
    trigger_delay_ms: float,
    window_samples: int,
) -> dict[str, Any]:
    i_samples = iq_pairs[:, 0].astype(np.float32, copy=False)
    q_samples = iq_pairs[:, 1].astype(np.float32, copy=False)
    power = (i_samples * i_samples + q_samples * q_samples).astype(np.float64, copy=False)
    complex_sample_count = int(iq_pairs.shape[0])
    if complex_sample_count == 0:
        raise RuntimeError("Capture contained zero complex samples.")

    window_len = max(1, min(window_samples, complex_sample_count))
    if complex_sample_count >= window_len:
        kernel = np.ones(window_len, dtype=np.float64) / float(window_len)
        window_power = np.convolve(power, kernel, mode="valid")
    else:
        window_power = power.copy()

    trigger_sample_index = min(
        max(int(round(sample_rate_hz * trigger_delay_ms / 1000.0)), 0),
        complex_sample_count - 1,
    )
    trigger_window_index = min(trigger_sample_index, max(len(window_power) - 1, 0))
    peak_window_index = int(np.argmax(window_power))
    peak_window_power = float(window_power[peak_window_index])
    median_window_power = float(np.median(window_power))
    trigger_window_power = float(window_power[trigger_window_index])
    full_scale = float((2**11) - 1)

    def power_to_dbfs(value: float) -> float:
        normalized = max(value / (2.0 * full_scale * full_scale), 1e-12)
        return 10.0 * float(np.log10(normalized))

    abs_i = np.abs(i_samples)
    abs_q = np.abs(q_samples)
    peak_component = float(max(abs_i.max(initial=0.0), abs_q.max(initial=0.0)))
    clip_fraction = float(np.mean((abs_i >= full_scale) | (abs_q >= full_scale)))

    return {
        "complex_sample_count": complex_sample_count,
        "duration_ms": round(1000.0 * complex_sample_count / sample_rate_hz, 3),
        "window_samples": int(window_len),
        "mean_power_dbfs": round(power_to_dbfs(float(power.mean())), 3),
        "median_window_power_dbfs": round(power_to_dbfs(median_window_power), 3),
        "peak_window_power_dbfs": round(power_to_dbfs(peak_window_power), 3),
        "trigger_window_power_dbfs": round(power_to_dbfs(trigger_window_power), 3),
        "peak_to_median_window_db": round(
            10.0 * float(np.log10(max(peak_window_power, 1e-12) / max(median_window_power, 1e-12))),
            3,
        ),
        "trigger_to_median_window_db": round(
            10.0 * float(np.log10(max(trigger_window_power, 1e-12) / max(median_window_power, 1e-12))),
            3,
        ),
        "peak_component_abs_i16": round(peak_component, 1),
        "peak_component_dbfs": round(
            20.0 * float(np.log10(max(peak_component / full_scale, 1e-12))),
            3,
        ),
        "clip_fraction": round(clip_fraction, 8),
        "trigger_sample_index_estimate": int(trigger_sample_index),
        "trigger_time_ms_estimate": round(1000.0 * trigger_sample_index / sample_rate_hz, 3),
        "peak_window_index": int(peak_window_index),
        "peak_window_time_ms": round(1000.0 * peak_window_index / sample_rate_hz, 3),
        "peak_minus_trigger_ms": round(
            1000.0 * (peak_window_index - trigger_sample_index) / sample_rate_hz,
            3,
        ),
        "energy_event_detected": bool(
            (peak_window_power > 0.0)
            and (10.0 * float(np.log10(max(peak_window_power, 1e-12) / max(median_window_power, 1e-12))) >= 3.0)
        ),
    }


def write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def strip_db_units(value: str) -> str:
    return value.replace(" dB", "").strip()


def restore_rf_state(runner: ParamikoCommandRunner, state: dict[str, str]) -> None:
    writes = (
        ("/sys/bus/iio/devices/iio:device0/out_altvoltage1_TX_LO_powerdown", state["tx_lo_powerdown"]),
        ("/sys/bus/iio/devices/iio:device0/in_voltage0_gain_control_mode", state["rx_gain_mode_ch0"]),
        ("/sys/bus/iio/devices/iio:device0/in_voltage1_gain_control_mode", state["rx_gain_mode_ch1"]),
        ("/sys/bus/iio/devices/iio:device0/in_voltage0_hardwaregain", strip_db_units(state["rx_gain_db_ch0"])),
        ("/sys/bus/iio/devices/iio:device0/in_voltage1_hardwaregain", strip_db_units(state["rx_gain_db_ch1"])),
        ("/sys/bus/iio/devices/iio:device0/out_voltage0_hardwaregain", strip_db_units(state["tx_attenuation_db_ch0"])),
        ("/sys/bus/iio/devices/iio:device0/out_voltage1_hardwaregain", strip_db_units(state["tx_attenuation_db_ch1"])),
    )
    failures: list[str] = []
    for path, value in writes:
        command = f"printf %s {json.dumps(value)} > {json.dumps(path)}"
        returncode, stdout, stderr = runner(command)
        if returncode != 0:
            details = stderr.strip() or stdout.strip() or "no diagnostic output"
            failures.append(f"{path}: {details}")
    if failures:
        raise RuntimeError("; ".join(failures))


def capture_with_trigger(
    *,
    iio_readdev_bin: Path,
    cfg: CaptureConfig,
    io: SshDevMemRegisterIo,
) -> tuple[bytes, str, dict[str, Any]]:
    bringup_cfg = BringupConfig(
        backend="ssh-devmem",
        base_addr=cfg.base_addr,
        frame_bit_count=cfg.frame_bit_count,
        preamble_count=cfg.preamble_count,
        start_offset=cfg.start_offset,
        rx_decision_mode=0,
        start_hold_ms=cfg.start_hold_ms,
        poll_limit=cfg.poll_limit,
        poll_delay_ms=cfg.poll_delay_ms,
        expected_id=0x4250534B,
        clear_done=True,
        max_total_errors=None,
        max_payload_errors=None,
    )

    argv = [
        str(iio_readdev_bin),
        "-u",
        cfg.iio_uri,
        "-b",
        str(cfg.buffer_size),
        "-s",
        str(cfg.sample_count),
        cfg.capture_device,
        *cfg.capture_channels,
    ]
    proc = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    burst_payload: dict[str, Any] = {
        "started_utc": None,
        "finished_utc": None,
        "ok": False,
        "error_type": None,
        "error": None,
        "result": None,
    }

    def trigger_worker() -> None:
        time.sleep(max(cfg.trigger_delay_ms, 0.0) / 1000.0)
        burst_payload["started_utc"] = iso_now()
        try:
            result = run_bringup(io, bringup_cfg)
        except Exception as exc:  # pragma: no cover - depends on hardware state
            burst_payload["error_type"] = type(exc).__name__
            burst_payload["error"] = str(exc)
        else:
            burst_payload["ok"] = True
            burst_payload["result"] = asdict(result)
        finally:
            burst_payload["finished_utc"] = iso_now()

    trigger_thread = threading.Thread(target=trigger_worker, daemon=True)
    capture_started_utc = iso_now()
    trigger_thread.start()
    try:
        stdout_bytes, stderr_bytes = proc.communicate(timeout=cfg.capture_timeout_s)
    except subprocess.TimeoutExpired as exc:
        proc.kill()
        stdout_bytes, stderr_bytes = proc.communicate()
        trigger_thread.join(timeout=2.0)
        raise RuntimeError(
            f"iio_readdev timed out after {cfg.capture_timeout_s} s while capturing {cfg.sample_count} samples."
        ) from exc

    trigger_thread.join(timeout=2.0)
    if proc.returncode != 0:
        stderr_text = stderr_bytes.decode("utf-8", errors="replace")
        raise CaptureReadError(
            f"iio_readdev failed with exit code {proc.returncode}: {stderr_text.strip() or 'no diagnostic output'}",
            stdout_bytes=stdout_bytes,
            stderr_text=stderr_text,
            burst_payload=burst_payload,
        )
    if not stdout_bytes:
        stderr_text = stderr_bytes.decode("utf-8", errors="replace").strip()
        raise CaptureReadError(
            f"iio_readdev returned no samples for {cfg.capture_device}: {stderr_text or 'empty stdout'}",
            stdout_bytes=stdout_bytes,
            stderr_text=stderr_text,
            burst_payload=burst_payload,
        )

    burst_payload["capture_started_utc"] = capture_started_utc
    burst_payload["capture_finished_utc"] = iso_now()
    return stdout_bytes, stderr_bytes.decode("utf-8", errors="replace"), burst_payload


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-host", default=DEFAULT_HOST)
    parser.add_argument("--ssh-user", default=DEFAULT_USER)
    parser.add_argument("--ssh-password", default=DEFAULT_PASSWORD)
    parser.add_argument("--ssh-port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--ssh-timeout-s", type=float, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--iio-uri", default=DEFAULT_IIO_URI)
    parser.add_argument("--iio-readdev-bin", default=None)
    parser.add_argument("--base-addr", type=parse_int, default=DEFAULT_BASE_ADDR)
    parser.add_argument("--frame-bit-count", type=int, default=DEFAULT_FRAME_BIT_COUNT)
    parser.add_argument("--preamble-count", type=int, default=DEFAULT_PREAMBLE_COUNT)
    parser.add_argument("--start-offset", type=int, default=DEFAULT_START_OFFSET)
    parser.add_argument("--start-hold-ms", type=int, default=DEFAULT_START_HOLD_MS)
    parser.add_argument("--poll-limit", type=int, default=DEFAULT_POLL_LIMIT)
    parser.add_argument("--poll-delay-ms", type=int, default=DEFAULT_POLL_DELAY_MS)
    parser.add_argument("--rx-gain-db", type=float, default=DEFAULT_RX_GAIN_DB)
    parser.add_argument("--tx-attenuation-db", type=float, default=DEFAULT_TX_ATTENUATION_DB)
    parser.add_argument("--settle-ms", type=int, default=DEFAULT_SETTLE_MS)
    parser.add_argument("--sample-rate-hz", type=int, default=DEFAULT_SAMPLE_RATE_HZ)
    parser.add_argument("--sample-count", type=int, default=DEFAULT_SAMPLE_COUNT)
    parser.add_argument("--buffer-size", type=int, default=DEFAULT_BUFFER_SIZE)
    parser.add_argument("--trigger-delay-ms", type=float, default=DEFAULT_TRIGGER_DELAY_MS)
    parser.add_argument("--capture-timeout-s", type=float, default=DEFAULT_CAPTURE_TIMEOUT_S)
    parser.add_argument("--capture-device", default="cf-ad9361-lpc")
    parser.add_argument("--capture-channels", nargs="+", default=["voltage0", "voltage1"])
    parser.add_argument("--out-iq", type=Path, default=None)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--configure-rf", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--restore-rf", action=argparse.BooleanOptionalAction, default=True)
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    cfg = CaptureConfig(
        ssh_host=args.ssh_host,
        ssh_user=args.ssh_user,
        ssh_port=args.ssh_port,
        iio_uri=args.iio_uri,
        base_addr=args.base_addr,
        frame_bit_count=args.frame_bit_count,
        preamble_count=args.preamble_count,
        start_offset=args.start_offset,
        start_hold_ms=args.start_hold_ms,
        poll_limit=args.poll_limit,
        poll_delay_ms=args.poll_delay_ms,
        rx_gain_db=args.rx_gain_db,
        tx_attenuation_db=args.tx_attenuation_db,
        settle_ms=args.settle_ms,
        sample_rate_hz=args.sample_rate_hz,
        sample_count=args.sample_count,
        buffer_size=args.buffer_size,
        trigger_delay_ms=args.trigger_delay_ms,
        capture_timeout_s=args.capture_timeout_s,
        capture_device=args.capture_device,
        capture_channels=list(args.capture_channels),
        configure_rf=bool(args.configure_rf),
        restore_rf=bool(args.restore_rf),
    )
    iio_readdev_bin = find_iio_readdev_bin(args.iio_readdev_bin)

    runner = ParamikoCommandRunner(
        host=args.ssh_host,
        user=args.ssh_user,
        password=args.ssh_password,
        port=args.ssh_port,
        key_path=None,
        timeout_s=args.ssh_timeout_s,
    )
    io = SshDevMemRegisterIo(args.base_addr, command_runner=runner)

    board_before: dict[str, str] = {}
    board_ready: dict[str, str] = {}
    board_after: dict[str, str] = {}
    iq_bytes = b""
    capture_stderr = ""
    capture_error = None
    burst = None
    restore_error = None

    try:
        board_before = read_ad9361_state(runner)
        if cfg.configure_rf:
            configure_ad9361(
                runner,
                rx_gain_db=cfg.rx_gain_db,
                tx_attenuation_db=cfg.tx_attenuation_db,
                settle_ms=cfg.settle_ms,
            )
        board_ready = read_ad9361_state(runner)
        try:
            iq_bytes, capture_stderr, burst = capture_with_trigger(
                iio_readdev_bin=iio_readdev_bin,
                cfg=cfg,
                io=io,
            )
        except CaptureReadError as exc:
            iq_bytes = exc.stdout_bytes
            capture_stderr = exc.stderr_text
            burst = exc.burst_payload
            capture_error = {
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        except Exception as exc:
            capture_error = {
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
    finally:
        try:
            if cfg.restore_rf and board_before:
                restore_rf_state(runner, board_before)
        except Exception as exc:  # pragma: no cover - best effort
            restore_error = f"{type(exc).__name__}: {exc}"
        try:
            board_after = read_ad9361_state(runner)
        finally:
            io.close()

    metrics = None
    if iq_bytes and args.out_iq is not None:
        write_bytes(args.out_iq.resolve(), iq_bytes)

    if iq_bytes:
        iq_pairs = parse_capture_bytes(iq_bytes)
        metrics = analyze_capture(
            iq_pairs,
            sample_rate_hz=cfg.sample_rate_hz,
            trigger_delay_ms=cfg.trigger_delay_ms,
            window_samples=min(DEFAULT_WINDOW_SAMPLES, max(cfg.sample_count // 32, 1024)),
        )

    payload = {
        "timestamp_utc": iso_now(),
        "config": asdict(cfg),
        "iio_readdev_bin": str(iio_readdev_bin),
        "board_before": board_before,
        "board_ready": board_ready,
        "board_after": board_after,
        "restore_error": restore_error,
        "capture": {
            "byte_count": len(iq_bytes),
            "int16_count": int(len(iq_bytes) // 2),
            "stderr": capture_stderr.strip(),
            "error": capture_error,
            "out_iq": None if args.out_iq is None else str(args.out_iq.resolve()),
        },
        "burst": burst,
        "metrics": metrics,
    }

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Wrote {args.json_out}")
    print(f"Capture bytes: {len(iq_bytes)}")
    if metrics is None:
        print(f"Capture error: {capture_error['error'] if capture_error else 'none'}")
    else:
        print(f"Energy event detected: {metrics['energy_event_detected']}")
        print(f"Peak window minus trigger: {metrics['peak_minus_trigger_ms']} ms")
    if burst is not None:
        print(f"Burst helper ok: {burst.get('ok')}")
        if burst.get("result") is not None:
            print(f"Received bits: {burst['result']['received_bits']}")


if __name__ == "__main__":
    main()
