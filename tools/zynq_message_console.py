#!/usr/bin/env python3
"""Educational PS/PL message-mailbox console for Zynq.

The tool intentionally uses a tiny 64-byte AXI-Lite mailbox instead of DMA so
students can see the complete software-visible PS/PL contract.  It supports a
behavioral loopback mock for laptops/CI and a /dev/mem backend for later board
bring-up.  The physical base address is always supplied by the user from the
actual Vivado address map.
"""

from __future__ import annotations

import argparse
import mmap
import os
import struct
import time
from dataclasses import dataclass

REG_ID = 0x00
REG_VERSION = 0x04
REG_CONTROL = 0x08
REG_STATUS = 0x0C
REG_TX_SEQUENCE = 0x10
REG_TX_LENGTH = 0x14
REG_TX_DATA0 = 0x20
REG_RX_SEQUENCE = 0x60
REG_RX_LENGTH = 0x64
REG_RX_META = 0x68
REG_RX_DATA0 = 0x70

MAILBOX_WORDS = 16
MAX_PAYLOAD_BYTES = MAILBOX_WORDS * 4
REGISTER_SPAN = 0xB0

CORE_ID = 0x4D424F58  # "MBOX"
CORE_VERSION = 0x00010000

CONTROL_TX_START = 1 << 0
CONTROL_RX_ACK = 1 << 1

STATUS_TX_BUSY = 1 << 0
STATUS_TX_DONE = 1 << 1
STATUS_RX_VALID = 1 << 2
STATUS_RX_OVERFLOW = 1 << 3

RX_META_CRC_OK = 1 << 0
RX_META_FRAME_ERROR = 1 << 1


class RegisterBackend:
    """Minimal 32-bit register backend."""

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
    """Map one AXI-Lite mailbox window through Linux /dev/mem."""

    def __init__(self, base_address: int, device: str = "/dev/mem") -> None:
        if base_address < 0:
            raise ValueError("base address must be non-negative")

        page_size = mmap.PAGESIZE
        page_base = base_address & ~(page_size - 1)
        self._page_offset = base_address - page_base
        mapping_size = self._page_offset + REGISTER_SPAN

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
            raise ValueError(f"invalid 32-bit mailbox offset 0x{offset:x}")

    def read32(self, offset: int) -> int:
        self._check_offset(offset)
        return struct.unpack_from("<I", self._map, self._page_offset + offset)[0]

    def write32(self, offset: int, value: int) -> None:
        self._check_offset(offset)
        struct.pack_into(
            "<I", self._map, self._page_offset + offset, value & 0xFFFFFFFF
        )

    def close(self) -> None:
        self._map.close()
        os.close(self._fd)


class LoopbackMockBackend(RegisterBackend):
    """Behavioral mailbox used by CI and the no-board teaching demo.

    TX_START immediately copies TX registers into the RX mailbox and marks the
    message CRC-good.  This is intentionally a register-protocol model, not a
    modem or RF simulation.
    """

    def __init__(self) -> None:
        self.registers: dict[int, int] = {
            REG_ID: CORE_ID,
            REG_VERSION: CORE_VERSION,
            REG_STATUS: 0,
        }
        self.writes: list[tuple[int, int]] = []

    def read32(self, offset: int) -> int:
        return self.registers.get(offset, 0)

    def write32(self, offset: int, value: int) -> None:
        value &= 0xFFFFFFFF
        self.writes.append((offset, value))

        if offset != REG_CONTROL:
            self.registers[offset] = value
            return

        if value & CONTROL_RX_ACK:
            self.registers[REG_STATUS] = self.read32(REG_STATUS) & ~STATUS_RX_VALID

        if value & CONTROL_TX_START:
            status = self.read32(REG_STATUS)
            if status & STATUS_RX_VALID:
                self.registers[REG_STATUS] = status | STATUS_RX_OVERFLOW
                return

            self.registers[REG_STATUS] = status | STATUS_TX_BUSY
            self.registers[REG_RX_SEQUENCE] = self.read32(REG_TX_SEQUENCE)
            self.registers[REG_RX_LENGTH] = self.read32(REG_TX_LENGTH)
            self.registers[REG_RX_META] = RX_META_CRC_OK
            for index in range(MAILBOX_WORDS):
                self.registers[REG_RX_DATA0 + 4 * index] = self.read32(
                    REG_TX_DATA0 + 4 * index
                )

            self.registers[REG_STATUS] = (
                self.read32(REG_STATUS) & ~STATUS_TX_BUSY
            ) | STATUS_TX_DONE | STATUS_RX_VALID


@dataclass(frozen=True)
class ReceivedMessage:
    sequence: int
    payload: bytes
    crc_ok: bool
    frame_error: bool


def pack_payload(payload: bytes) -> tuple[int, ...]:
    """Pack up to 64 bytes into sixteen little-endian 32-bit words."""
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError(
            f"payload is {len(payload)} bytes; mailbox limit is {MAX_PAYLOAD_BYTES}"
        )
    padded = payload.ljust(MAX_PAYLOAD_BYTES, b"\x00")
    return tuple(
        struct.unpack_from("<I", padded, 4 * index)[0]
        for index in range(MAILBOX_WORDS)
    )


def unpack_payload(words: tuple[int, ...], length: int) -> bytes:
    """Unpack mailbox words using the explicit byte length."""
    if len(words) != MAILBOX_WORDS:
        raise ValueError(f"mailbox snapshot must contain {MAILBOX_WORDS} words")
    if length < 0 or length > MAX_PAYLOAD_BYTES:
        raise ValueError(f"invalid mailbox payload length {length}")
    raw = b"".join(struct.pack("<I", word & 0xFFFFFFFF) for word in words)
    return raw[:length]


class MessageMailbox:
    """Typed software view of the educational PS/PL mailbox."""

    def __init__(self, backend: RegisterBackend) -> None:
        self.backend = backend

    def probe(self) -> tuple[int, int]:
        core_id = self.backend.read32(REG_ID)
        version = self.backend.read32(REG_VERSION)
        if core_id != CORE_ID:
            raise RuntimeError(
                f"unexpected mailbox ID 0x{core_id:08x}; expected 0x{CORE_ID:08x}"
            )
        return core_id, version

    def send(self, payload: bytes, sequence: int) -> None:
        if not 0 <= sequence <= 0xFFFFFFFF:
            raise ValueError("sequence must fit in uint32")
        if self.backend.read32(REG_STATUS) & STATUS_TX_BUSY:
            raise RuntimeError("mailbox TX is busy")

        words = pack_payload(payload)
        self.backend.write32(REG_TX_SEQUENCE, sequence)
        self.backend.write32(REG_TX_LENGTH, len(payload))
        for index, word in enumerate(words):
            self.backend.write32(REG_TX_DATA0 + 4 * index, word)
        self.backend.write32(REG_CONTROL, CONTROL_TX_START)

    def receive(self) -> ReceivedMessage | None:
        if not self.backend.read32(REG_STATUS) & STATUS_RX_VALID:
            return None

        sequence = self.backend.read32(REG_RX_SEQUENCE)
        length = self.backend.read32(REG_RX_LENGTH)
        meta = self.backend.read32(REG_RX_META)
        words = tuple(
            self.backend.read32(REG_RX_DATA0 + 4 * index)
            for index in range(MAILBOX_WORDS)
        )
        return ReceivedMessage(
            sequence=sequence,
            payload=unpack_payload(words, length),
            crc_ok=bool(meta & RX_META_CRC_OK),
            frame_error=bool(meta & RX_META_FRAME_ERROR),
        )

    def receive_wait(self, timeout_s: float, poll_s: float = 0.05) -> ReceivedMessage | None:
        if timeout_s < 0:
            raise ValueError("timeout must be non-negative")
        if poll_s <= 0:
            raise ValueError("poll interval must be positive")

        deadline = time.monotonic() + timeout_s
        while True:
            message = self.receive()
            if message is not None:
                return message
            if time.monotonic() >= deadline:
                return None
            time.sleep(min(poll_s, max(0.0, deadline - time.monotonic())))

    def acknowledge_receive(self) -> None:
        self.backend.write32(REG_CONTROL, CONTROL_RX_ACK)


def _parse_int(text: str) -> int:
    return int(text, 0)


def _payload_text(payload: bytes) -> str:
    return payload.decode("utf-8", errors="replace")


def _print_tx(sequence: int, payload: bytes) -> None:
    print(
        f'TX sequence={sequence} bytes={len(payload)} payload="{_payload_text(payload)}"'
    )


def _print_rx(message: ReceivedMessage) -> None:
    crc = "OK" if message.crc_ok and not message.frame_error else "FAIL"
    print(
        f'RX sequence={message.sequence} bytes={len(message.payload)} '
        f'crc={crc} payload="{_payload_text(message.payload)}"'
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--base", type=_parse_int, help="AXI-Lite physical base address")
    source.add_argument(
        "--mock", action="store_true", help="use an in-process behavioral loopback"
    )
    parser.add_argument("--devmem", default="/dev/mem", help="physical-memory device")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("probe", help="validate mailbox ID/version")

    send = subparsers.add_parser("send", help="write one UTF-8 message and pulse TX_START")
    send.add_argument("message")
    send.add_argument("--sequence", type=_parse_int, default=0)

    receive = subparsers.add_parser("receive", help="read and acknowledge one RX message")
    receive.add_argument("--wait", type=float, default=0.0, metavar="SECONDS")
    receive.add_argument("--poll", type=float, default=0.05, metavar="SECONDS")

    demo = subparsers.add_parser("demo", help="mock-friendly send + receive round trip")
    demo.add_argument("message")
    demo.add_argument("--sequence", type=_parse_int, default=0)
    return parser


def _run_command(device: MessageMailbox, args: argparse.Namespace) -> int:
    if args.command == "probe":
        core_id, version = device.probe()
        print(f"id=0x{core_id:08x} version=0x{version:08x}")
        return 0

    if args.command == "send":
        payload = args.message.encode("utf-8")
        device.send(payload, args.sequence)
        _print_tx(args.sequence, payload)
        return 0

    if args.command == "receive":
        message = device.receive_wait(args.wait, args.poll)
        if message is None:
            print("RX timeout: no valid message")
            return 2
        _print_rx(message)
        device.acknowledge_receive()
        return 0 if message.crc_ok and not message.frame_error else 3

    if args.command == "demo":
        payload = args.message.encode("utf-8")
        device.send(payload, args.sequence)
        _print_tx(args.sequence, payload)
        message = device.receive_wait(0.0)
        if message is None:
            raise RuntimeError("mock demo did not produce an RX message")
        _print_rx(message)
        device.acknowledge_receive()
        return 0

    raise AssertionError(f"unexpected command {args.command}")


def main() -> int:
    args = _build_parser().parse_args()
    backend: RegisterBackend
    if args.mock:
        backend = LoopbackMockBackend()
    else:
        backend = DevMemBackend(args.base, args.devmem)

    with backend:
        device = MessageMailbox(backend)
        device.probe()
        return _run_command(device, args)


if __name__ == "__main__":
    raise SystemExit(main())
