from pathlib import Path

import pytest

from tools.css_axi_bringup import (
    CONTROL_CLEAR_COUNTERS,
    CONTROL_CLEAR_DONE,
    CONTROL_CLEAR_FRAME_ERROR,
    CONTROL_IRQ_ENABLE,
    CORE_ID,
    CssAxiDevice,
    MockRegisterBackend,
    REG_COMPLETED_COUNT,
    REG_CONTROL,
    REG_FRAME_ERROR_COUNT,
    REG_ID,
    REG_RESULT0,
    REG_STATUS,
)


def test_probe_and_status_decode() -> None:
    backend = MockRegisterBackend(
        {
            REG_ID: CORE_ID,
            0x04: 0x00010000,
            REG_STATUS: 0b11011,
            REG_COMPLETED_COUNT: 17,
            REG_FRAME_ERROR_COUNT: 3,
        }
    )
    device = CssAxiDevice(backend)

    assert device.probe() == (CORE_ID, 0x00010000)
    status = device.read_status()
    assert status.busy is True
    assert status.input_ready is True
    assert status.result_pending is False
    assert status.done_sticky is True
    assert status.frame_error_sticky is True
    assert status.completed_count == 17
    assert status.frame_error_count == 3


def test_probe_rejects_wrong_core() -> None:
    device = CssAxiDevice(MockRegisterBackend({REG_ID: 0xDEADBEEF}))
    with pytest.raises(RuntimeError, match="unexpected CSS core ID"):
        device.probe()


def test_control_pulses_preserve_irq_enable() -> None:
    backend = MockRegisterBackend({REG_CONTROL: CONTROL_IRQ_ENABLE})
    device = CssAxiDevice(backend)

    device.clear_done()
    assert backend.writes[-1] == (
        REG_CONTROL,
        CONTROL_IRQ_ENABLE | CONTROL_CLEAR_DONE,
    )

    device.clear_frame_error()
    assert backend.writes[-1] == (
        REG_CONTROL,
        CONTROL_IRQ_ENABLE | CONTROL_CLEAR_FRAME_ERROR,
    )

    device.clear_counters()
    assert backend.writes[-1] == (
        REG_CONTROL,
        CONTROL_IRQ_ENABLE | CONTROL_CLEAR_COUNTERS,
    )

    device.clear_sticky_and_counters()
    assert backend.writes[-1] == (
        REG_CONTROL,
        CONTROL_IRQ_ENABLE
        | CONTROL_CLEAR_DONE
        | CONTROL_CLEAR_FRAME_ERROR
        | CONTROL_CLEAR_COUNTERS,
    )


def test_irq_enable_write() -> None:
    backend = MockRegisterBackend()
    device = CssAxiDevice(backend)

    device.set_irq_enable(True)
    assert backend.writes[-1] == (REG_CONTROL, CONTROL_IRQ_ENABLE)
    device.set_irq_enable(False)
    assert backend.writes[-1] == (REG_CONTROL, 0)


def test_result_decode_matches_rtl_packet_layout() -> None:
    word0 = 37 | (91 << 8) | (1 << 15) | (12 << 16)
    words = (
        word0,
        0x89ABCDEF,
        0x01234567,
        0x76543210,
        0xFEDCBA98,
        0,
        0,
        0,
    )

    result = CssAxiDevice.decode_result(words, completed_count=23)
    assert result.peak_bin == 37
    assert result.second_bin == 91
    assert result.frame_error is True
    assert result.saturation_count == 12
    assert result.peak_magnitude_squared == 0x0123456789ABCDEF
    assert result.second_magnitude_squared == 0xFEDCBA9876543210
    assert result.completed_count == 23
    assert result.raw_words == words


def test_result_decode_requires_eight_words() -> None:
    with pytest.raises(ValueError, match="exactly eight"):
        CssAxiDevice.decode_result((0,) * 7)


class CountSequenceBackend(MockRegisterBackend):
    def __init__(self, counts: list[int], registers: dict[int, int]) -> None:
        super().__init__(registers)
        self._counts = iter(counts)

    def read32(self, offset: int) -> int:
        if offset == REG_COMPLETED_COUNT:
            return next(self._counts)
        return super().read32(offset)


def test_coherent_result_retries_if_counter_changes() -> None:
    registers = {REG_RESULT0 + 4 * index: index + 1 for index in range(8)}
    backend = CountSequenceBackend([4, 5, 5, 5], registers)

    result = CssAxiDevice(backend).read_result_coherent(max_attempts=2)
    assert result.completed_count == 5
    assert result.raw_words == tuple(range(1, 9))


def test_coherent_result_rejects_repeated_torn_reads() -> None:
    registers = {REG_RESULT0 + 4 * index: index for index in range(8)}
    backend = CountSequenceBackend([1, 2, 3, 4], registers)

    with pytest.raises(RuntimeError, match="changed during every"):
        CssAxiDevice(backend).read_result_coherent(max_attempts=2)


def test_coherent_result_requires_positive_attempt_count() -> None:
    with pytest.raises(ValueError, match="at least one"):
        CssAxiDevice(MockRegisterBackend()).read_result_coherent(max_attempts=0)


def test_mock_json_offset_parsing(tmp_path: Path) -> None:
    from tools.css_axi_bringup import _load_mock

    path = tmp_path / "css-registers.json"
    path.write_text('{"0x00": "0x43535337", "0x30": 9}', encoding="utf-8")

    backend = _load_mock(path)
    assert backend.read32(REG_ID) == CORE_ID
    assert backend.read32(REG_COMPLETED_COUNT) == 9
