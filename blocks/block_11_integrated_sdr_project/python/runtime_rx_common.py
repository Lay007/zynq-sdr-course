#!/usr/bin/env python3
"""Helpers for the AD9361 RX common control block after runtime FPGA reloads."""

from __future__ import annotations

import time
from typing import Any

from lab_11_12_runtime_fpga_manager_reload import run_remote


RX_COMMON_REGS = {
    "rx_common_ctrl_req": 0x79020040,
    "rx_common_mode": 0x79020044,
    "rx_common_clk_count": 0x79020054,
    "rx_common_status": 0x7902005C,
    "rx_common_sync_status": 0x79020068,
    "rx_delay_probe0": 0x79020800,
}


def read_remote_devmem32(runner: Any, address: int) -> int:
    return int(
        run_remote(runner, f"/sbin/devmem 0x{address:X} 32", context=f"read 0x{address:X}"),
        0,
    )


def write_remote_devmem32(runner: Any, address: int, value: int) -> None:
    run_remote(
        runner,
        f"/sbin/devmem 0x{address:X} 32 0x{value & 0xFFFFFFFF:X}",
        context=f"write 0x{address:X}",
    )


def read_named_registers(runner: Any, registers: dict[str, int]) -> dict[str, str]:
    return {
        name: f"0x{read_remote_devmem32(runner, address):08X}"
        for name, address in registers.items()
    }


def read_rx_common_snapshot(runner: Any) -> dict[str, str]:
    return read_named_registers(runner, RX_COMMON_REGS)


def force_rx_common_ctrl_request(
    runner: Any,
    *,
    value: int = 0x00000003,
    settle_s: float = 0.5,
) -> dict[str, Any]:
    before = read_rx_common_snapshot(runner)
    write_remote_devmem32(runner, RX_COMMON_REGS["rx_common_ctrl_req"], value)
    if settle_s > 0:
        time.sleep(settle_s)
    after = read_rx_common_snapshot(runner)
    return {
        "write_address": f"0x{RX_COMMON_REGS['rx_common_ctrl_req']:08X}",
        "write_value": f"0x{value & 0xFFFFFFFF:08X}",
        "before": before,
        "after": after,
    }
