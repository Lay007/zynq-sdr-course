#!/usr/bin/env python3
"""Lab 11.7 - PS-side AXI-Lite bring-up for the deterministic BPSK burst."""

from __future__ import annotations

import argparse
import json
import mmap
import os
import shlex
import struct
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FRAME_BIT_COUNT = 281
DEFAULT_PREAMBLE_COUNT = 25
DEFAULT_START_OFFSET = 62
DEFAULT_POLL_LIMIT = 128
DEFAULT_POLL_DELAY_MS = 20
DEFAULT_EXPECTED_ID = 0x4250534B
DEFAULT_MOCK_BASE_ADDR = 0x43C00000


class RegisterIo(Protocol):
    def read32(self, offset: int) -> int:
        """Read one 32-bit register at the given offset."""

    def write32(self, offset: int, value: int) -> None:
        """Write one 32-bit register at the given offset."""

    def close(self) -> None:
        """Release any underlying resources."""


class CommandRunner(Protocol):
    def __call__(self, command: str) -> tuple[int, str, str]:
        """Run one shell command and return (returncode, stdout, stderr)."""

    def close(self) -> None:
        """Release any underlying resources."""


@dataclass(frozen=True)
class RegisterMap:
    control_status: int = 0x00
    frame_bit_count: int = 0x04
    preamble_count: int = 0x08
    start_offset: int = 0x0C
    received_bits: int = 0x10
    total_errors: int = 0x14
    payload_errors: int = 0x18
    core_id: int = 0x1C
    start_mask: int = 0x0000_0001
    busy_mask: int = 0x0000_0002
    done_mask: int = 0x0000_0004


REGS = RegisterMap()


@dataclass(frozen=True)
class BringupConfig:
    backend: str
    base_addr: int
    frame_bit_count: int
    preamble_count: int
    start_offset: int
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
    initial_status: int
    final_status: int
    cleared_status: int
    done_cleared: bool
    busy_observed: bool
    done_observed: bool
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


def parse_int(value: str) -> int:
    return int(value, 0)


def parse_devmem_read_output(stdout: str) -> int:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("devmem returned no stdout to parse.")
    return int(lines[-1], 0)


def format_command_failure(context: str, returncode: int, stdout: str, stderr: str) -> str:
    details = stderr.strip() or stdout.strip() or "no diagnostic output"
    return f"{context} failed with exit code {returncode}: {details}"


def register_snapshot(io: RegisterIo, base_addr: int) -> dict[str, dict[str, int | str]]:
    items = (
        ("CONTROL_STATUS", REGS.control_status),
        ("FRAME_BIT_COUNT", REGS.frame_bit_count),
        ("PREAMBLE_COUNT", REGS.preamble_count),
        ("START_OFFSET", REGS.start_offset),
        ("RECEIVED_BITS", REGS.received_bits),
        ("TOTAL_ERRORS", REGS.total_errors),
        ("PAYLOAD_ERRORS", REGS.payload_errors),
        ("ID", REGS.core_id),
    )
    snapshot: dict[str, dict[str, int | str]] = {}
    for name, offset in items:
        address = base_addr + offset
        snapshot[name] = {
            "offset": offset,
            "address": f"0x{address:08X}",
            "value": io.read32(offset),
        }
    return snapshot


class DevMemRegisterIo:
    """Access AXI-Lite registers through the Linux `devmem` utility."""

    def __init__(self, base_addr: int, width_bits: int = 32) -> None:
        self.base_addr = base_addr
        self.width_bits = width_bits

    def _address(self, offset: int) -> int:
        return self.base_addr + offset

    def read32(self, offset: int) -> int:
        address = self._address(offset)
        proc = subprocess.run(
            ["devmem", f"0x{address:X}", str(self.width_bits)],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                format_command_failure(
                    f"devmem read at 0x{address:08X}",
                    proc.returncode,
                    proc.stdout,
                    proc.stderr,
                )
            )
        return parse_devmem_read_output(proc.stdout)

    def write32(self, offset: int, value: int) -> None:
        address = self._address(offset)
        proc = subprocess.run(
            ["devmem", f"0x{address:X}", str(self.width_bits), f"0x{value & 0xFFFFFFFF:X}"],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                format_command_failure(
                    f"devmem write at 0x{address:08X}",
                    proc.returncode,
                    proc.stdout,
                    proc.stderr,
                )
            )

    def close(self) -> None:
        return None


class ParamikoCommandRunner:
    """Small SSH command runner used by the host-side `ssh-devmem` backend."""

    def __init__(
        self,
        *,
        host: str,
        user: str,
        password: str | None,
        port: int,
        key_path: Path | None,
        timeout_s: float,
    ) -> None:
        try:
            import paramiko
        except ImportError as exc:  # pragma: no cover - exercised only when missing locally
            raise RuntimeError(
                "The ssh-devmem backend requires paramiko. Install dependencies from requirements.txt."
            ) from exc

        self._paramiko = paramiko
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connect_kwargs: dict[str, object] = {
            "hostname": host,
            "username": user,
            "port": port,
            "timeout": timeout_s,
        }
        if key_path is not None:
            connect_kwargs["key_filename"] = str(key_path)
        if password is not None:
            connect_kwargs["password"] = password
            connect_kwargs["look_for_keys"] = False
            connect_kwargs["allow_agent"] = False

        self.client.connect(**connect_kwargs)

    def __call__(self, command: str) -> tuple[int, str, str]:
        sentinel = "__CODEX_RC__:"
        wrapped = shlex.quote(f"{command}; rc=$?; printf '{sentinel}%d\\n' \"$rc\"")
        stdin, stdout, stderr = self.client.exec_command(f"sh -lc {wrapped}")
        del stdin
        stdout_text = stdout.read().decode("utf-8", errors="replace")
        stderr_text = stderr.read().decode("utf-8", errors="replace")
        lines = stdout_text.splitlines()
        returncode = stdout.channel.recv_exit_status()
        for index in range(len(lines) - 1, -1, -1):
            if lines[index].startswith(sentinel):
                returncode = int(lines[index].split(":", 1)[1])
                lines.pop(index)
                stdout_text = "\n".join(lines)
                if stdout_text:
                    stdout_text += "\n"
                break
        return (returncode, stdout_text, stderr_text)

    def close(self) -> None:
        self.client.close()


class SshDevMemRegisterIo:
    """Access AXI-Lite registers through remote Linux `devmem` over SSH."""

    def __init__(
        self,
        base_addr: int,
        *,
        width_bits: int = 32,
        command_runner: CommandRunner | None = None,
        host: str | None = None,
        user: str = "root",
        password: str | None = None,
        port: int = 22,
        key_path: Path | None = None,
        timeout_s: float = 10.0,
        devmem_bin: str = "/sbin/devmem",
    ) -> None:
        self.base_addr = base_addr
        self.width_bits = width_bits
        self.devmem_bin = devmem_bin
        self.runner = command_runner or ParamikoCommandRunner(
            host=host or "",
            user=user,
            password=password,
            port=port,
            key_path=key_path,
            timeout_s=timeout_s,
        )

    def _address(self, offset: int) -> int:
        return self.base_addr + offset

    def _run(self, argv: list[str], *, context: str) -> str:
        command = shlex.join(argv)
        returncode, stdout, stderr = self.runner(command)
        if returncode != 0:
            raise RuntimeError(format_command_failure(context, returncode, stdout, stderr))
        return stdout

    def read32(self, offset: int) -> int:
        address = self._address(offset)
        stdout = self._run(
            [self.devmem_bin, f"0x{address:X}", str(self.width_bits)],
            context=f"ssh-devmem read at 0x{address:08X}",
        )
        return parse_devmem_read_output(stdout)

    def write32(self, offset: int, value: int) -> None:
        address = self._address(offset)
        self._run(
            [self.devmem_bin, f"0x{address:X}", str(self.width_bits), f"0x{value & 0xFFFFFFFF:X}"],
            context=f"ssh-devmem write at 0x{address:08X}",
        )

    def close(self) -> None:
        self.runner.close()


class MmapRegisterIo:
    """Access AXI-Lite registers directly through `/dev/mem` on Linux."""

    def __init__(self, base_addr: int, region_size: int = 0x1000) -> None:
        if os.name == "nt":
            raise RuntimeError("The mmap backend requires Linux with /dev/mem access.")

        self.base_addr = base_addr
        self.region_size = region_size
        self.page_size = mmap.PAGESIZE
        self.page_base = base_addr & ~(self.page_size - 1)
        self.page_offset = base_addr - self.page_base
        self.map_size = self.page_offset + region_size

        self.fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
        self.mem = mmap.mmap(
            self.fd,
            self.map_size,
            flags=mmap.MAP_SHARED,
            prot=mmap.PROT_READ | mmap.PROT_WRITE,
            offset=self.page_base,
        )

    def _seek(self, offset: int) -> int:
        absolute = self.page_offset + offset
        if absolute < 0 or absolute + 4 > self.map_size:
            raise ValueError(f"Offset 0x{offset:X} is outside the mapped region.")
        return absolute

    def read32(self, offset: int) -> int:
        absolute = self._seek(offset)
        self.mem.seek(absolute)
        return struct.unpack("<I", self.mem.read(4))[0]

    def write32(self, offset: int, value: int) -> None:
        absolute = self._seek(offset)
        self.mem.seek(absolute)
        self.mem.write(struct.pack("<I", value & 0xFFFFFFFF))
        self.mem.flush()

    def close(self) -> None:
        self.mem.close()
        os.close(self.fd)


class MockRegisterIo:
    """Deterministic local model of the AXI-Lite wrapper for tests and dry runs."""

    def __init__(
        self,
        *,
        id_word: int = DEFAULT_EXPECTED_ID,
        busy_reads_before_done: int = 2,
        total_errors: int = 0,
        payload_errors: int = 0,
    ) -> None:
        self.id_word = id_word & 0xFFFFFFFF
        self.busy_reads_before_done = max(busy_reads_before_done, 0)
        self.total_errors = max(total_errors, 0)
        self.payload_errors = max(payload_errors, 0)
        self._busy_remaining = 0
        self._done_sticky = False
        self._started = False
        self.regs: dict[int, int] = {
            REGS.control_status: 0,
            REGS.frame_bit_count: 0,
            REGS.preamble_count: 0,
            REGS.start_offset: 0,
            REGS.received_bits: 0,
            REGS.total_errors: 0,
            REGS.payload_errors: 0,
            REGS.core_id: self.id_word,
        }

    def _status_word(self) -> int:
        busy = 1 if self._busy_remaining > 0 else 0
        done = 1 if self._done_sticky else 0
        return (done << 2) | (busy << 1)

    def _complete_if_ready(self) -> None:
        if self._started and self._busy_remaining == 0 and not self._done_sticky:
            self._done_sticky = True
            self._started = False
            self.regs[REGS.received_bits] = self.regs[REGS.frame_bit_count]
            self.regs[REGS.total_errors] = self.total_errors
            self.regs[REGS.payload_errors] = self.payload_errors

    def read32(self, offset: int) -> int:
        if offset == REGS.control_status:
            if self._busy_remaining > 0:
                status = self._status_word()
                self._busy_remaining -= 1
                self._complete_if_ready()
                return status

            self._complete_if_ready()
            return self._status_word()

        return self.regs.get(offset, 0)

    def write32(self, offset: int, value: int) -> None:
        value &= 0xFFFFFFFF
        if offset == REGS.control_status:
            if value & REGS.start_mask:
                self._started = True
                self._done_sticky = False
                self._busy_remaining = self.busy_reads_before_done
                self.regs[REGS.received_bits] = 0
                self.regs[REGS.total_errors] = 0
                self.regs[REGS.payload_errors] = 0
            if value & REGS.done_mask:
                self._done_sticky = False
            self.regs[offset] = self._status_word()
            return

        self.regs[offset] = value

    def close(self) -> None:
        return None


def build_backend(args: argparse.Namespace) -> RegisterIo:
    if args.backend == "mock":
        return MockRegisterIo(
            id_word=args.expected_id,
            busy_reads_before_done=args.mock_busy_reads,
            total_errors=args.mock_total_errors,
            payload_errors=args.mock_payload_errors,
        )
    if args.base_addr is None:
        raise ValueError("--base-addr is required for mmap/devmem/ssh-devmem backends.")
    if args.backend == "mmap":
        return MmapRegisterIo(args.base_addr)
    if args.backend == "devmem":
        return DevMemRegisterIo(args.base_addr)
    if args.backend == "ssh-devmem":
        if not args.ssh_host:
            raise ValueError("--ssh-host is required for the ssh-devmem backend.")
        return SshDevMemRegisterIo(
            args.base_addr,
            host=args.ssh_host,
            user=args.ssh_user,
            password=args.ssh_password,
            port=args.ssh_port,
            key_path=args.ssh_key_path,
            timeout_s=args.ssh_timeout_s,
            devmem_bin=args.ssh_devmem_bin,
        )
    raise ValueError(f"Unsupported backend: {args.backend}")


def run_bringup(io: RegisterIo, cfg: BringupConfig) -> BringupResult:
    id_word = io.read32(REGS.core_id)
    if id_word != cfg.expected_id:
        raise RuntimeError(
            f"Unexpected AXI-Lite ID word 0x{id_word:08X}; expected 0x{cfg.expected_id:08X}."
        )

    initial_status = io.read32(REGS.control_status)

    io.write32(REGS.frame_bit_count, cfg.frame_bit_count)
    io.write32(REGS.preamble_count, cfg.preamble_count)
    io.write32(REGS.start_offset, cfg.start_offset)
    io.write32(REGS.control_status, REGS.start_mask)

    busy_observed = False
    done_observed = False
    final_status = 0
    poll_reads = 0

    for poll_reads in range(1, cfg.poll_limit + 1):
        final_status = io.read32(REGS.control_status)
        if final_status & REGS.busy_mask:
            busy_observed = True
        if final_status & REGS.done_mask:
            done_observed = True
            break
        if cfg.poll_delay_ms > 0:
            time.sleep(cfg.poll_delay_ms / 1000.0)

    if not done_observed:
        raise TimeoutError(
            f"AXI-Lite controlled burst did not assert done within {cfg.poll_limit} polls."
        )

    received_bits = io.read32(REGS.received_bits)
    total_errors = io.read32(REGS.total_errors)
    payload_errors = io.read32(REGS.payload_errors)

    if cfg.max_total_errors is not None and total_errors > cfg.max_total_errors:
        raise RuntimeError(
            f"total_errors={total_errors} exceeds max_total_errors={cfg.max_total_errors}."
        )
    if cfg.max_payload_errors is not None and payload_errors > cfg.max_payload_errors:
        raise RuntimeError(
            f"payload_errors={payload_errors} exceeds max_payload_errors={cfg.max_payload_errors}."
        )

    cleared_status = final_status
    done_cleared = False
    if cfg.clear_done:
        io.write32(REGS.control_status, REGS.done_mask)
        cleared_status = io.read32(REGS.control_status)
        done_cleared = not bool(cleared_status & REGS.done_mask)

    payload_bit_count = max(cfg.frame_bit_count - cfg.preamble_count, 1)
    snapshot = register_snapshot(io, cfg.base_addr)
    return BringupResult(
        backend=cfg.backend,
        base_addr=cfg.base_addr,
        id_word=id_word,
        initial_status=initial_status,
        final_status=final_status,
        cleared_status=cleared_status,
        done_cleared=done_cleared,
        busy_observed=busy_observed,
        done_observed=done_observed,
        poll_reads=poll_reads,
        frame_bit_count=cfg.frame_bit_count,
        preamble_count=cfg.preamble_count,
        start_offset=cfg.start_offset,
        received_bits=received_bits,
        total_errors=total_errors,
        payload_errors=payload_errors,
        ber_total=total_errors / max(cfg.frame_bit_count, 1),
        ber_payload=payload_errors / payload_bit_count,
        register_snapshot=snapshot,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the minimal PS-side AXI-Lite sequence for the BPSK BER core."
    )
    parser.add_argument("--backend", choices=["mmap", "devmem", "mock", "ssh-devmem"], default="mock")
    parser.add_argument(
        "--base-addr",
        type=parse_int,
        default=None,
        help="AXI-Lite base address, for example 0x43C00000. Required for mmap/devmem/ssh-devmem.",
    )
    parser.add_argument("--frame-bit-count", type=int, default=DEFAULT_FRAME_BIT_COUNT)
    parser.add_argument("--preamble-count", type=int, default=DEFAULT_PREAMBLE_COUNT)
    parser.add_argument("--start-offset", type=int, default=DEFAULT_START_OFFSET)
    parser.add_argument("--poll-limit", type=int, default=DEFAULT_POLL_LIMIT)
    parser.add_argument("--poll-delay-ms", type=int, default=DEFAULT_POLL_DELAY_MS)
    parser.add_argument("--expected-id", type=parse_int, default=DEFAULT_EXPECTED_ID)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--no-clear-done", action="store_true")
    parser.add_argument("--max-total-errors", type=int, default=None)
    parser.add_argument("--max-payload-errors", type=int, default=None)
    parser.add_argument("--ssh-host", default=os.environ.get("ZYNQ_SSH_HOST"))
    parser.add_argument("--ssh-user", default=os.environ.get("ZYNQ_SSH_USER", "root"))
    parser.add_argument("--ssh-password", default=os.environ.get("ZYNQ_SSH_PASSWORD"))
    parser.add_argument("--ssh-port", type=int, default=int(os.environ.get("ZYNQ_SSH_PORT", "22")))
    parser.add_argument("--ssh-key-path", type=Path, default=None)
    parser.add_argument("--ssh-timeout-s", type=float, default=10.0)
    parser.add_argument("--ssh-devmem-bin", default="/sbin/devmem")
    parser.add_argument(
        "--mock-busy-reads",
        type=int,
        default=2,
        help="Mock backend only: number of busy polls before done is asserted.",
    )
    parser.add_argument(
        "--mock-total-errors",
        type=int,
        default=0,
        help="Mock backend only: deterministic total error count.",
    )
    parser.add_argument(
        "--mock-payload-errors",
        type=int,
        default=0,
        help="Mock backend only: deterministic payload-only error count.",
    )
    return parser.parse_args()


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    if args.backend == "mock" and args.base_addr is None:
        args.base_addr = DEFAULT_MOCK_BASE_ADDR

    io = build_backend(args)
    cfg = BringupConfig(
        backend=args.backend,
        base_addr=args.base_addr,
        frame_bit_count=args.frame_bit_count,
        preamble_count=args.preamble_count,
        start_offset=args.start_offset,
        poll_limit=args.poll_limit,
        poll_delay_ms=args.poll_delay_ms,
        expected_id=args.expected_id,
        clear_done=not args.no_clear_done,
        max_total_errors=args.max_total_errors,
        max_payload_errors=args.max_payload_errors,
    )

    try:
        result = run_bringup(io, cfg)
    finally:
        io.close()

    payload = {
        "config": asdict(cfg),
        "result": asdict(result),
    }

    print("Lab 11.7 - AXI-Lite BPSK bring-up")
    print(f"Backend: {result.backend}")
    print(f"Base address: 0x{result.base_addr:08X}")
    print(f"ID word: 0x{result.id_word:08X}")
    print(f"Busy observed: {result.busy_observed}")
    print(f"Done observed: {result.done_observed}")
    print(f"Poll reads: {result.poll_reads}")
    print(f"Received bits: {result.received_bits}")
    print(f"Total errors: {result.total_errors}")
    print(f"Payload errors: {result.payload_errors}")
    print(f"BER total/payload: {result.ber_total:.6e}/{result.ber_payload:.6e}")
    if cfg.clear_done:
        print(f"Done cleared: {result.done_cleared}")

    if args.json_out is not None:
        write_json(args.json_out, payload)
        print(f"JSON report: {args.json_out}")


if __name__ == "__main__":
    main()
