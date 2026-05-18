#!/usr/bin/env python3
"""Lab 5.5 - Float vs fixed-point vs RTL comparison for FIR block."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
TB_DIR = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "tb"
ASSET_DIR = ROOT / "docs" / "assets"

H_FLOAT = np.array([0.125, 0.375, 0.375, 0.125], dtype=np.float64)
H_Q15 = np.array([4096, 12288, 12288, 4096], dtype=np.int64)
SHIFT = 15


@dataclass(frozen=True)
class ComparisonMetrics:
    samples_compared: int
    rmse_float_vs_rtl: float
    rmse_fixed_vs_rtl: float
    max_abs_float_vs_rtl: float
    max_abs_fixed_vs_rtl: float
    pass_float_within_1_lsb: bool
    pass_fixed_exact_match: bool


def run_vector_generator() -> None:
    cmd = [sys.executable, "blocks/block_05_fpga_hdl_flow/python/generate_fir_iq_4tap_vectors.py"]
    subprocess.run(cmd, cwd=ROOT, check=True)


def read_vectors(path: Path) -> np.ndarray:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        v, i, q = line.split()
        rows.append((int(v), int(i), int(q)))
    return np.array(rows, dtype=np.int64)


def sat16(x: int) -> int:
    return int(max(-32768, min(32767, x)))


def round_shift(x: int, shift: int = SHIFT) -> int:
    return int((x + (1 << (shift - 1))) >> shift)


def fixed_fir_model(inputs: np.ndarray) -> np.ndarray:
    xi = [0, 0, 0, 0]
    xq = [0, 0, 0, 0]
    out = []
    for valid, i_s, q_s in inputs:
        if valid:
            xi = [int(i_s)] + xi[:3]
            xq = [int(q_s)] + xq[:3]
            acc_i = sum(v * c for v, c in zip(xi, H_Q15))
            acc_q = sum(v * c for v, c in zip(xq, H_Q15))
            yi = sat16(round_shift(acc_i))
            yq = sat16(round_shift(acc_q))
            out.append((1, yi, yq))
        else:
            out.append((0, 0, 0))
    return np.array(out, dtype=np.int64)


def float_fir_model(inputs: np.ndarray) -> np.ndarray:
    xi = [0.0, 0.0, 0.0, 0.0]
    xq = [0.0, 0.0, 0.0, 0.0]
    out = []
    for valid, i_s, q_s in inputs:
        if valid:
            xi = [float(i_s)] + xi[:3]
            xq = [float(q_s)] + xq[:3]
            yi = float(np.dot(np.array(xi), H_FLOAT))
            yq = float(np.dot(np.array(xq), H_FLOAT))
            out.append((1, yi, yq))
        else:
            out.append((0, 0.0, 0.0))
    return np.array(out, dtype=np.float64)


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    run_vector_generator()

    inputs = read_vectors(TB_DIR / "fir_iq_4tap_input_vectors.txt")
    rtl = read_vectors(TB_DIR / "fir_iq_4tap_expected_vectors.txt")
    fixed = fixed_fir_model(inputs)
    flt = float_fir_model(inputs)

    valid_mask = rtl[:, 0] == 1
    rtl_iq = rtl[valid_mask, 1:].astype(np.float64)
    fixed_iq = fixed[valid_mask, 1:].astype(np.float64)
    flt_iq = flt[valid_mask, 1:]

    err_float = flt_iq - rtl_iq
    err_fixed = fixed_iq - rtl_iq

    metrics = ComparisonMetrics(
        samples_compared=int(np.sum(valid_mask)),
        rmse_float_vs_rtl=float(np.sqrt(np.mean(err_float**2))),
        rmse_fixed_vs_rtl=float(np.sqrt(np.mean(err_fixed**2))),
        max_abs_float_vs_rtl=float(np.max(np.abs(err_float))),
        max_abs_fixed_vs_rtl=float(np.max(np.abs(err_fixed))),
        pass_float_within_1_lsb=bool(np.max(np.abs(err_float)) <= 1.0),
        pass_fixed_exact_match=bool(np.max(np.abs(err_fixed)) == 0.0),
    )

    plot_path = ASSET_DIR / "lab55_float_fixed_rtl_error.png"
    table_path = ASSET_DIR / "lab55_float_fixed_rtl_resource_table.md"
    metrics_path = ASSET_DIR / "lab55_float_fixed_rtl_metrics.json"

    bars = [
        metrics.rmse_float_vs_rtl,
        metrics.rmse_fixed_vs_rtl,
        metrics.max_abs_float_vs_rtl,
        metrics.max_abs_fixed_vs_rtl,
    ]
    labels = [
        "RMSE float-RTL",
        "RMSE fixed-RTL",
        "MAX |float-RTL|",
        "MAX |fixed-RTL|",
    ]
    plt.figure(figsize=(8.0, 4.3))
    plt.bar(labels, bars)
    plt.grid(True, axis="y", alpha=0.35)
    plt.ylabel("Error in Q1.15 LSB units")
    plt.title("Lab 5.5 - Float/fixed/RTL error comparison")
    plt.xticks(rotation=12)
    plt.tight_layout()
    plt.savefig(plot_path, dpi=180)
    plt.close()

    resource_table = """# Lab 5.5 resource and latency comparison

| Implementation | Numerical model | Typical FPGA resources* | Latency (cycles) | Notes |
|---|---|---|---:|---|
| Python float | float64 reference | N/A (software) | N/A | best analytical reference |
| Python fixed-point | Q1.15 emulation | N/A (software) | N/A | mirrors hardware quantization |
| RTL FIR 4-tap | Q1.15 integer MAC | ~4 multipliers, ~3 adders, registers | 1-2 | synthesizable datapath |

*Resource row is an educational estimate for architecture discussion.
"""
    table_path.write_text(resource_table, encoding="utf-8")
    metrics_path.write_text(
        json.dumps({"metrics": asdict(metrics)}, indent=2),
        encoding="utf-8",
    )

    print("Lab 5.5 - Float vs fixed vs RTL comparison")
    print(f"Compared valid samples: {metrics.samples_compared}")
    print(f"RMSE float-RTL: {metrics.rmse_float_vs_rtl:.4f} LSB")
    print(f"RMSE fixed-RTL: {metrics.rmse_fixed_vs_rtl:.4f} LSB")
    print(f"MAX |float-RTL|: {metrics.max_abs_float_vs_rtl:.4f} LSB")
    print(f"MAX |fixed-RTL|: {metrics.max_abs_fixed_vs_rtl:.4f} LSB")
    print(f"Fixed exact match with RTL: {metrics.pass_fixed_exact_match}")
    print(f"Metrics JSON: {metrics_path}")


if __name__ == "__main__":
    main()
