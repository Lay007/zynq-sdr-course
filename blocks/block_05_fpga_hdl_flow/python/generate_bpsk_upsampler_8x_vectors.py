#!/usr/bin/env python3
"""Generate deterministic vectors for the BPSK 8x symbol upsampler."""

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


def ensure_package() -> None:
    required = (
        PACKAGE_DIR / "config.json",
        PACKAGE_DIR / "tx_symbols_q15.txt",
    )
    if all(path.is_file() for path in required):
        return

    subprocess.run([sys.executable, str(PACKAGE_GENERATOR)], cwd=ROOT, check=True)


def main() -> None:
    ensure_package()
    TB_DIR.mkdir(parents=True, exist_ok=True)

    cfg = json.loads((PACKAGE_DIR / "config.json").read_text(encoding="utf-8"))
    symbol_pairs = np.loadtxt(PACKAGE_DIR / "tx_symbols_q15.txt", dtype=np.int64)
    sps = int(cfg["samples_per_symbol"])

    symbol_i = symbol_pairs[:, 0].reshape(-1)
    symbol_q = symbol_pairs[:, 1].reshape(-1)

    up_i = np.zeros(symbol_i.size * sps, dtype=np.int64)
    up_q = np.zeros(symbol_q.size * sps, dtype=np.int64)
    up_i[::sps] = symbol_i
    up_q[::sps] = symbol_q

    input_path = TB_DIR / "bpsk_upsampler_8x_input_vectors.txt"
    expected_path = TB_DIR / "bpsk_upsampler_8x_expected_vectors.txt"

    with input_path.open("w", encoding="utf-8") as f:
        f.write("# i q\n")
        for i_value, q_value in zip(symbol_i.tolist(), symbol_q.tolist()):
            f.write(f"{int(i_value)} {int(q_value)}\n")

    with expected_path.open("w", encoding="utf-8") as f:
        f.write("# valid i q\n")
        for i_value, q_value in zip(up_i.tolist(), up_q.tolist()):
            f.write(f"1 {int(i_value)} {int(q_value)}\n")

    print(f"Wrote {input_path}")
    print(f"Wrote {expected_path}")
    print(f"Symbol count: {symbol_i.size}")
    print(f"Output sample count: {up_i.size}")


if __name__ == "__main__":
    main()
