import pytest

from tools.zynq_message_console import (
    CONTROL_RX_ACK,
    CONTROL_TX_START,
    CORE_ID,
    CORE_VERSION,
    MAX_PAYLOAD_BYTES,
    MessageMailbox,
    LoopbackMockBackend,
    REG_CONTROL,
    REG_ID,
    REG_RX_DATA0,
    REG_RX_LENGTH,
    REG_RX_META,
    REG_RX_SEQUENCE,
    REG_STATUS,
    REG_TX_DATA0,
    RX_META_CRC_OK,
    STATUS_RX_OVERFLOW,
    STATUS_RX_VALID,
    pack_payload,
    unpack_payload,
)


def test_pack_payload_is_little_endian() -> None:
    words = pack_payload(b"ABCD")
    assert words[0] == 0x44434241
    assert words[1:] == (0,) * 15


def test_pack_unpack_round_trip_full_mailbox() -> None:
    payload = bytes(range(MAX_PAYLOAD_BYTES))
    assert unpack_payload(pack_payload(payload), len(payload)) == payload


def test_pack_rejects_payload_larger_than_mailbox() -> None:
    with pytest.raises(ValueError, match="mailbox limit"):
        pack_payload(b"x" * (MAX_PAYLOAD_BYTES + 1))


def test_unpack_requires_sixteen_words() -> None:
    with pytest.raises(ValueError, match="16 words"):
        unpack_payload((0,) * 15, 0)


def test_unpack_rejects_invalid_length() -> None:
    with pytest.raises(ValueError, match="invalid mailbox payload length"):
        unpack_payload((0,) * 16, MAX_PAYLOAD_BYTES + 1)


def test_probe_reads_mailbox_identity() -> None:
    device = MessageMailbox(LoopbackMockBackend())
    assert device.probe() == (CORE_ID, CORE_VERSION)


def test_probe_rejects_wrong_identity() -> None:
    backend = LoopbackMockBackend()
    backend.registers[REG_ID] = 0xDEADBEEF
    with pytest.raises(RuntimeError, match="unexpected mailbox ID"):
        MessageMailbox(backend).probe()


def test_mock_loopback_round_trip_and_ack() -> None:
    backend = LoopbackMockBackend()
    device = MessageMailbox(backend)
    payload = "Hello Zynq".encode()

    device.send(payload, sequence=17)
    assert backend.writes[-1] == (REG_CONTROL, CONTROL_TX_START)
    assert backend.read32(REG_STATUS) & STATUS_RX_VALID
    assert backend.read32(REG_RX_SEQUENCE) == 17
    assert backend.read32(REG_RX_LENGTH) == len(payload)
    assert backend.read32(REG_RX_META) == RX_META_CRC_OK

    message = device.receive()
    assert message is not None
    assert message.sequence == 17
    assert message.payload == payload
    assert message.crc_ok is True
    assert message.frame_error is False

    device.acknowledge_receive()
    assert backend.writes[-1] == (REG_CONTROL, CONTROL_RX_ACK)
    assert backend.read32(REG_STATUS) & STATUS_RX_VALID == 0


def test_send_zero_fills_unused_payload_words() -> None:
    backend = LoopbackMockBackend()
    device = MessageMailbox(backend)
    device.send(b"A", sequence=1)

    assert backend.read32(REG_TX_DATA0) == 0x41
    for index in range(1, 16):
        assert backend.read32(REG_TX_DATA0 + 4 * index) == 0


def test_receive_wait_zero_timeout_returns_none_when_empty() -> None:
    assert MessageMailbox(LoopbackMockBackend()).receive_wait(0.0) is None


def test_busy_rx_mailbox_sets_overflow_without_replacing_message() -> None:
    backend = LoopbackMockBackend()
    device = MessageMailbox(backend)

    device.send(b"first", sequence=1)
    first_word = backend.read32(REG_RX_DATA0)
    device.send(b"second", sequence=2)

    assert backend.read32(REG_STATUS) & STATUS_RX_OVERFLOW
    assert backend.read32(REG_RX_SEQUENCE) == 1
    assert backend.read32(REG_RX_DATA0) == first_word


def test_sequence_must_fit_uint32() -> None:
    device = MessageMailbox(LoopbackMockBackend())
    with pytest.raises(ValueError, match="sequence must fit"):
        device.send(b"x", sequence=-1)
    with pytest.raises(ValueError, match="sequence must fit"):
        device.send(b"x", sequence=0x1_0000_0000)


def test_utf8_payload_limit_is_measured_in_bytes() -> None:
    device = MessageMailbox(LoopbackMockBackend())
    payload = "Я" * 33
    assert len(payload.encode("utf-8")) == 66
    with pytest.raises(ValueError, match="mailbox limit"):
        device.send(payload.encode("utf-8"), sequence=3)
