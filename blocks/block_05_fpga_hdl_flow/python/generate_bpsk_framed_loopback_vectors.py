#!/usr/bin/env python3
"""Generate vectors for the framed BPSK TX/RX HDL loopback."""

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
POS_LEVEL = 32767
NEG_LEVEL = -32767
SHIFT = 15
MAX_FRAME_BITS = 512


def ensure_package() -> None:
    required = (
        PACKAGE_DIR / "config.json",
        PACKAGE_DIR / "tx_bits.txt",
        PACKAGE_DIR / "rrc_taps_q15.txt",
    )
    if all(path.is_file() for path in required):
        return

    subprocess.run([sys.executable, str(PACKAGE_GENERATOR)], cwd=ROOT, check=True)


def sat16(value: int) -> int:
    return max(-32768, min(32767, value))


def round_shift(value: int, shift: int = SHIFT) -> int:
    return (value + (1 << (shift - 1))) >> shift


def map_bits_to_symbols(bits: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    symbols_i = np.where(bits > 0, NEG_LEVEL, POS_LEVEL).astype(np.int64)
    symbols_q = np.zeros(bits.size, dtype=np.int64)
    return symbols_i, symbols_q


def upsample(symbols_i: np.ndarray, symbols_q: np.ndarray, sps: int) -> tuple[np.ndarray, np.ndarray]:
    up_i = np.zeros(symbols_i.size * sps, dtype=np.int64)
    up_q = np.zeros(symbols_q.size * sps, dtype=np.int64)
    up_i[::sps] = symbols_i
    up_q[::sps] = symbols_q
    return up_i, up_q


def fixed_fir_q15(input_i: np.ndarray, input_q: np.ndarray, taps: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    xi = [0] * len(taps)
    xq = [0] * len(taps)
    out_i = np.zeros(input_i.size, dtype=np.int64)
    out_q = np.zeros(input_q.size, dtype=np.int64)

    for idx, (i_value, q_value) in enumerate(zip(input_i.tolist(), input_q.tolist(), strict=True)):
        acc_i = int(i_value) * int(taps[0])
        acc_q = int(q_value) * int(taps[0])

        for tap_idx in range(1, len(taps)):
            acc_i += int(xi[tap_idx - 1]) * int(taps[tap_idx])
            acc_q += int(xq[tap_idx - 1]) * int(taps[tap_idx])

        out_i[idx] = sat16(round_shift(acc_i))
        out_q[idx] = sat16(round_shift(acc_q))

        xi = [int(i_value)] + xi[:-1]
        xq = [int(q_value)] + xq[:-1]

    return out_i, out_q


def find_start_offset(matched_i: np.ndarray, tx_bits: np.ndarray, sps: int) -> int:
    search_limit = min(matched_i.size, 512)

    for start in range(search_limit):
        recovered = (matched_i[start::sps][: tx_bits.size] < 0).astype(np.int16)
        if recovered.size == tx_bits.size and np.array_equal(recovered, tx_bits):
            return start

    raise ValueError("failed to find a deterministic start offset for the HDL framed loopback")


def main() -> None:
    ensure_package()
    TB_DIR.mkdir(parents=True, exist_ok=True)
    RTL_DIR.mkdir(parents=True, exist_ok=True)

    cfg = json.loads((PACKAGE_DIR / "config.json").read_text(encoding="utf-8"))
    tx_bits = np.loadtxt(PACKAGE_DIR / "tx_bits.txt", dtype=np.int16).reshape(-1)
    taps = np.loadtxt(PACKAGE_DIR / "rrc_taps_q15.txt", dtype=np.int64).reshape(-1)

    sps = int(cfg["samples_per_symbol"])
    flush_symbols = (2 * (taps.size - 1) + sps - 1) // sps
    preamble_count = len(cfg["preamble_bits"])

    symbols_i, symbols_q = map_bits_to_symbols(tx_bits)
    flush_i = np.zeros(flush_symbols, dtype=np.int64)
    flush_q = np.zeros(flush_symbols, dtype=np.int64)
    full_symbols_i = np.concatenate([symbols_i, flush_i])
    full_symbols_q = np.concatenate([symbols_q, flush_q])

    up_i, up_q = upsample(full_symbols_i, full_symbols_q, sps)
    tx_i, tx_q = fixed_fir_q15(up_i, up_q, taps)
    matched_i, matched_q = fixed_fir_q15(tx_i, tx_q, taps)

    start_offset = find_start_offset(matched_i, tx_bits, sps)
    recovered = (matched_i[start_offset::sps][: tx_bits.size] < 0).astype(np.int16)
    total_errors = int(np.sum(recovered != tx_bits))
    payload_errors = int(np.sum(recovered[preamble_count:] != tx_bits[preamble_count:]))
    if total_errors != 0:
        raise ValueError(
            f"expected zero framed loopback errors, got total={total_errors}, payload={payload_errors}"
        )

    input_path = TB_DIR / "bpsk_framed_loopback_input_bits.txt"
    expected_path = TB_DIR / "bpsk_framed_loopback_expected_bits.txt"
    meta_path = TB_DIR / "bpsk_framed_loopback_meta.txt"
    mem_path = RTL_DIR / "bpsk_frame_bits.mem"

    with input_path.open("w", encoding="utf-8") as f:
        f.write("# valid bit last\n")
        for idx, bit in enumerate(tx_bits.tolist()):
            last = 1 if idx == tx_bits.size - 1 else 0
            f.write(f"1 {int(bit)} {last}\n")

    with expected_path.open("w", encoding="utf-8") as f:
        f.write("# valid bit\n")
        for bit in tx_bits.tolist():
            f.write(f"1 {int(bit)}\n")

    with meta_path.open("w", encoding="utf-8") as f:
        f.write("# start_offset sps bit_count preamble_count flush_symbols\n")
        f.write(f"{start_offset} {sps} {tx_bits.size} {preamble_count} {flush_symbols}\n")

    with mem_path.open("w", encoding="utf-8") as f:
        for bit in tx_bits.tolist():
            f.write(f"{int(bit):01x}\n")
        for _ in range(MAX_FRAME_BITS - tx_bits.size):
            f.write("0\n")

    print(f"Wrote {input_path}")
    print(f"Wrote {expected_path}")
    print(f"Wrote {meta_path}")
    print(f"Wrote {mem_path}")
    print(
        "Recovered bits: "
        f"{tx_bits.size}, start offset: {start_offset}, flush symbols: {flush_symbols}, "
        f"total errors: {total_errors}, payload errors: {payload_errors}"
    )


if __name__ == "__main__":
    main()
