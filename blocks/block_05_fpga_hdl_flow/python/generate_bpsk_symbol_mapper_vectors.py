#!/usr/bin/env python3
"""Generate deterministic vectors for the BPSK symbol mapper testbench."""

from __future__ import annotations

from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
PACKAGE_DIR = ROOT / "blocks" / "block_11_integrated_sdr_project" / "assets" / "end_to_end_bpsk_reference"
TB_DIR = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "tb"
VECTOR_COUNT = 32
POS_LEVEL = 32767
NEG_LEVEL = -32767


def load_bits() -> np.ndarray:
    bits_path = PACKAGE_DIR / "tx_bits.txt"
    if bits_path.is_file():
        return np.loadtxt(bits_path, dtype=np.int16)

    fallback = np.array(
        [
            0,
            0,
            0,
            0,
            0,
            1,
            1,
            0,
            0,
            1,
            0,
            1,
            0,
            1,
            1,
            0,
            1,
            0,
            0,
            1,
            1,
            1,
            0,
            0,
            0,
            1,
            1,
            1,
            0,
            1,
            0,
            0,
        ],
        dtype=np.int16,
    )
    return fallback


def main() -> None:
    TB_DIR.mkdir(parents=True, exist_ok=True)
    bits = load_bits().astype(np.int16).reshape(-1)[:VECTOR_COUNT]
    inputs = [(1, int(bit)) for bit in bits]
    expected = [(1, POS_LEVEL if bit == 0 else NEG_LEVEL, 0) for bit in bits]

    input_path = TB_DIR / "bpsk_symbol_mapper_input_vectors.txt"
    expected_path = TB_DIR / "bpsk_symbol_mapper_expected_vectors.txt"

    with input_path.open("w", encoding="utf-8") as f:
        f.write("# valid bit\n")
        for valid, bit in inputs:
            f.write(f"{valid} {bit}\n")

    with expected_path.open("w", encoding="utf-8") as f:
        f.write("# valid i q\n")
        for valid, i_value, q_value in expected:
            f.write(f"{valid} {i_value} {q_value}\n")

    print(f"Wrote {input_path}")
    print(f"Wrote {expected_path}")


if __name__ == "__main__":
    main()
