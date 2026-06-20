#!/usr/bin/env python3
"""Lab 11.8 - PS-side axi_gpreg bring-up for the AD9361 BPSK overlay."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from lab_11_7_axi_lite_bpsk_bringup import (
    DevMemRegisterIo,
    MmapRegisterIo,
    ParamikoCommandRunner,
    RegisterIo,
    SshDevMemRegisterIo,
    parse_int,
)


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FRAME_BIT_COUNT = 281
DEFAULT_PREAMBLE_COUNT = 25
DEFAULT_START_OFFSET = 62
DEFAULT_START_HOLD_MS = 5
DEFAULT_POLL_LIMIT = 128
DEFAULT_POLL_DELAY_MS = 20
DEFAULT_EXPECTED_ID = 0x4250534B
DEFAULT_BASE_ADDR = 0x79040000


@dataclass(frozen=True)
class RegisterMap:
    core_version: int = 0x000
    core_id: int = 0x004
    scratch: int = 0x008
    gp_control_out: int = 0x404
    gp_status_in: int = 0x408
    gp_frame_bit_count_out: int = 0x444
    gp_received_bits_in: int = 0x448
    gp_preamble_count_out: int = 0x484
    gp_total_errors_in: int = 0x488
    gp_start_offset_out: int = 0x4C4
    gp_payload_errors_in: int = 0x4C8
    gp_signature_in: int = 0x508
    start_mask: int = 0x0000_0001
    clear_done_mask: int = 0x0000_0002
    status_start_mask: int = 0x0000_0001
    status_busy_mask: int = 0x0000_0002
    status_done_mask: int = 0x0000_0004
    status_timeout_mask: int = 0x0000_0008


REGS = RegisterMap()


class BringupTimeoutError(TimeoutError):
    """Timeout with the last observed status trace for post-mortem debugging."""

    def __init__(
        self,
        message: str,
        *,
        poll_reads: int,
        last_status: int,
        status_trace: list[int],
    ) -> None:
        super().__init__(message)
        self.poll_reads = poll_reads
        self.last_status = last_status
        self.status_trace = list(status_trace)


@dataclass(frozen=True)
class BringupConfig:
    backend: str
    base_addr: int
    frame_bit_count: int
    preamble_count: int
    start_offset: int
    start_hold_ms: int
    poll_limit: int
    poll_delay_ms: int
    expected_id: int
    clear_done: bool
    max_total_errors: int | None
    max_payload_errors: int | None


@dataclass(frozen=True)
class BringupResult:
    backend: str
    base_addr: int
    id_word: int
    signature_word: int
    initial_status: int
    final_status: int
    cleared_status: int
    done_cleared: bool
    busy_observed: bool
    done_observed: bool
    timed_out_observed: bool
    completed_by_timeout: bool
    poll_reads: int
    frame_bit_count: int
    preamble_count: int
    start_offset: int
    received_bits: int
    total_errors: int
    payload_errors: int
    ber_total: float
    ber_payload: float
    register_snapshot: dict[str, dict[str, int | str]]


def register_snapshot(io: RegisterIo, base_addr: int) -> dict[str, dict[str, int | str]]:
    items = (
        ("CORE_VERSION", REGS.core_version),
        ("CORE_ID", REGS.core_id),
        ("SCRATCH", REGS.scratch),
        ("GP_CONTROL_OUT", REGS.gp_control_out),
        ("GP_STATUS_IN", REGS.gp_status_in),
        ("GP_FRAME_BIT_COUNT_OUT", REGS.gp_frame_bit_count_out),
        ("GP_RECEIVED_BITS_IN", REGS.gp_received_bits_in),
        ("GP_PREAMBLE_COUNT_OUT", REGS.gp_preamble_count_out),
        ("GP_TOTAL_ERRORS_IN", REGS.gp_total_errors_in),
        ("GP_START_OFFSET_OUT", REGS.gp_start_offset_out),
        ("GP_PAYLOAD_ERRORS_IN", REGS.gp_payload_errors_in),
        ("GP_SIGNATURE_IN", REGS.gp_signature_in),
    )
    snapshot: dict[str, dict[str, int | str]] = {}
    for name, offset in items:
        snapshot[name] = {
            "offset": offset,
            "address": f"0x{base_addr + offset:08X}",
            "value": io.read32(offset),
        }
    return snapshot


class MockRegisterIo:
    """Small CI-friendly model of the gpreg-based control plane."""

    def __init__(
        self,
        *,
        busy_reads_before_done: int = 3,
        total_errors: int = 0,
        payload_errors: int = 0,
    ) -> None:
        self._busy_reads_before_done = max(busy_reads_before_done, 0)
        self._busy_reads_remaining = 0
        self._busy = False
        self._done = False
        self._control_word = 0
        self._total_errors = total_errors
        self._payload_errors = payload_errors
        self.regs = {
            REGS.core_version: 0x0004_0063,
            REGS.core_id: DEFAULT_EXPECTED_ID,
            REGS.scratch: 0,
            REGS.gp_control_out: 0,
            REGS.gp_status_in: 0,
            REGS.gp_frame_bit_count_out: 0,
            REGS.gp_received_bits_in: 0,
            REGS.gp_preamble_count_out: 0,
            REGS.gp_total_errors_in: 0,
            REGS.gp_start_offset_out: 0,
            REGS.gp_payload_errors_in: 0,
            REGS.gp_signature_in: DEFAULT_EXPECTED_ID,
        }

    def _compose_status(self) -> int:
        status = 8 << 8
        if self._control_word & REGS.start_mask:
            status |= REGS.status_start_mask
        if self._busy:
            status |= REGS.status_busy_mask
        if self._done:
            status |= REGS.status_done_mask
        return status

    def _complete_run(self) -> None:
        self._busy = False
        self._done = True
        self.regs[REGS.gp_received_bits_in] = self.regs[REGS.gp_frame_bit_count_out]
        self.regs[REGS.gp_total_errors_in] = self._total_errors
        self.regs[REGS.gp_payload_errors_in] = self._payload_errors

    def read32(self, offset: int) -> int:
        if offset == REGS.gp_status_in and self._busy:
            if self._busy_reads_remaining > 0:
                self._busy_reads_remaining -= 1
            if self._busy_reads_remaining == 0:
                self._complete_run()
        if offset == REGS.gp_status_in:
            self.regs[offset] = self._compose_status()
        return self.regs[offset]

    def write32(self, offset: int, value: int) -> None:
        value &= 0xFFFF_FFFF
        previous = self.regs.get(offset, 0)
        self.regs[offset] = value
        if offset != REGS.gp_control_out:
            return

        self._control_word = value
        if (value & REGS.start_mask) and not (previous & REGS.start_mask):
            self._busy = True
            self._done = False
            self._busy_reads_remaining = self._busy_reads_before_done
            self.regs[REGS.gp_received_bits_in] = 0
            self.regs[REGS.gp_total_errors_in] = 0
            self.regs[REGS.gp_payload_errors_in] = 0
        if (value & REGS.clear_done_mask) and not (previous & REGS.clear_done_mask):
            self._done = False

    def close(self) -> None:
        return None


def build_backend(args: argparse.Namespace) -> RegisterIo:
    if args.backend == "mock":
        return MockRegisterIo()
    if args.backend == "mmap":
        return MmapRegisterIo(args.base_addr)
    if args.backend == "devmem":
        return DevMemRegisterIo(args.base_addr)
    if args.backend == "ssh-devmem":
        key_path = Path(args.ssh_key).expanduser().resolve() if args.ssh_key else None
        runner = ParamikoCommandRunner(
            host=args.ssh_host,
            user=args.ssh_user,
            password=args.ssh_password,
            port=args.ssh_port,
            key_path=key_path,
            timeout_s=args.ssh_timeout_s,
        )
        return SshDevMemRegisterIo(args.base_addr, command_runner=runner)
    raise ValueError(f"Unsupported backend: {args.backend}")


def run_bringup(io: RegisterIo, cfg: BringupConfig) -> BringupResult:
    id_word = io.read32(REGS.core_id)
    if id_word != cfg.expected_id:
        raise RuntimeError(
            f"Unexpected axi_gpreg ID 0x{id_word:08X}; expected 0x{cfg.expected_id:08X}."
        )

    signature_word = io.read32(REGS.gp_signature_in)
    if signature_word != cfg.expected_id:
        raise RuntimeError(
            f"Unexpected bridge signature 0x{signature_word:08X}; expected 0x{cfg.expected_id:08X}."
        )

    initial_status = io.read32(REGS.gp_status_in)
    io.write32(REGS.gp_frame_bit_count_out, cfg.frame_bit_count)
    io.write32(REGS.gp_preamble_count_out, cfg.preamble_count)
    io.write32(REGS.gp_start_offset_out, cfg.start_offset)
    io.write32(REGS.gp_control_out, 0)
    io.write32(REGS.gp_control_out, REGS.start_mask)
    if cfg.start_hold_ms:
        time.sleep(cfg.start_hold_ms / 1000.0)
    io.write32(REGS.gp_control_out, 0)

    busy_observed = False
    done_observed = False
    timed_out_observed = False
    completed_by_timeout = False
    final_status = initial_status
    poll_reads = 0
    status_trace: list[int] = []
    for poll_reads in range(1, cfg.poll_limit + 1):
        final_status = io.read32(REGS.gp_status_in)
        status_trace.append(final_status)
        if final_status & REGS.status_busy_mask:
            busy_observed = True
        if final_status & REGS.status_timeout_mask:
            timed_out_observed = True
        if final_status & REGS.status_done_mask:
            done_observed = True
            break
        if timed_out_observed and (final_status & REGS.status_busy_mask) == 0:
            completed_by_timeout = True
            break
        if cfg.poll_delay_ms:
            time.sleep(cfg.poll_delay_ms / 1000.0)

    if not done_observed and not completed_by_timeout:
        raise BringupTimeoutError(
            f"Timed out after {cfg.poll_limit} polls: GP status never asserted done at 0x{cfg.base_addr:08X}.",
            poll_reads=cfg.poll_limit,
            last_status=final_status,
            status_trace=status_trace,
        )

    received_bits = io.read32(REGS.gp_received_bits_in)
    total_errors = io.read32(REGS.gp_total_errors_in)
    payload_errors = io.read32(REGS.gp_payload_errors_in)

    if cfg.max_total_errors is not None and total_errors > cfg.max_total_errors:
        raise RuntimeError(
            f"Observed total_errors={total_errors}, above allowed limit {cfg.max_total_errors}."
        )
    if cfg.max_payload_errors is not None and payload_errors > cfg.max_payload_errors:
        raise RuntimeError(
            f"Observed payload_errors={payload_errors}, above allowed limit {cfg.max_payload_errors}."
        )

    cleared_status = final_status
    done_cleared = False
    if cfg.clear_done:
        io.write32(REGS.gp_control_out, REGS.clear_done_mask)
        io.write32(REGS.gp_control_out, 0)
        cleared_status = io.read32(REGS.gp_status_in)
        done_cleared = (cleared_status & REGS.status_done_mask) == 0

    payload_bit_count = max(cfg.frame_bit_count - cfg.preamble_count, 1)
    return BringupResult(
        backend=cfg.backend,
        base_addr=cfg.base_addr,
        id_word=id_word,
        signature_word=signature_word,
        initial_status=initial_status,
        final_status=final_status,
        cleared_status=cleared_status,
        done_cleared=done_cleared,
        busy_observed=busy_observed,
        done_observed=done_observed,
        timed_out_observed=timed_out_observed,
        completed_by_timeout=completed_by_timeout,
        poll_reads=poll_reads,
        frame_bit_count=cfg.frame_bit_count,
        preamble_count=cfg.preamble_count,
        start_offset=cfg.start_offset,
        received_bits=received_bits,
        total_errors=total_errors,
        payload_errors=payload_errors,
        ber_total=total_errors / max(cfg.frame_bit_count, 1),
        ber_payload=payload_errors / payload_bit_count,
        register_snapshot=register_snapshot(io, cfg.base_addr),
    )


def write_json_report(path: Path, result: BringupResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(result)
    payload["base_addr"] = f"0x{result.base_addr:08X}"
    payload["id_word"] = f"0x{result.id_word:08X}"
    payload["signature_word"] = f"0x{result.signature_word:08X}"
    payload["initial_status"] = f"0x{result.initial_status:08X}"
    payload["final_status"] = f"0x{result.final_status:08X}"
    payload["cleared_status"] = f"0x{result.cleared_status:08X}"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_failure_json_report(
    path: Path,
    *,
    io: RegisterIo,
    cfg: BringupConfig,
    exc: Exception,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "ok": False,
        "backend": cfg.backend,
        "base_addr": f"0x{cfg.base_addr:08X}",
        "frame_bit_count": cfg.frame_bit_count,
        "preamble_count": cfg.preamble_count,
        "start_offset": cfg.start_offset,
        "error_type": type(exc).__name__,
        "error": str(exc),
    }

    poll_reads = getattr(exc, "poll_reads", None)
    if poll_reads is not None:
        payload["poll_reads"] = int(poll_reads)

    last_status = getattr(exc, "last_status", None)
    if last_status is not None:
        payload["last_status"] = f"0x{int(last_status):08X}"

    status_trace = getattr(exc, "status_trace", None)
    if status_trace is not None:
        payload["status_trace"] = [f"0x{int(status):08X}" for status in status_trace]

    try:
        payload["register_snapshot"] = register_snapshot(io, cfg.base_addr)
    except Exception as snapshot_exc:  # pragma: no cover - best effort only
        payload["register_snapshot_error"] = str(snapshot_exc)

    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("mock", "mmap", "devmem", "ssh-devmem"), default="mock")
    parser.add_argument("--base-addr", type=parse_int, default=DEFAULT_BASE_ADDR)
    parser.add_argument("--frame-bit-count", type=int, default=DEFAULT_FRAME_BIT_COUNT)
    parser.add_argument("--preamble-count", type=int, default=DEFAULT_PREAMBLE_COUNT)
    parser.add_argument("--start-offset", type=int, default=DEFAULT_START_OFFSET)
    parser.add_argument("--start-hold-ms", type=int, default=DEFAULT_START_HOLD_MS)
    parser.add_argument("--poll-limit", type=int, default=DEFAULT_POLL_LIMIT)
    parser.add_argument("--poll-delay-ms", type=int, default=DEFAULT_POLL_DELAY_MS)
    parser.add_argument("--expected-id", type=parse_int, default=DEFAULT_EXPECTED_ID)
    parser.add_argument("--clear-done", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--max-total-errors", type=int, default=0)
    parser.add_argument("--max-payload-errors", type=int, default=0)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--ssh-host", default="192.168.40.1")
    parser.add_argument("--ssh-user", default="root")
    parser.add_argument("--ssh-password", default="analog")
    parser.add_argument("--ssh-port", type=int, default=22)
    parser.add_argument("--ssh-key")
    parser.add_argument("--ssh-timeout-s", type=float, default=10.0)
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    cfg = BringupConfig(
        backend=args.backend,
        base_addr=args.base_addr,
        frame_bit_count=args.frame_bit_count,
        preamble_count=args.preamble_count,
        start_offset=args.start_offset,
        start_hold_ms=args.start_hold_ms,
        poll_limit=args.poll_limit,
        poll_delay_ms=args.poll_delay_ms,
        expected_id=args.expected_id,
        clear_done=args.clear_done,
        max_total_errors=args.max_total_errors,
        max_payload_errors=args.max_payload_errors,
    )
    io = build_backend(args)
    try:
        result = run_bringup(io, cfg)
    except Exception as exc:
        if args.json_out is not None:
            write_failure_json_report(args.json_out, io=io, cfg=cfg, exc=exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
    finally:
        io.close()

    if args.json_out is not None:
        write_json_report(args.json_out, result)

    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    main()
