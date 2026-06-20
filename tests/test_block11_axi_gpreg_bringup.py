from __future__ import annotations

import sys
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1] / "blocks" / "block_11_integrated_sdr_project" / "python"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from lab_11_8_axi_gpreg_bpsk_bringup import (  # noqa: E402
    DEFAULT_EXPECTED_ID,
    BringupConfig,
    MockRegisterIo,
    REGS,
    run_bringup,
)


def make_config(**overrides: int | str | bool | None) -> BringupConfig:
    payload = {
        "backend": "mock",
        "base_addr": 0x79040000,
        "frame_bit_count": 281,
        "preamble_count": 25,
        "start_offset": 62,
        "start_hold_ms": 0,
        "poll_limit": 32,
        "poll_delay_ms": 0,
        "expected_id": DEFAULT_EXPECTED_ID,
        "clear_done": True,
        "max_total_errors": 0,
        "max_payload_errors": 0,
    }
    payload.update(overrides)
    return BringupConfig(**payload)


def test_run_bringup_completes_with_mock_backend() -> None:
    io = MockRegisterIo(busy_reads_before_done=3)
    result = run_bringup(io, make_config())

    assert result.id_word == DEFAULT_EXPECTED_ID
    assert result.signature_word == DEFAULT_EXPECTED_ID
    assert result.busy_observed is True
    assert result.done_observed is True
    assert result.received_bits == 281
    assert result.total_errors == 0
    assert result.payload_errors == 0
    assert result.done_cleared is True
    assert result.register_snapshot["GP_SIGNATURE_IN"]["value"] == DEFAULT_EXPECTED_ID


def test_run_bringup_raises_on_signature_mismatch() -> None:
    io = MockRegisterIo()
    io.regs[REGS.gp_signature_in] = 0x12345678

    try:
        run_bringup(io, make_config())
    except RuntimeError as exc:
        assert "Unexpected bridge signature" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected signature mismatch failure.")


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
        assert "never asserted done" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected gpreg timeout failure.")
