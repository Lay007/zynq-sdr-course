#!/usr/bin/env python3
"""Lab 11.8 - PS-side axi_gpreg bring-up for the AD9361 BPSK overlay."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from bench_config import DEFAULT_HOST, DEFAULT_PASSWORD, DEFAULT_PORT, DEFAULT_TIMEOUT_S, DEFAULT_USER
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
DEFAULT_RX_DECISION_MODE = "i"


RX_DECISION_MODE_MAP: dict[str, int] = {
    "i": 0,
    "neg-i": 1,
    "neg_i": 1,
    "-i": 1,
    "q": 2,
    "neg-q": 3,
    "neg_q": 3,
    "-q": 3,
}


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
    gp_error_counts_in: int = 0x488
    gp_start_offset_out: int = 0x4C4
    gp_adc_input_debug_in: int = 0x4C8
    gp_signature_in: int = 0x508
    gp_tx_valid_count_in: int = 0x548
    gp_rx_valid_count_in: int = 0x588
    gp_capture_debug_in: int = 0x5C8
    start_mask: int = 0x0000_0001
    clear_done_mask: int = 0x0000_0002
    decision_mode_shift: int = 2
    decision_mode_mask: int = 0x0000_000C
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
    rx_decision_mode: int
    start_hold_ms: int
    poll_limit: int
    poll_delay_ms: int
    expected_id: int
    clear_done: bool
    max_total_errors: int | None
    max_payload_errors: int | None
    # Extra gp_ctrl bits OR'd into the control word above the decision-mode field
    # (bits [3:2]). 0x10 = gp_ctrl[4] selects the QPSK core in the dual-modem
    # bridge; 0 keeps the BPSK path bit-identical.
    mod_select_bits: int = 0


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
    rx_decision_mode: int
    rx_decision_mode_name: str
    received_bits: int
    total_errors: int
    payload_errors: int
    tx_valid_count: int
    rx_valid_count: int
    adc_input_debug_word: int | None
    adc_input_debug: dict[str, int | bool] | None
    adc_input_debug_error: dict[str, str] | None
    adc_input_state_word: int | None
    adc_input_state: dict[str, int | bool] | None
    adc_input_state_error: dict[str, str] | None
    capture_debug_word: int | None
    capture_debug: dict[str, int | bool] | None
    capture_debug_error: dict[str, str] | None
    rx_decision_debug_word: int | None
    rx_decision_debug: dict[str, int | bool] | None
    rx_decision_debug_error: dict[str, str] | None
    ber_total: float
    ber_payload: float
    register_snapshot: dict[str, dict[str, int | str]]


def decode_capture_debug(word: int) -> dict[str, int | bool]:
    word &= 0xFFFF_FFFF
    return {
        "capture_valid_seen_any": bool((word >> 31) & 0x1),
        "capture_nonzero_seen_any": bool((word >> 30) & 0x1),
        "capture_valid_while_active_seen_any": bool((word >> 29) & 0x1),
        "capture_i_negative_seen_any": bool((word >> 28) & 0x1),
        "capture_q_negative_seen_any": bool((word >> 27) & 0x1),
        "capture_valid_count_lsb13": (word >> 14) & 0x1FFF,
        "capture_peak_abs_max_q14": word & 0x3FFF,
    }


def decode_adc_input_debug(word: int) -> dict[str, int | bool]:
    word &= 0xFFFF_FFFF
    return {
        "adc_input_valid_seen_any": bool((word >> 31) & 0x1),
        "adc_input_nonzero_seen_any": bool((word >> 30) & 0x1),
        "adc_input_enable_seen_any": bool((word >> 29) & 0x1),
        "adc_input_reset_asserted_current": bool((word >> 28) & 0x1),
        "adc_input_clk_counter_lsb16": (word >> 12) & 0xFFFF,
        "adc_input_valid_count_lsb12": word & 0x0FFF,
    }


def decode_rx_decision_debug(word: int) -> dict[str, int | bool]:
    word &= 0xFFFF_FFFF
    return {
        "recovered_valid_seen_any": bool((word >> 31) & 0x1),
        "recovered_one_seen_any": bool((word >> 30) & 0x1),
        "decision_negative_seen_any": bool((word >> 29) & 0x1),
        "decision_nonzero_seen_any": bool((word >> 28) & 0x1),
        "recovered_valid_count_lsb8": (word >> 20) & 0xFF,
        "recovered_one_count_lsb8": (word >> 12) & 0xFF,
        "tx_valid_count_lsb12": word & 0x0FFF,
    }


def parse_rx_decision_mode(value: str) -> int:
    key = value.strip().lower()
    if key not in RX_DECISION_MODE_MAP:
        valid = ", ".join(sorted({"i", "neg-i", "q", "neg-q"}))
        raise argparse.ArgumentTypeError(f"Unsupported rx decision mode `{value}`. Expected one of: {valid}.")
    return RX_DECISION_MODE_MAP[key]


def rx_decision_mode_name(mode: int) -> str:
    normalized = int(mode) & 0x3
    names = {
        0: "i",
        1: "neg-i",
        2: "q",
        3: "neg-q",
    }
    return names[normalized]


def read_optional_register(io: RegisterIo, offset: int) -> tuple[int | None, dict[str, str] | None]:
    try:
        return io.read32(offset), None
    except Exception as exc:
        return None, {
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


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
        ("GP_ERROR_COUNTS_IN", REGS.gp_error_counts_in),
        ("GP_START_OFFSET_OUT", REGS.gp_start_offset_out),
        ("GP_ADC_INPUT_DEBUG_IN", REGS.gp_adc_input_debug_in),
        ("GP_SIGNATURE_IN", REGS.gp_signature_in),
        ("GP_TX_VALID_COUNT_IN", REGS.gp_tx_valid_count_in),
        ("GP_RX_VALID_COUNT_IN", REGS.gp_rx_valid_count_in),
    )
    snapshot: dict[str, dict[str, int | str]] = {}
    for name, offset in items:
        snapshot[name] = {
            "offset": offset,
            "address": f"0x{base_addr + offset:08X}",
            "value": io.read32(offset),
        }
    optional_items = (("GP_CAPTURE_DEBUG_IN", REGS.gp_capture_debug_in),)
    for name, offset in optional_items:
        value, error = read_optional_register(io, offset)
        entry: dict[str, int | str] = {
            "offset": offset,
            "address": f"0x{base_addr + offset:08X}",
        }
        if value is not None:
            entry["value"] = value
        if error is not None:
            entry["error_type"] = error["error_type"]
            entry["error"] = error["error"]
        snapshot[name] = entry
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
            REGS.gp_error_counts_in: 0,
            REGS.gp_start_offset_out: 0,
            REGS.gp_adc_input_debug_in: 0,
            REGS.gp_signature_in: DEFAULT_EXPECTED_ID,
            REGS.gp_tx_valid_count_in: 0,
            REGS.gp_rx_valid_count_in: 0,
            REGS.gp_capture_debug_in: 0,
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
        self.regs[REGS.gp_error_counts_in] = (
            ((self._total_errors & 0xFFFF) << 16) | (self._payload_errors & 0xFFFF)
        )

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
            self.regs[REGS.gp_error_counts_in] = 0
            self.regs[REGS.gp_tx_valid_count_in] = self.regs[REGS.gp_frame_bit_count_out] * 8
            self.regs[REGS.gp_rx_valid_count_in] = self.regs[REGS.gp_frame_bit_count_out] * 8
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
    decision_mode_word = ((cfg.rx_decision_mode & 0x3) << REGS.decision_mode_shift) \
        | (cfg.mod_select_bits & 0xFFFF_FFF0)
    io.write32(REGS.gp_frame_bit_count_out, cfg.frame_bit_count)
    io.write32(REGS.gp_preamble_count_out, cfg.preamble_count)
    io.write32(REGS.gp_start_offset_out, cfg.start_offset)
    io.write32(REGS.gp_control_out, decision_mode_word)
    io.write32(REGS.gp_control_out, decision_mode_word | REGS.start_mask)
    if cfg.start_hold_ms:
        time.sleep(cfg.start_hold_ms / 1000.0)
    io.write32(REGS.gp_control_out, decision_mode_word)

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
    error_counts_word = io.read32(REGS.gp_error_counts_in)
    total_errors = (error_counts_word >> 16) & 0xFFFF
    payload_errors = error_counts_word & 0xFFFF
    tx_valid_count_word = io.read32(REGS.gp_tx_valid_count_in)
    tx_valid_count = tx_valid_count_word & 0x0FFF
    rx_valid_count = io.read32(REGS.gp_rx_valid_count_in)
    adc_input_debug_word, adc_input_debug_error = read_optional_register(io, REGS.gp_adc_input_debug_in)
    capture_debug_word, capture_debug_error = read_optional_register(io, REGS.gp_capture_debug_in)
    rx_decision_debug_word = tx_valid_count_word
    rx_decision_debug_error = None
    adc_input_debug = (
        decode_adc_input_debug(adc_input_debug_word)
        if adc_input_debug_word is not None
        else None
    )
    capture_debug = (
        decode_capture_debug(capture_debug_word)
        if capture_debug_word is not None
        else None
    )
    rx_decision_debug = (
        decode_rx_decision_debug(rx_decision_debug_word)
        if rx_decision_debug_word is not None
        else None
    )

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
        io.write32(REGS.gp_control_out, decision_mode_word | REGS.clear_done_mask)
        io.write32(REGS.gp_control_out, decision_mode_word)
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
        rx_decision_mode=(cfg.rx_decision_mode & 0x3),
        rx_decision_mode_name=rx_decision_mode_name(cfg.rx_decision_mode),
        received_bits=received_bits,
        total_errors=total_errors,
        payload_errors=payload_errors,
        tx_valid_count=tx_valid_count,
        rx_valid_count=rx_valid_count,
        adc_input_debug_word=adc_input_debug_word,
        adc_input_debug=adc_input_debug,
        adc_input_debug_error=adc_input_debug_error,
        adc_input_state_word=None,
        adc_input_state=None,
        adc_input_state_error=None,
        capture_debug_word=capture_debug_word,
        capture_debug=capture_debug,
        capture_debug_error=capture_debug_error,
        rx_decision_debug_word=rx_decision_debug_word,
        rx_decision_debug=rx_decision_debug,
        rx_decision_debug_error=rx_decision_debug_error,
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
    parser.add_argument("--rx-decision-mode", type=parse_rx_decision_mode, default=parse_rx_decision_mode(DEFAULT_RX_DECISION_MODE))
    parser.add_argument("--start-hold-ms", type=int, default=DEFAULT_START_HOLD_MS)
    parser.add_argument("--poll-limit", type=int, default=DEFAULT_POLL_LIMIT)
    parser.add_argument("--poll-delay-ms", type=int, default=DEFAULT_POLL_DELAY_MS)
    parser.add_argument("--expected-id", type=parse_int, default=DEFAULT_EXPECTED_ID)
    parser.add_argument("--clear-done", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--max-total-errors", type=int, default=0)
    parser.add_argument("--max-payload-errors", type=int, default=0)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--ssh-host", default=DEFAULT_HOST)
    parser.add_argument("--ssh-user", default=DEFAULT_USER)
    parser.add_argument("--ssh-password", default=DEFAULT_PASSWORD)
    parser.add_argument("--ssh-port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--ssh-key")
    parser.add_argument("--ssh-timeout-s", type=float, default=DEFAULT_TIMEOUT_S)
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
        rx_decision_mode=args.rx_decision_mode,
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
