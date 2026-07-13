#!/usr/bin/env python3
"""Run the canonical Block 5 HDL smoke suite on Windows, Linux, or macOS."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TB_DIR = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "tb"
RTL_DIR = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "rtl"
PY_DIR = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "python"
BRIDGE_DIR = ROOT / "hardware" / "7020_ad936x_sdr" / "hdl" / "course_bpsk_fmcomms2_zc702"


@dataclass(frozen=True)
class HdlTest:
    name: str
    sources: tuple[Path, ...]


def rtl(*names: str) -> tuple[Path, ...]:
    return tuple(RTL_DIR / name for name in names)


def tb(name: str) -> Path:
    return TB_DIR / name


def merge(*groups: tuple[Path, ...]) -> tuple[Path, ...]:
    """Concatenate source groups, dropping repeats — iverilog rejects a file twice."""
    seen: dict[Path, None] = {}
    for group in groups:
        for path in group:
            seen.setdefault(path, None)
    return tuple(seen)


COMMON_BPSK = rtl(
    "bpsk_symbol_mapper.v",
    "bpsk_upsampler_8x.v",
    "bpsk_rrc_tx_fir.v",
    "bpsk_rrc_rx_fir.v",
    "bpsk_symbol_timing_sampler.v",
    "bpsk_symbol_timing_recovery.v",
    "bpsk_hard_decision.v",
    "bpsk_framed_tx_chain.v",
    "bpsk_rx_bit_recovery_chain.v",
)

BPSK_TOP = COMMON_BPSK + rtl(
    "bpsk_frame_bit_source.v",
    "bpsk_ber_counter.v",
    "bpsk_zynq_ber_top.v",
)

QPSK_RX_CHAIN = rtl(
    "dc_blocker.v",
    "qpsk_mf_phase_picker.v",
    "bpsk_rrc_rx_fir.v",
    "bpsk_symbol_timing_sampler.v",
    "qpsk_costas.v",
    "qpsk_hard_decision.v",
    "qpsk_rx_bit_recovery_chain.v",
)

QPSK_RX_BENCH = merge(
    QPSK_RX_CHAIN,
    rtl("bpsk_rrc_tx_fir.v", "bpsk_ber_counter.v", "qpsk_ber_counter.v"),
)

QPSK_TOP = merge(
    QPSK_RX_CHAIN,
    rtl(
        "qpsk_symbol_mapper.v",
        "bpsk_upsampler_8x.v",
        "bpsk_rrc_tx_fir.v",
        "qpsk_framed_tx_chain.v",
        "qpsk_frame_dibit_source.v",
        "bpsk_ber_counter.v",
        "qpsk_ber_counter.v",
        "qpsk_zynq_ber_top.v",
    ),
)

QPSK_BRIDGE = merge(
    BPSK_TOP,
    QPSK_RX_CHAIN,
    rtl(
        "qpsk_symbol_mapper.v",
        "qpsk_framed_tx_chain.v",
        "qpsk_frame_dibit_source.v",
        "qpsk_ber_counter.v",
        "qpsk_zynq_ber_top.v",
    ),
    (
        BRIDGE_DIR / "bridge_rx_lclk_fifo.v",
        BRIDGE_DIR / "bpsk_zynq_ber_gpreg_bridge.v",
    ),
)

TESTS = (
    HdlTest("tb_iq_passthrough", rtl("iq_passthrough.v") + (tb("tb_iq_passthrough.v"),)),
    HdlTest("tb_fir_iq_4tap", rtl("fir_iq_4tap.v") + (tb("tb_fir_iq_4tap.v"),)),
    HdlTest("tb_nco_mixer_iq", rtl("nco_mixer_iq.v") + (tb("tb_nco_mixer_iq.v"),)),
    HdlTest("tb_bpsk_symbol_mapper", rtl("bpsk_symbol_mapper.v") + (tb("tb_bpsk_symbol_mapper.v"),)),
    HdlTest("tb_qpsk_symbol_mapper", rtl("qpsk_symbol_mapper.v") + (tb("tb_qpsk_symbol_mapper.v"),)),
    HdlTest("tb_bpsk_upsampler_8x", rtl("bpsk_upsampler_8x.v") + (tb("tb_bpsk_upsampler_8x.v"),)),
    HdlTest("tb_bpsk_rrc_tx_fir", rtl("bpsk_rrc_tx_fir.v") + (tb("tb_bpsk_rrc_tx_fir.v"),)),
    HdlTest(
        "tb_bpsk_rx_bit_recovery",
        rtl(
            "bpsk_rrc_tx_fir.v",
            "bpsk_rrc_rx_fir.v",
            "bpsk_symbol_timing_sampler.v",
            "bpsk_symbol_timing_recovery.v",
            "bpsk_hard_decision.v",
        ) + (tb("tb_bpsk_rx_bit_recovery.v"),),
    ),
    HdlTest("tb_bpsk_framed_loopback", COMMON_BPSK + (tb("tb_bpsk_framed_loopback.v"),)),
    HdlTest("tb_bpsk_zynq_ber_top", BPSK_TOP + (tb("tb_bpsk_zynq_ber_top.v"),)),
    HdlTest("tb_qpsk_zynq_ber_top", QPSK_TOP + (tb("tb_qpsk_zynq_ber_top.v"),)),
    # Real-capture RX benches. They were absent from this suite while the RX chain grew a
    # DC blocker and a Costas loop, so nothing caught the 90/270-degree frame-sync hole
    # until hardware did. QPSK_RX_BENCH carries everything the RX chain needs.
    HdlTest("tb_qpsk_quadrant_resolve", QPSK_RX_BENCH + (tb("tb_qpsk_quadrant_resolve.v"),)),
    HdlTest("tb_qpsk_costas_acquire", QPSK_RX_BENCH + (tb("tb_qpsk_costas_acquire.v"),)),
    HdlTest("tb_qpsk_costas_multiburst", QPSK_RX_BENCH + (tb("tb_qpsk_costas_multiburst.v"),)),
    HdlTest("tb_qpsk_costas_acq_window", QPSK_RX_BENCH + (tb("tb_qpsk_costas_acq_window.v"),)),
    HdlTest("tb_qpsk_phase_picker", QPSK_RX_BENCH + (tb("tb_qpsk_phase_picker.v"),)),
    HdlTest("tb_qpsk_coarse_cfo", merge(QPSK_RX_BENCH, rtl("qpsk_coarse_cfo.v")) + (tb("tb_qpsk_coarse_cfo.v"),)),
    HdlTest("tb_qpsk_rx_dcblock", QPSK_RX_BENCH + (tb("tb_qpsk_rx_dcblock.v"),)),
    HdlTest("tb_qpsk_rx_costas", QPSK_RX_BENCH + (tb("tb_qpsk_rx_costas.v"),)),
    HdlTest("tb_qpsk_costas_stress", QPSK_RX_BENCH + (tb("tb_qpsk_costas_stress.v"),)),
    HdlTest("tb_qpsk_bridge_loopback", QPSK_BRIDGE + (tb("tb_qpsk_bridge_loopback.v"),)),
    HdlTest(
        "tb_bridge_rx_lclk_fifo",
        (BRIDGE_DIR / "bridge_rx_lclk_fifo.v", tb("tb_bridge_rx_lclk_fifo.v")),
    ),
    HdlTest(
        "tb_bpsk_zynq_ber_top_multiframe",
        BPSK_TOP + (tb("tb_bpsk_zynq_ber_top_multiframe.v"),),
    ),
    HdlTest(
        "tb_bpsk_symbol_timing_recovery",
        rtl("bpsk_symbol_timing_recovery.v") + (tb("tb_bpsk_symbol_timing_recovery.v"),),
    ),
    HdlTest(
        "tb_bpsk_zynq_ber_timing_recovery",
        BPSK_TOP + (tb("tb_bpsk_zynq_ber_timing_recovery.v"),),
    ),
    HdlTest(
        "tb_bpsk_zynq_ber_axi_lite",
        BPSK_TOP + rtl("bpsk_zynq_ber_axi_lite.v") + (tb("tb_bpsk_zynq_ber_axi_lite.v"),),
    ),
    HdlTest("tb_axis_iq_passthrough", rtl("axis_iq_passthrough.v") + (tb("tb_axis_iq_passthrough.v"),)),
)

GENERATORS = (
    PY_DIR / "generate_fir_iq_4tap_vectors.py",
    PY_DIR / "generate_nco_mixer_iq_vectors.py",
    ROOT / "blocks" / "block_11_integrated_sdr_project" / "python" / "end_to_end_bpsk_reference.py",
    PY_DIR / "generate_bpsk_symbol_mapper_vectors.py",
    PY_DIR / "generate_bpsk_upsampler_8x_vectors.py",
    PY_DIR / "generate_bpsk_rrc_tx_fir_vectors.py",
    PY_DIR / "generate_bpsk_rx_bit_recovery_vectors.py",
    PY_DIR / "generate_bpsk_framed_loopback_vectors.py",
    PY_DIR / "generate_bpsk_timing_recovery_vectors.py",
)

REQUIRED_GENERATED_FILES = (
    TB_DIR / "fir_iq_4tap_input_vectors.txt",
    TB_DIR / "fir_iq_4tap_expected_vectors.txt",
    TB_DIR / "nco_mixer_iq_input_vectors.txt",
    TB_DIR / "nco_mixer_iq_expected_vectors.txt",
    TB_DIR / "bpsk_symbol_mapper_input_vectors.txt",
    TB_DIR / "bpsk_symbol_mapper_expected_vectors.txt",
    TB_DIR / "bpsk_upsampler_8x_input_vectors.txt",
    TB_DIR / "bpsk_upsampler_8x_expected_vectors.txt",
    TB_DIR / "bpsk_rrc_tx_fir_input_vectors.txt",
    TB_DIR / "bpsk_rrc_tx_fir_expected_vectors.txt",
    TB_DIR / "bpsk_rx_bit_recovery_input_vectors.txt",
    TB_DIR / "bpsk_rx_bit_recovery_expected_bits.txt",
    TB_DIR / "bpsk_rx_bit_recovery_meta.txt",
    TB_DIR / "bpsk_framed_loopback_input_bits.txt",
    TB_DIR / "bpsk_framed_loopback_expected_bits.txt",
    TB_DIR / "bpsk_framed_loopback_meta.txt",
    TB_DIR / "bpsk_timing_recovery_mf_input.mem",
    TB_DIR / "bpsk_timing_recovery_model_bits.txt",
    TB_DIR / "bpsk_chain_drift_rx.mem",
    RTL_DIR / "bpsk_rrc_tx_fir_taps.mem",
    RTL_DIR / "bpsk_frame_bits.mem",
)

# Committed (not generated) stimulus that testbenches $readmemh by repo-relative path.
# Simulations run from a temporary workspace, so these must be copied in alongside the
# generated vectors -- otherwise $readmemh silently loads an all-zero array and the
# testbench "fails" for reasons that have nothing to do with the RTL.
STATIC_SIM_INPUTS = (
    TB_DIR / "qpsk_selfota_a0_rx.mem",
    TB_DIR / "qpsk_selfota_burst_centred_rx.mem",
    TB_DIR / "qpsk_selfota_burst_halfsym_rx.mem",
    TB_DIR / "framed_cfo25k_rx.mem",
    TB_DIR / "framed_cfo0_rx.mem",
    TB_DIR / "qpsk_selfota_fresh_rx.mem",
    TB_DIR / "qpsk_selfota_stress_rx.mem",
)


def run(command: list[str], *, cwd: Path = ROOT) -> None:
    print(f">>> {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def require_tool(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise FileNotFoundError(f"{name} was not found on PATH")
    return executable


def generate_vectors() -> None:
    for generator in GENERATORS:
        run([sys.executable, str(generator)])


def require_generated_inputs() -> None:
    candidates = REQUIRED_GENERATED_FILES + STATIC_SIM_INPUTS
    missing = [str(path.relative_to(ROOT)) for path in candidates if not path.is_file() or path.stat().st_size == 0]
    if missing:
        raise RuntimeError(f"Missing HDL simulation inputs: {', '.join(missing)}")


def populate_simulation_workspace(workspace: Path) -> None:
    for source in REQUIRED_GENERATED_FILES + STATIC_SIM_INPUTS:
        target = workspace / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def run_tests(*, generate: bool = True) -> None:
    iverilog = require_tool("iverilog")
    vvp = require_tool("vvp")
    if generate:
        generate_vectors()
    require_generated_inputs()
    with tempfile.TemporaryDirectory(prefix="zynq-sdr-hdl-") as temporary_dir:
        workspace = Path(temporary_dir)
        populate_simulation_workspace(workspace)
        for test in TESTS:
            missing_sources = [str(path.relative_to(ROOT)) for path in test.sources if not path.is_file()]
            if missing_sources:
                raise FileNotFoundError(f"{test.name}: missing source(s): {', '.join(missing_sources)}")
            output = workspace / f"{test.name}.out"
            run([iverilog, "-g2012", "-o", str(output), *(str(path) for path in test.sources)])
            run([vvp, str(output)], cwd=workspace)
    print(f"Canonical HDL smoke passed: {len(TESTS)} testbenches.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-generate",
        action="store_true",
        help="Reuse existing generated vectors instead of regenerating them.",
    )
    args = parser.parse_args()
    run_tests(generate=not args.no_generate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
