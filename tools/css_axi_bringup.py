#!/usr/bin/env python3
"""Bring-up helper for the Block 8 SF7 CSS AXI-Lite control plane.

The helper can talk to a mapped AXI-Lite register window through /dev/mem on
Zynq Linux, or use an in-memory mock backend for unit tests/offline examples.
It intentionally does not configure AXI DMA or stream samples; it covers the
software-visible register/status/result boundary of css_sf7_axi_accelerator.
"""

from __future__ import annotations

import argparse
import json
import mmap
import os
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

REG_ID = 0x00
REG_VERSION = 0x04
REG_CONTROL = 0x08
REG_STATUS = 0x0C
REG_RESULT0 = 0x10
REG_COMPLETED_COUNT = 0x30
REG_FRAME_ERROR_COUNT = 0x34
REGISTER_SPAN = 0x38

CORE_ID = 0x43535337  # "CSS7"
CORE_VERSION = 0x00010000

CONTROL_IRQ_ENABLE = 1 << 0
CONTROL_CLEAR_DONE = 1 << 8
CONTROL_CLEAR_FRAME_ERROR = 1 << 9
CONTROL_CLEAR_COUNTERS = 1 << 10

STATUS_BUSY = 1 << 0
STATUS_INPUT_READY = 1 << 1
STATUS_RESULT_PENDING = 1 << 2
STATUS_DONE_STICKY = 1 << 3
STATUS_FRAME_ERROR_STICKY = 1 << 4


class RegisterBackend:
    """Minimal 32-bit register backend interface."""

    def read32(self, offset: int) -> int:
        raise NotImplementedError

    def write32(self, offset: int, value: int) -> None:
        raise NotImplementedError

    def close(self) -> None:
        pass

    def __enter__(self) -> "RegisterBackend":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class DevMemBackend(RegisterBackend):
    """Page-aligned /dev/mem mapping for one AXI-Lite register window."""

    def __init__(self, base_address: int, device: str = "/dev/mem") -> None:
        if base_address < 0:
            raise ValueError("base address must be non-negative")

        page_size = mmap.PAGESIZE
        page_base = base_address & ~(page_size - 1)
        page_offset = base_address - page_base
        mapping_size = page_offset + REGISTER_SPAN

        self._page_offset = page_offset
        self._fd = os.open(device, os.O_RDWR | os.O_SYNC)
        try:
            self._map = mmap.mmap(
                self._fd,
                mapping_size,
                flags=mmap.MAP_SHARED,
                prot=mmap.PROT_READ | mmap.PROT_WRITE,
                offset=page_base,
            )
        except Exception:
            os.close(self._fd)
            raise

    @staticmethod
    def _check_offset(offset: int) -> None:
        if offset < 0 or offset >= REGISTER_SPAN or offset % 4:
            raise ValueError(f"invalid 32-bit register offset 0x{offset:x}")

    def read32(self, offset: int) -> int:
        self._check_offset(offset)
        start = self._page_offset + offset
        return struct.unpack_from("<I", self._map, start)[0]

    def write32(self, offset: int, value: int) -> None:
        self._check_offset(offset)
        start = self._page_offset + offset
        struct.pack_into("<I", self._map, start, value & 0xFFFFFFFF)

    def close(self) -> None:
        self._map.close()
        os.close(self._fd)


class MockRegisterBackend(RegisterBackend):
    """Simple mutable backend used by tests and offline register snapshots."""

    def __init__(self, registers: Mapping[int, int] | None = None) -> None:
        self.registers = {
            int(offset): int(value) & 0xFFFFFFFF
            for offset, value in (registers or {}).items()
        }
        self.writes: list[tuple[int, int]] = []

    def read32(self, offset: int) -> int:
        return self.registers.get(offset, 0)

    def write32(self, offset: int, value: int) -> None:
        value &= 0xFFFFFFFF
        self.writes.append((offset, value))
        self.registers[offset] = value


@dataclass(frozen=True)
class CssStatus:
    busy: bool
    input_ready: bool
    result_pending: bool
    done_sticky: bool
    frame_error_sticky: bool
    completed_count: int
    frame_error_count: int


@dataclass(frozen=True)
class CssResult:
    peak_bin: int
    second_bin: int
    frame_error: bool
    saturation_count: int
    peak_magnitude_squared: int
    second_magnitude_squared: int
    completed_count: int
    raw_words: tuple[int, ...]


class CssAxiDevice:
    """Typed software view of css_sf7_axi_accelerator AXI-Lite registers."""

    def __init__(self, backend: RegisterBackend) -> None:
        self.backend = backend

    def probe(self) -> tuple[int, int]:
        core_id = self.backend.read32(REG_ID)
        version = self.backend.read32(REG_VERSION)
        if core_id != CORE_ID:
            raise RuntimeError(
                f"unexpected CSS core ID 0x{core_id:08x}; expected 0x{CORE_ID:08x}"
            )
        return core_id, version

    def read_status(self) -> CssStatus:
        status = self.backend.read32(REG_STATUS)
        return CssStatus(
            busy=bool(status & STATUS_BUSY),
            input_ready=bool(status & STATUS_INPUT_READY),
            result_pending=bool(status & STATUS_RESULT_PENDING),
            done_sticky=bool(status & STATUS_DONE_STICKY),
            frame_error_sticky=bool(status & STATUS_FRAME_ERROR_STICKY),
            completed_count=self.backend.read32(REG_COMPLETED_COUNT),
            frame_error_count=self.backend.read32(REG_FRAME_ERROR_COUNT),
        )

    def _irq_enabled(self) -> bool:
        return bool(self.backend.read32(REG_CONTROL) & CONTROL_IRQ_ENABLE)

    def _write_control_pulse(self, pulse_bits: int) -> None:
        value = CONTROL_IRQ_ENABLE if self._irq_enabled() else 0
        self.backend.write32(REG_CONTROL, value | pulse_bits)

    def set_irq_enable(self, enabled: bool) -> None:
        self.backend.write32(REG_CONTROL, CONTROL_IRQ_ENABLE if enabled else 0)

    def clear_done(self) -> None:
        self._write_control_pulse(CONTROL_CLEAR_DONE)

    def clear_frame_error(self) -> None:
        self._write_control_pulse(CONTROL_CLEAR_FRAME_ERROR)

    def clear_counters(self) -> None:
        self._write_control_pulse(CONTROL_CLEAR_COUNTERS)

    def clear_sticky_and_counters(self) -> None:
        self._write_control_pulse(
            CONTROL_CLEAR_DONE | CONTROL_CLEAR_FRAME_ERROR | CONTROL_CLEAR_COUNTERS
        )

    def read_result_coherent(self, max_attempts: int = 4) -> CssResult:
        """Read the 256-bit snapshot without accepting a torn multiword value.

        The RTL updates last_result and completed_count on the same result event.
        Reading completed_count before and after the eight result words detects a
        result arriving while software is walking the 32-bit AXI-Lite window.
        """
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least one")

        for _ in range(max_attempts):
            before = self.backend.read32(REG_COMPLETED_COUNT)
            words = tuple(
                self.backend.read32(REG_RESULT0 + 4 * index) for index in range(8)
            )
            after = self.backend.read32(REG_COMPLETED_COUNT)
            if before == after:
                return self.decode_result(words, after)

        raise RuntimeError("CSS result changed during every coherent snapshot attempt")

    @staticmethod
    def decode_result(words: tuple[int, ...], completed_count: int = 0) -> CssResult:
        if len(words) != 8:
            raise ValueError("CSS result snapshot must contain exactly eight 32-bit words")

        word0 = words[0]
        peak_magnitude_squared = words[1] | (words[2] << 32)
        second_magnitude_squared = words[3] | (words[4] << 32)
        return CssResult(
            peak_bin=word0 & 0x7F,
            second_bin=(word0 >> 8) & 0x7F,
            frame_error=bool(word0 & (1 << 15)),
            saturation_count=(word0 >> 16) & 0xFFFF,
            peak_magnitude_squared=peak_magnitude_squared,
            second_magnitude_squared=second_magnitude_squared,
            completed_count=completed_count,
            raw_words=words,
        )


def _parse_int(text: str) -> int:
    return int(text, 0)


def _load_mock(path: Path) -> MockRegisterBackend:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("mock JSON must be an object mapping offsets to values")
    registers = {_parse_int(str(key)): _parse_int(str(value)) for key, value in payload.items()}
    return MockRegisterBackend(registers)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--base", type=_parse_int, help="AXI-Lite physical base address")
    source.add_argument("--mock-json", type=Path, help="offline register map JSON")
    parser.add_argument("--devmem", default="/dev/mem", help="physical-memory device")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("probe", help="validate ID and print core version")
    subparsers.add_parser("status", help="print decoded status and counters")
    result = subparsers.add_parser("result", help="read coherent last-result snapshot")
    result.add_argument("--attempts", type=int, default=4)

    irq = subparsers.add_parser("irq", help="enable or disable IRQ generation")
    irq.add_argument("state", choices=("on", "off"))

    clear = subparsers.add_parser("clear", help="clear sticky flags/counters")
    clear.add_argument("what", choices=("done", "frame", "counters", "all"))
    return parser


def _run_command(device: CssAxiDevice, args: argparse.Namespace) -> None:
    if args.command == "probe":
        core_id, version = device.probe()
        print(f"id=0x{core_id:08x} version=0x{version:08x}")
    elif args.command == "status":
        print(json.dumps(asdict(device.read_status()), indent=2, sort_keys=True))
    elif args.command == "result":
        result = asdict(device.read_result_coherent(args.attempts))
        result["raw_words"] = [f"0x{word:08x}" for word in result["raw_words"]]
        print(json.dumps(result, indent=2, sort_keys=True))
    elif args.command == "irq":
        device.set_irq_enable(args.state == "on")
    elif args.command == "clear":
        {
            "done": device.clear_done,
            "frame": device.clear_frame_error,
            "counters": device.clear_counters,
            "all": device.clear_sticky_and_counters,
        }[args.what]()


def main() -> int:
    args = _build_parser().parse_args()
    backend: RegisterBackend
    if args.mock_json is not None:
        backend = _load_mock(args.mock_json)
    else:
        backend = DevMemBackend(args.base, args.devmem)

    with backend:
        _run_command(CssAxiDevice(backend), args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
