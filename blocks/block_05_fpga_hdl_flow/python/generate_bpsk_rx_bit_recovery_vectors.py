#!/usr/bin/env python3
"""Generate vectors for deterministic BPSK RX bit recovery."""

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
Q15_SCALE = 32767.0


def ensure_package() -> None:
    required = (
        PACKAGE_DIR / "config.json",
        PACKAGE_DIR / "sample_plan.json",
        PACKAGE_DIR / "tx_bits.txt",
        PACKAGE_DIR / "rrc_taps_q15.txt",
    )
    if all(path.is_file() for path in required):
        return

    subprocess.run([sys.executable, str(PACKAGE_GENERATOR)], cwd=ROOT, check=True)


def clip_int16(values: np.ndarray) -> np.ndarray:
    return np.clip(np.round(values), -32768, 32767).astype(np.int16)


def read_ci16(path: Path) -> np.ndarray:
    raw = np.fromfile(path, dtype="<i2").astype(np.float64)
    if raw.size % 2 != 0:
        raise ValueError(f"invalid CI16 file: {path}")
    return raw[0::2] / 32768.0 + 1j * raw[1::2] / 32768.0


def fixed_fir_q15(x: np.ndarray, taps_q15: np.ndarray) -> np.ndarray:
    xi = clip_int16(np.real(x) * Q15_SCALE)
    xq = clip_int16(np.imag(x) * Q15_SCALE)
    y = np.zeros(xi.size, dtype=np.complex128)

    for n in range(xi.size):
        acc_i = int(xi[n]) * int(taps_q15[0])
        acc_q = int(xq[n]) * int(taps_q15[0])
        for tap_idx in range(1, taps_q15.size):
            idx = n - tap_idx
            if idx < 0:
                break
            acc_i += int(xi[idx]) * int(taps_q15[tap_idx])
            acc_q += int(xq[idx]) * int(taps_q15[tap_idx])

        yi = (acc_i + (1 << 14)) >> 15
        yq = (acc_q + (1 << 14)) >> 15
        yi = max(-32768, min(32767, yi))
        yq = max(-32768, min(32767, yq))
        y[n] = complex(yi, yq)

    return y


def main() -> None:
    ensure_package()
    TB_DIR.mkdir(parents=True, exist_ok=True)

    cfg = json.loads((PACKAGE_DIR / "config.json").read_text(encoding="utf-8"))
    sample_plan = json.loads((PACKAGE_DIR / "sample_plan.json").read_text(encoding="utf-8"))
    tx_bits = np.loadtxt(PACKAGE_DIR / "tx_bits.txt", dtype=np.int16).reshape(-1)
    taps_q15 = np.loadtxt(PACKAGE_DIR / "rrc_taps_q15.txt", dtype=np.int16).reshape(-1)
    capture = read_ci16(PACKAGE_DIR / f"{cfg['dataset_id']}.ci16")

    t = np.arange(capture.size, dtype=np.float64) / cfg["sample_rate_hz"]
    corrected = capture * np.exp(-1j * (2.0 * np.pi * cfg["cfo_hz"] * t + cfg["phase_offset_rad"]))
    corrected = np.concatenate([corrected, np.zeros(taps_q15.size - 1, dtype=np.complex128)])
    corrected_i = clip_int16(np.real(corrected) * Q15_SCALE)
    corrected_q = clip_int16(np.imag(corrected) * Q15_SCALE)

    matched = fixed_fir_q15(corrected, taps_q15)
    start = int(sample_plan["matched_filter_sample_start"])
    sps = int(sample_plan["samples_per_symbol"])
    recovered_symbols = matched[start::sps][: tx_bits.size]
    recovered_bits = (np.real(recovered_symbols) < 0).astype(np.int16)

    total_errors = int(np.sum(recovered_bits != tx_bits))
    preamble_count = len(cfg["preamble_bits"])
    payload_errors = int(np.sum(recovered_bits[preamble_count:] != tx_bits[preamble_count:]))
    if total_errors != 0:
        raise ValueError(
            f"expected zero bit errors for the deterministic RX chain, got total={total_errors}, payload={payload_errors}"
        )

    input_path = TB_DIR / "bpsk_rx_bit_recovery_input_vectors.txt"
    expected_path = TB_DIR / "bpsk_rx_bit_recovery_expected_bits.txt"
    meta_path = TB_DIR / "bpsk_rx_bit_recovery_meta.txt"

    with input_path.open("w", encoding="utf-8") as f:
        f.write("# valid i q\n")
        for i_value, q_value in zip(corrected_i.tolist(), corrected_q.tolist()):
            f.write(f"1 {int(i_value)} {int(q_value)}\n")

    with expected_path.open("w", encoding="utf-8") as f:
        f.write("# valid bit\n")
        for bit in recovered_bits.tolist():
            f.write(f"1 {int(bit)}\n")

    with meta_path.open("w", encoding="utf-8") as f:
        f.write("# start_offset sps bit_count preamble_count\n")
        f.write(f"{start} {sps} {tx_bits.size} {preamble_count}\n")

    print(f"Wrote {input_path}")
    print(f"Wrote {expected_path}")
    print(f"Wrote {meta_path}")
    print(f"Recovered bits: {tx_bits.size}, total errors: {total_errors}, payload errors: {payload_errors}")


if __name__ == "__main__":
    main()
