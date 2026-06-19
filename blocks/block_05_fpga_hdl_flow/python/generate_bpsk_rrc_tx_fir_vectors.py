#!/usr/bin/env python3
"""Generate vectors and coefficient memory for the BPSK RRC TX FIR RTL block."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
PACKAGE_DIR = ROOT / "blocks" / "block_11_integrated_sdr_project" / "assets" / "end_to_end_bpsk_reference"
PACKAGE_GENERATOR = (
    ROOT / "blocks" / "block_11_integrated_sdr_project" / "python" / "end_to_end_bpsk_reference.py"
)
TB_DIR = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "tb"
RTL_DIR = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "rtl"
SHIFT = 15


def ensure_package() -> None:
    required = (
        PACKAGE_DIR / "config.json",
        PACKAGE_DIR / "tx_symbols_q15.txt",
        PACKAGE_DIR / "rrc_taps_q15.txt",
    )
    if all(path.is_file() for path in required):
        return

    subprocess.run([sys.executable, str(PACKAGE_GENERATOR)], cwd=ROOT, check=True)


def sat16(value: int) -> int:
    return max(-32768, min(32767, value))


def round_shift(value: int, shift: int = SHIFT) -> int:
    return (value + (1 << (shift - 1))) >> shift


def to_hex16(value: int) -> str:
    return f"{value & 0xFFFF:04x}"


def upsample(symbols_i: np.ndarray, symbols_q: np.ndarray, sps: int) -> tuple[np.ndarray, np.ndarray]:
    up_i = np.zeros(symbols_i.size * sps, dtype=np.int64)
    up_q = np.zeros(symbols_q.size * sps, dtype=np.int64)
    up_i[::sps] = symbols_i
    up_q[::sps] = symbols_q
    return up_i, up_q


def fixed_fir_q15(input_i: np.ndarray, input_q: np.ndarray, taps: np.ndarray) -> list[tuple[int, int, int]]:
    xi = [0] * len(taps)
    xq = [0] * len(taps)
    expected: list[tuple[int, int, int]] = []

    for i_value, q_value in zip(input_i.tolist(), input_q.tolist()):
        acc_i = int(i_value) * int(taps[0])
        acc_q = int(q_value) * int(taps[0])

        for tap_idx in range(1, len(taps)):
            acc_i += int(xi[tap_idx - 1]) * int(taps[tap_idx])
            acc_q += int(xq[tap_idx - 1]) * int(taps[tap_idx])

        yi = sat16(round_shift(acc_i))
        yq = sat16(round_shift(acc_q))
        expected.append((1, yi, yq))

        xi = [int(i_value)] + xi[:-1]
        xq = [int(q_value)] + xq[:-1]

    return expected


def main() -> None:
    ensure_package()
    TB_DIR.mkdir(parents=True, exist_ok=True)
    RTL_DIR.mkdir(parents=True, exist_ok=True)

    cfg = json.loads((PACKAGE_DIR / "config.json").read_text(encoding="utf-8"))
    symbol_pairs = np.loadtxt(PACKAGE_DIR / "tx_symbols_q15.txt", dtype=np.int64)
    taps = np.loadtxt(PACKAGE_DIR / "rrc_taps_q15.txt", dtype=np.int64).reshape(-1)

    symbols_i = symbol_pairs[:, 0].reshape(-1)
    symbols_q = symbol_pairs[:, 1].reshape(-1)
    up_i, up_q = upsample(symbols_i, symbols_q, int(cfg["samples_per_symbol"]))
    tail_zeros = np.zeros(taps.size - 1, dtype=np.int64)
    input_i = np.concatenate([up_i, tail_zeros])
    input_q = np.concatenate([up_q, tail_zeros])

    inputs = [(1, int(i_value), int(q_value)) for i_value, q_value in zip(input_i, input_q)]
    expected = fixed_fir_q15(input_i, input_q, taps)

    input_path = TB_DIR / "bpsk_rrc_tx_fir_input_vectors.txt"
    expected_path = TB_DIR / "bpsk_rrc_tx_fir_expected_vectors.txt"
    mem_path = RTL_DIR / "bpsk_rrc_tx_fir_taps.mem"

    with input_path.open("w", encoding="utf-8") as f:
        f.write("# valid i q\n")
        for valid, i_value, q_value in inputs:
            f.write(f"{valid} {i_value} {q_value}\n")

    with expected_path.open("w", encoding="utf-8") as f:
        f.write("# valid i q\n")
        for valid, i_value, q_value in expected:
            f.write(f"{valid} {i_value} {q_value}\n")

    with mem_path.open("w", encoding="utf-8") as f:
        for tap in taps.tolist():
            f.write(f"{to_hex16(int(tap))}\n")

    print(f"Wrote {input_path}")
    print(f"Wrote {expected_path}")
    print(f"Wrote {mem_path}")
    print(f"Vector count: {len(inputs)}")


if __name__ == "__main__":
    main()
