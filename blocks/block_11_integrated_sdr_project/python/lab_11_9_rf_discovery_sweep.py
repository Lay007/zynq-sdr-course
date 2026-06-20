#!/usr/bin/env python3
"""Lab 11.9 - RF discovery sweep for the AD9361 gpreg BPSK overlay."""

from __future__ import annotations

import argparse
import json
import shlex
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from lab_11_7_axi_lite_bpsk_bringup import ParamikoCommandRunner, parse_int
from lab_11_8_axi_gpreg_bpsk_bringup import (
    BringupConfig,
    BringupResult,
    BringupTimeoutError,
    SshDevMemRegisterIo,
    run_bringup,
)


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_JSON_OUT = ROOT / "docs" / "assets" / "lab119_rf_discovery_sweep_live.json"
DEFAULT_HOST = "192.168.40.1"
DEFAULT_USER = "root"
DEFAULT_PASSWORD = "analog"
DEFAULT_PORT = 22
DEFAULT_TIMEOUT_S = 10.0
DEFAULT_BASE_ADDR = 0x79040000
DEFAULT_FRAME_BIT_COUNT = 281
DEFAULT_PREAMBLE_COUNT = 25
DEFAULT_POLL_LIMIT = 128
DEFAULT_POLL_DELAY_MS = 20
DEFAULT_START_HOLD_MS = 5
DEFAULT_START_OFFSETS = "48,54,58,62,66,70,74"
DEFAULT_RX_GAINS_DB = "10,20,30"
DEFAULT_TX_ATTENUATIONS_DB = "-80,-70,-60"
DEFAULT_SETTLE_MS = 50


@dataclass(frozen=True)
class SweepConfig:
    host: str
    user: str
    port: int
    base_addr: int
    frame_bit_count: int
    preamble_count: int
    poll_limit: int
    poll_delay_ms: int
    start_hold_ms: int
    start_offsets: list[int]
    rx_gains_db: list[float]
    tx_attenuations_db: list[float]
    settle_ms: int


@dataclass(frozen=True)
class SweepAttempt:
    start_offset: int
    rx_gain_db: float
    tx_attenuation_db: float
    ok: bool
    error_type: str | None
    error: str | None
    score: list[float]
    result: dict[str, object] | None


def parse_number_list(text: str, *, cast: type[int] | type[float]) -> list[int] | list[float]:
    values: list[int] | list[float] = []
    for token in text.split(","):
        stripped = token.strip()
        if not stripped:
            continue
        values.append(cast(stripped))
    if not values:
        raise ValueError("Expected at least one sweep value.")
    return values


def run_remote(runner: ParamikoCommandRunner, command: str, *, context: str) -> str:
    returncode, stdout, stderr = runner(command)
    if returncode != 0:
        details = stderr.strip() or stdout.strip() or "no diagnostic output"
        raise RuntimeError(f"{context} failed with exit code {returncode}: {details}")
    return stdout.strip()


def write_remote_value(runner: ParamikoCommandRunner, path: str, value: str) -> None:
    quoted = shlex.quote(value)
    run_remote(runner, f"printf %s {quoted} > {shlex.quote(path)}", context=f"write {path}")


def configure_ad9361(
    runner: ParamikoCommandRunner,
    *,
    rx_gain_db: float,
    tx_attenuation_db: float,
    settle_ms: int,
) -> None:
    writes = {
        "/sys/bus/iio/devices/iio:device0/out_altvoltage1_TX_LO_powerdown": "0",
        "/sys/bus/iio/devices/iio:device0/in_voltage0_gain_control_mode": "manual",
        "/sys/bus/iio/devices/iio:device0/in_voltage1_gain_control_mode": "manual",
        "/sys/bus/iio/devices/iio:device0/in_voltage0_hardwaregain": f"{rx_gain_db:g}",
        "/sys/bus/iio/devices/iio:device0/in_voltage1_hardwaregain": f"{rx_gain_db:g}",
        "/sys/bus/iio/devices/iio:device0/out_voltage0_hardwaregain": f"{tx_attenuation_db:g}",
        "/sys/bus/iio/devices/iio:device0/out_voltage1_hardwaregain": f"{tx_attenuation_db:g}",
    }
    for path, value in writes.items():
        write_remote_value(runner, path, value)
    if settle_ms > 0:
        time.sleep(settle_ms / 1000.0)


def read_ad9361_state(runner: ParamikoCommandRunner) -> dict[str, str]:
    fields = {
        "model": "tr -d '\\0' </proc/device-tree/model; echo",
        "rx_lo_hz": "cat /sys/bus/iio/devices/iio:device0/out_altvoltage0_RX_LO_frequency; echo",
        "tx_lo_hz": "cat /sys/bus/iio/devices/iio:device0/out_altvoltage1_TX_LO_frequency; echo",
        "rx_sample_rate_hz": "cat /sys/bus/iio/devices/iio:device0/in_voltage_sampling_frequency; echo",
        "tx_sample_rate_hz": "cat /sys/bus/iio/devices/iio:device0/out_voltage_sampling_frequency; echo",
        "rx_gain_mode_ch0": "cat /sys/bus/iio/devices/iio:device0/in_voltage0_gain_control_mode; echo",
        "rx_gain_mode_ch1": "cat /sys/bus/iio/devices/iio:device0/in_voltage1_gain_control_mode; echo",
        "rx_gain_db_ch0": "cat /sys/bus/iio/devices/iio:device0/in_voltage0_hardwaregain; echo",
        "rx_gain_db_ch1": "cat /sys/bus/iio/devices/iio:device0/in_voltage1_hardwaregain; echo",
        "tx_attenuation_db_ch0": "cat /sys/bus/iio/devices/iio:device0/out_voltage0_hardwaregain; echo",
        "tx_attenuation_db_ch1": "cat /sys/bus/iio/devices/iio:device0/out_voltage1_hardwaregain; echo",
        "tx_lo_powerdown": "cat /sys/bus/iio/devices/iio:device0/out_altvoltage1_TX_LO_powerdown; echo",
    }
    state: dict[str, str] = {}
    for key, command in fields.items():
        state[key] = run_remote(runner, command, context=f"read {key}")
    return state


def attempt_score(result: BringupResult) -> list[float]:
    return [
        float(result.received_bits),
        float(not result.timed_out_observed),
        float(result.done_observed),
        float(-result.total_errors),
        float(-result.payload_errors),
    ]


def run_attempt(io: SshDevMemRegisterIo, cfg: SweepConfig, *, start_offset: int) -> BringupResult:
    bringup_cfg = BringupConfig(
        backend="ssh-devmem",
        base_addr=cfg.base_addr,
        frame_bit_count=cfg.frame_bit_count,
        preamble_count=cfg.preamble_count,
        start_offset=start_offset,
        start_hold_ms=cfg.start_hold_ms,
        poll_limit=cfg.poll_limit,
        poll_delay_ms=cfg.poll_delay_ms,
        expected_id=0x4250534B,
        clear_done=True,
        max_total_errors=None,
        max_payload_errors=None,
    )
    return run_bringup(io, bringup_cfg)


def summarize_best_attempt(attempts: list[SweepAttempt]) -> dict[str, object] | None:
    successful = [attempt for attempt in attempts if attempt.ok and attempt.result is not None]
    if not successful:
        return None
    best = max(successful, key=lambda attempt: tuple(attempt.score))
    return asdict(best)


def build_summary(attempts: list[SweepAttempt]) -> dict[str, object]:
    successful = [attempt for attempt in attempts if attempt.ok and attempt.result is not None]
    nonzero_received = [
        attempt for attempt in successful if int(attempt.result["received_bits"]) > 0
    ]
    timeout_observed = [
        attempt for attempt in successful if bool(attempt.result["timed_out_observed"])
    ]
    return {
        "attempt_count": len(attempts),
        "successful_attempt_count": len(successful),
        "nonzero_received_bits_attempt_count": len(nonzero_received),
        "timeout_observed_attempt_count": len(timeout_observed),
        "max_received_bits": max(
            (int(attempt.result["received_bits"]) for attempt in successful),
            default=0,
        ),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-host", default=DEFAULT_HOST)
    parser.add_argument("--ssh-user", default=DEFAULT_USER)
    parser.add_argument("--ssh-password", default=DEFAULT_PASSWORD)
    parser.add_argument("--ssh-port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--ssh-timeout-s", type=float, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--base-addr", type=parse_int, default=DEFAULT_BASE_ADDR)
    parser.add_argument("--frame-bit-count", type=int, default=DEFAULT_FRAME_BIT_COUNT)
    parser.add_argument("--preamble-count", type=int, default=DEFAULT_PREAMBLE_COUNT)
    parser.add_argument("--poll-limit", type=int, default=DEFAULT_POLL_LIMIT)
    parser.add_argument("--poll-delay-ms", type=int, default=DEFAULT_POLL_DELAY_MS)
    parser.add_argument("--start-hold-ms", type=int, default=DEFAULT_START_HOLD_MS)
    parser.add_argument("--start-offsets", default=DEFAULT_START_OFFSETS)
    parser.add_argument("--rx-gains-db", default=DEFAULT_RX_GAINS_DB)
    parser.add_argument("--tx-attenuations-db", default=DEFAULT_TX_ATTENUATIONS_DB)
    parser.add_argument("--settle-ms", type=int, default=DEFAULT_SETTLE_MS)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    cfg = SweepConfig(
        host=args.ssh_host,
        user=args.ssh_user,
        port=args.ssh_port,
        base_addr=args.base_addr,
        frame_bit_count=args.frame_bit_count,
        preamble_count=args.preamble_count,
        poll_limit=args.poll_limit,
        poll_delay_ms=args.poll_delay_ms,
        start_hold_ms=args.start_hold_ms,
        start_offsets=list(parse_number_list(args.start_offsets, cast=int)),
        rx_gains_db=list(parse_number_list(args.rx_gains_db, cast=float)),
        tx_attenuations_db=list(parse_number_list(args.tx_attenuations_db, cast=float)),
        settle_ms=args.settle_ms,
    )

    runner = ParamikoCommandRunner(
        host=args.ssh_host,
        user=args.ssh_user,
        password=args.ssh_password,
        port=args.ssh_port,
        key_path=None,
        timeout_s=args.ssh_timeout_s,
    )
    io = SshDevMemRegisterIo(args.base_addr, command_runner=runner)
    attempts: list[SweepAttempt] = []
    board_before: dict[str, str] = {}
    board_after: dict[str, str] = {}

    try:
        board_before = read_ad9361_state(runner)
        for tx_attenuation_db in cfg.tx_attenuations_db:
            for rx_gain_db in cfg.rx_gains_db:
                configure_ad9361(
                    runner,
                    rx_gain_db=rx_gain_db,
                    tx_attenuation_db=tx_attenuation_db,
                    settle_ms=cfg.settle_ms,
                )
                for start_offset in cfg.start_offsets:
                    try:
                        result = run_attempt(io, cfg, start_offset=start_offset)
                        attempts.append(
                            SweepAttempt(
                                start_offset=start_offset,
                                rx_gain_db=rx_gain_db,
                                tx_attenuation_db=tx_attenuation_db,
                                ok=True,
                                error_type=None,
                                error=None,
                                score=attempt_score(result),
                                result=asdict(result),
                            )
                        )
                    except BringupTimeoutError as exc:
                        attempts.append(
                            SweepAttempt(
                                start_offset=start_offset,
                                rx_gain_db=rx_gain_db,
                                tx_attenuation_db=tx_attenuation_db,
                                ok=False,
                                error_type=type(exc).__name__,
                                error=str(exc),
                                score=[-1.0],
                                result={
                                    "poll_reads": exc.poll_reads,
                                    "last_status": f"0x{exc.last_status:08X}",
                                    "status_trace": [f"0x{status:08X}" for status in exc.status_trace],
                                },
                            )
                        )
                    except Exception as exc:
                        attempts.append(
                            SweepAttempt(
                                start_offset=start_offset,
                                rx_gain_db=rx_gain_db,
                                tx_attenuation_db=tx_attenuation_db,
                                ok=False,
                                error_type=type(exc).__name__,
                                error=str(exc),
                                score=[-1.0],
                                result=None,
                            )
                        )
        board_after = read_ad9361_state(runner)
    finally:
        io.close()

    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config": asdict(cfg),
        "board_before": board_before,
        "board_after": board_after,
        "summary": build_summary(attempts),
        "best_attempt": summarize_best_attempt(attempts),
        "attempts": [asdict(attempt) for attempt in attempts],
    }
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    best_attempt = payload["best_attempt"]
    print(f"Wrote {args.json_out}")
    print(f"Attempts: {len(attempts)}")
    if best_attempt is None:
        print("Best attempt: none")
    else:
        print(json.dumps(best_attempt, indent=2))


if __name__ == "__main__":
    main()
