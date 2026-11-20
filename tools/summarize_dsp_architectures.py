#!/usr/bin/env python3
"""Combine Icarus metrics and comparable Vivado reports for Lab 5.14."""

import argparse
import hashlib
import json
from pathlib import Path

from run_dsp_architectures import BLOCK5, BLOCK8, ROOT
from summarize_fir_architectures import read_routed


def summarize(simulation: Path, nco_reports: Path, fft_reports: Path) -> dict:
    result = {"post_route_ooc": {}}
    for family, reports in (("nco", nco_reports), ("fft", fft_reports)):
        metrics = json.loads((simulation / f"{family}_simulation.json").read_text(encoding="utf-8"))
        for name, variant in metrics["variants"].items():
            metadata, resources = read_routed(reports, name)
            if result["post_route_ooc"] and result["post_route_ooc"] != metadata:
                raise ValueError("The Vivado tool, part or clock differs between variants")
            result["post_route_ooc"] = metadata
            variant["post_route_ooc"] = resources
        result[family] = metrics

    sources = [
        BLOCK5 / "rtl/nco_phase_architectures.sv",
        BLOCK5 / "tb/tb_nco_phase_architectures.sv",
        BLOCK8 / "tb/tb_ofdm_fft64_sequential.sv",
        ROOT / "tools/run_dsp_architectures.py",
        ROOT / "tools/vivado_dsp_architectures.tcl",
        ROOT / "tools/fir_architectures_ooc.xdc",
        ROOT / "tools/ofdm_fft_fixed.py", ROOT / "tools/ofdm_ifft_fixed.py",
        *[BLOCK8 / "rtl" / f"{name}.v" for name in (
            "ofdm_fft64_sequential", "ofdm_ifft64_sequential", "ofdm_ifft_butterfly", "ofdm_iq_bank_ram",
        )],
        *[ROOT / "verification/vectors" / f"block08_ofdm_{kind}_bin1_expected.mem"
          for kind in ("ifft", "fft")],
    ]
    result["source_sha256_lf"] = {
        source.relative_to(ROOT).as_posix(): hashlib.sha256(
            source.read_bytes().replace(b"\r\n", b"\n"),
        ).hexdigest() for source in sources
    }
    result["nco"]["quarter_wave_rom_sha256_lf"] = hashlib.sha256(
        (simulation / "nco_quarter_q15.mem").read_bytes().replace(b"\r\n", b"\n"),
    ).hexdigest()
    return result


def plot(result: dict, output: Path, *, russian: bool) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(2, 2, figsize=(9, 6.3), layout="constrained")
    nco = result["nco"]["variants"]
    fft = result["fft"]["variants"]
    nco_labels = ("LUT", "CORDIC")
    fft_labels = ("Исходный", "Конвейер,\nлогика", "Конвейер,\nBRAM") if russian else (
        "Baseline", "Pipelined,\nfabric", "Pipelined,\nBRAM",
    )
    for axis, labels, values, ylabel in (
        (axes[0, 0], nco_labels,
         [r["sfdr_dbc"] for r in nco.values()],
         "Динамический диапазон SFDR, дБн" if russian else "Spur-free dynamic range (dBc)"),
        (axes[0, 1], nco_labels,
         [r["ii_clocks"] for r in nco.values()],
         "Интервал приёма фазы, такты" if russian else "Phase initiation interval (clocks)"),
        (axes[1, 0], fft_labels,
         [r["frame_ii_clocks"] for r in fft.values()],
         "Интервал между кадрами, такты" if russian else "Frame initiation interval (clocks)"),
        (axes[1, 1], fft_labels,
         [r["post_route_ooc"]["slice_luts"] for r in fft.values()],
         "Число LUT после трассировки" if russian else "Routed slice LUTs"),
    ):
        bars = axis.bar(labels, values, color=("#226184", "#a04018", "#2e7555")[:len(labels)], width=0.55)
        axis.bar_label(bars, fmt="%.2f" if axis is axes[0, 0] else "%.0f", padding=3)
        axis.set_ylabel(ylabel)
        axis.margins(y=0.16)
        axis.grid(axis="y", alpha=0.24)
        axis.set_axisbelow(True)
    figure.suptitle("Архитектуры генератора NCO и БПФ" if russian else "NCO and FFT architectures")
    figure.savefig(output, dpi=165)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("simulation", type=Path)
    parser.add_argument("nco_reports", type=Path)
    parser.add_argument("fft_reports", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = summarize(args.simulation, args.nco_reports, args.fft_reports)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "lab514_dsp_architectures.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n",
    )
    plot(result, args.output / "lab514_dsp_architectures.png", russian=False)
    plot(result, args.output / "lab514_dsp_architectures_ru.png", russian=True)


if __name__ == "__main__":
    main()
