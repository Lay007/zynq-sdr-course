from __future__ import annotations

import sys
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1] / "blocks" / "block_11_integrated_sdr_project" / "python"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from lab_11_7_axi_lite_bpsk_bringup import (  # noqa: E402
    DEFAULT_EXPECTED_ID,
    BringupConfig,
    MockRegisterIo,
    parse_int,
    parse_devmem_read_output,
    run_bringup,
    SshDevMemRegisterIo,
)


def make_config(**overrides: int | str | bool | None) -> BringupConfig:
    payload = {
        "backend": "mock",
        "base_addr": 0x43C00000,
        "frame_bit_count": 281,
        "preamble_count": 25,
        "start_offset": 62,
        "poll_limit": 32,
        "poll_delay_ms": 0,
        "expected_id": DEFAULT_EXPECTED_ID,
        "clear_done": True,
        "max_total_errors": 0,
        "max_payload_errors": 0,
    }
    payload.update(overrides)
    return BringupConfig(**payload)


def test_parse_int_handles_hex_and_decimal() -> None:
    assert parse_int("62") == 62
    assert parse_int("0x3E") == 62


def test_parse_devmem_read_output_uses_last_non_empty_line() -> None:
    assert parse_devmem_read_output("\n0x4250534B\n") == DEFAULT_EXPECTED_ID


def test_run_bringup_completes_with_mock_backend() -> None:
    io = MockRegisterIo(busy_reads_before_done=3)
    result = run_bringup(io, make_config())

    assert result.id_word == DEFAULT_EXPECTED_ID
    assert result.busy_observed is True
    assert result.done_observed is True
    assert result.received_bits == 281
    assert result.total_errors == 0
    assert result.payload_errors == 0
    assert result.done_cleared is True
    assert result.register_snapshot["ID"]["value"] == DEFAULT_EXPECTED_ID


def test_run_bringup_raises_on_payload_error_threshold() -> None:
    io = MockRegisterIo(payload_errors=2)
    cfg = make_config(max_total_errors=None, max_payload_errors=0)

    try:
        run_bringup(io, cfg)
    except RuntimeError as exc:
        assert "payload_errors=2" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected payload error threshold failure.")


def test_run_bringup_times_out_when_done_never_arrives() -> None:
    io = MockRegisterIo(busy_reads_before_done=100)
    cfg = make_config(poll_limit=2, max_total_errors=None, max_payload_errors=None)

    try:
        run_bringup(io, cfg)
    except TimeoutError as exc:
        assert "did not assert done" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected AXI-Lite timeout failure.")


class FakeRunner:
    def __init__(self, responses: dict[str, tuple[int, str, str]]) -> None:
        self.responses = responses
        self.commands: list[str] = []
        self.closed = False

    def __call__(self, command: str) -> tuple[int, str, str]:
        self.commands.append(command)
        return self.responses[command]

    def close(self) -> None:
        self.closed = True


def test_ssh_devmem_backend_reads_and_writes_through_runner() -> None:
    runner = FakeRunner(
        {
            "/sbin/devmem 0x43C0001C 32": (0, "0x4250534B\n", ""),
            "/sbin/devmem 0x43C00004 32 0x119": (0, "", ""),
        }
    )
    io = SshDevMemRegisterIo(0x43C00000, command_runner=runner)

    assert io.read32(0x1C) == DEFAULT_EXPECTED_ID
    io.write32(0x04, 281)
    io.close()

    assert runner.commands == [
        "/sbin/devmem 0x43C0001C 32",
        "/sbin/devmem 0x43C00004 32 0x119",
    ]
    assert runner.closed is True


def test_ssh_devmem_backend_surfaces_bus_error() -> None:
    runner = FakeRunner(
        {
            "/sbin/devmem 0x43C0001C 32": (1, "", "Bus error\n"),
        }
    )
    io = SshDevMemRegisterIo(0x43C00000, command_runner=runner)

    try:
        io.read32(0x1C)
    except RuntimeError as exc:
        assert "Bus error" in str(exc)
        assert "0x43C0001C" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected ssh-devmem bus-error failure.")
