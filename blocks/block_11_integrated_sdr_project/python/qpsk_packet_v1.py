"""Packet-v1 reference codec for the 256-bit course QPSK payload.

The byte and bus conventions are intentionally explicit:

* sequence and CRC fields are little-endian;
* packet byte ``n`` maps to payload bus bits ``8*n +: 8``;
* bits within each byte are serialized least-significant bit first.

CRC-16/CCITT-FALSE is used over packet bytes 0 through 29: polynomial
0x1021, init 0xffff, refin=false, refout=false, xorout=0x0000.  Its standard
``123456789`` check value is 0x29b1.
"""

from __future__ import annotations

from dataclasses import dataclass


PACKET_SIZE = 32
HEADER_SIZE = 3
MAX_PAYLOAD_SIZE = 27
CRC_INPUT_SIZE = 30
CRC_POLYNOMIAL = 0x1021
CRC_INITIAL = 0xFFFF
CRC_XOR_OUT = 0x0000


@dataclass(frozen=True)
class PacketDecodeResult:
    """Decoded packet fields and integrity status."""

    payload: bytes
    sequence: int
    crc_ok: bool
    frame_error: bool


def crc16_ccitt_false(data: bytes) -> int:
    """Return CRC-16/CCITT-FALSE for *data*."""
    crc = CRC_INITIAL
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ CRC_POLYNOMIAL) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc ^ CRC_XOR_OUT


def encode_packet(payload: bytes, sequence: int) -> bytes:
    """Encode one application payload into the fixed 32-byte packet-v1 frame."""
    if len(payload) > MAX_PAYLOAD_SIZE:
        raise ValueError(
            f"payload is {len(payload)} bytes; packet-v1 limit is {MAX_PAYLOAD_SIZE}"
        )
    if not 0 <= sequence <= 0xFFFF:
        raise ValueError("sequence must fit in uint16")

    packet = bytearray(PACKET_SIZE)
    packet[0] = len(payload)
    packet[1:3] = sequence.to_bytes(2, "little")
    packet[HEADER_SIZE : HEADER_SIZE + len(payload)] = payload
    crc = crc16_ccitt_false(packet[:CRC_INPUT_SIZE])
    packet[CRC_INPUT_SIZE:PACKET_SIZE] = crc.to_bytes(2, "little")
    return bytes(packet)


def decode_packet(packet: bytes) -> PacketDecodeResult:
    """Decode one fixed-size packet without hiding CRC or length failures."""
    if len(packet) != PACKET_SIZE:
        raise ValueError(f"packet-v1 frame must be exactly {PACKET_SIZE} bytes")

    payload_length = packet[0]
    frame_error = payload_length > MAX_PAYLOAD_SIZE
    payload = b"" if frame_error else packet[HEADER_SIZE : HEADER_SIZE + payload_length]
    sequence = int.from_bytes(packet[1:3], "little")
    expected_crc = int.from_bytes(packet[CRC_INPUT_SIZE:PACKET_SIZE], "little")
    actual_crc = crc16_ccitt_false(packet[:CRC_INPUT_SIZE])
    return PacketDecodeResult(
        payload=payload,
        sequence=sequence,
        crc_ok=actual_crc == expected_crc,
        frame_error=frame_error,
    )
