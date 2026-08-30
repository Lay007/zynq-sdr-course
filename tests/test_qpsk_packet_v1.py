from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "blocks"
    / "block_11_integrated_sdr_project"
    / "python"
    / "qpsk_packet_v1.py"
)
SPEC = importlib.util.spec_from_file_location("qpsk_packet_v1", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
PACKET = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PACKET
SPEC.loader.exec_module(PACKET)


def test_crc16_ccitt_false_known_answer() -> None:
    assert PACKET.crc16_ccitt_false(b"123456789") == 0x29B1


@pytest.mark.parametrize("payload", [b"", bytes(range(27))])
@pytest.mark.parametrize("sequence", [0, 0xFFFF])
def test_encode_decode_boundaries(payload: bytes, sequence: int) -> None:
    encoded = PACKET.encode_packet(payload, sequence)
    decoded = PACKET.decode_packet(encoded)

    assert len(encoded) == 32
    assert decoded.payload == payload
    assert decoded.sequence == sequence
    assert decoded.crc_ok is True
    assert decoded.frame_error is False


def test_deterministic_little_endian_layout() -> None:
    packet = PACKET.encode_packet(b"ABC", 0x1234)

    assert packet[:8] == bytes.fromhex("03 34 12 41 42 43 00 00")
    assert packet[8:30] == bytes(22)
    assert packet[30:] == PACKET.crc16_ccitt_false(packet[:30]).to_bytes(2, "little")


def test_corrupted_payload_fails_crc() -> None:
    packet = bytearray(PACKET.encode_packet(b"Hello from board A", 17))
    packet[7] ^= 0x20

    decoded = PACKET.decode_packet(bytes(packet))
    assert decoded.crc_ok is False
    assert decoded.frame_error is False


def test_corrupted_crc_fails_crc() -> None:
    packet = bytearray(PACKET.encode_packet(b"hello", 3))
    packet[31] ^= 0x01

    assert PACKET.decode_packet(bytes(packet)).crc_ok is False


def test_invalid_length_field_is_reported() -> None:
    packet = bytearray(PACKET.encode_packet(b"", 9))
    packet[0] = 28
    crc = PACKET.crc16_ccitt_false(packet[:30])
    packet[30:] = crc.to_bytes(2, "little")

    decoded = PACKET.decode_packet(bytes(packet))
    assert decoded.frame_error is True
    assert decoded.payload == b""
    assert decoded.sequence == 9
    assert decoded.crc_ok is True


def test_oversize_payload_is_rejected() -> None:
    with pytest.raises(ValueError, match="packet-v1 limit"):
        PACKET.encode_packet(bytes(28), 0)


def test_sequence_must_fit_uint16() -> None:
    for sequence in (-1, 0x1_0000):
        with pytest.raises(ValueError, match="uint16"):
            PACKET.encode_packet(b"", sequence)


def test_packet_size_is_exact() -> None:
    for packet in (bytes(31), bytes(33)):
        with pytest.raises(ValueError, match="exactly 32 bytes"):
            PACKET.decode_packet(packet)
