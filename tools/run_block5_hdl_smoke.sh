#!/usr/bin/env bash
# Run the Block 5 HDL smoke suite used by local checks and GitHub Actions.
# The script intentionally keeps all generated vectors and VCD files deterministic.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="${PYTHON_BIN:-python3}"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="${PYTHON_BIN:-python}"
else
  echo "python3/python was not found on PATH; install Python or set PYTHON_BIN." >&2
  exit 1
fi

TB_DIR="blocks/block_05_fpga_hdl_flow/tb"
RTL_DIR="blocks/block_05_fpga_hdl_flow/rtl"
PY_DIR="blocks/block_05_fpga_hdl_flow/python"

"$PYTHON_BIN" "$PY_DIR/generate_fir_iq_4tap_vectors.py"
"$PYTHON_BIN" "$PY_DIR/generate_nco_mixer_iq_vectors.py"
"$PYTHON_BIN" "blocks/block_11_integrated_sdr_project/python/end_to_end_bpsk_reference.py"
"$PYTHON_BIN" "$PY_DIR/generate_bpsk_symbol_mapper_vectors.py"
"$PYTHON_BIN" "$PY_DIR/generate_bpsk_upsampler_8x_vectors.py"
"$PYTHON_BIN" "$PY_DIR/generate_bpsk_rrc_tx_fir_vectors.py"
"$PYTHON_BIN" "$PY_DIR/generate_bpsk_rx_bit_recovery_vectors.py"
"$PYTHON_BIN" "$PY_DIR/generate_bpsk_framed_loopback_vectors.py"
"$PYTHON_BIN" "$PY_DIR/generate_bpsk_timing_recovery_vectors.py"

test -s "$TB_DIR/fir_iq_4tap_input_vectors.txt"
test -s "$TB_DIR/fir_iq_4tap_expected_vectors.txt"
test -s "$TB_DIR/nco_mixer_iq_input_vectors.txt"
test -s "$TB_DIR/nco_mixer_iq_expected_vectors.txt"
test -s "$TB_DIR/bpsk_symbol_mapper_input_vectors.txt"
test -s "$TB_DIR/bpsk_symbol_mapper_expected_vectors.txt"
test -s "$TB_DIR/bpsk_upsampler_8x_input_vectors.txt"
test -s "$TB_DIR/bpsk_upsampler_8x_expected_vectors.txt"
test -s "$TB_DIR/bpsk_rrc_tx_fir_input_vectors.txt"
test -s "$TB_DIR/bpsk_rrc_tx_fir_expected_vectors.txt"
test -s "$TB_DIR/bpsk_rx_bit_recovery_input_vectors.txt"
test -s "$TB_DIR/bpsk_rx_bit_recovery_expected_bits.txt"
test -s "$TB_DIR/bpsk_rx_bit_recovery_meta.txt"
test -s "$TB_DIR/bpsk_framed_loopback_input_bits.txt"
test -s "$TB_DIR/bpsk_framed_loopback_expected_bits.txt"
test -s "$TB_DIR/bpsk_framed_loopback_meta.txt"
test -s "$RTL_DIR/bpsk_rrc_tx_fir_taps.mem"
test -s "$RTL_DIR/bpsk_frame_bits.mem"

iverilog -g2012 -o "$TB_DIR/tb_iq_passthrough.out" \
  "$RTL_DIR/iq_passthrough.v" \
  "$TB_DIR/tb_iq_passthrough.v"
vvp "$TB_DIR/tb_iq_passthrough.out"

iverilog -g2012 -o "$TB_DIR/tb_fir_iq_4tap.out" \
  "$RTL_DIR/fir_iq_4tap.v" \
  "$TB_DIR/tb_fir_iq_4tap.v"
vvp "$TB_DIR/tb_fir_iq_4tap.out"

iverilog -g2012 -o "$TB_DIR/tb_nco_mixer_iq.out" \
  "$RTL_DIR/nco_mixer_iq.v" \
  "$TB_DIR/tb_nco_mixer_iq.v"
vvp "$TB_DIR/tb_nco_mixer_iq.out"

iverilog -g2012 -o "$TB_DIR/tb_bpsk_symbol_mapper.out" \
  "$RTL_DIR/bpsk_symbol_mapper.v" \
  "$TB_DIR/tb_bpsk_symbol_mapper.v"
vvp "$TB_DIR/tb_bpsk_symbol_mapper.out"

iverilog -g2012 -o "$TB_DIR/tb_qpsk_symbol_mapper.out" \
  "$RTL_DIR/qpsk_symbol_mapper.v" \
  "$TB_DIR/tb_qpsk_symbol_mapper.v"
vvp "$TB_DIR/tb_qpsk_symbol_mapper.out"

iverilog -g2012 -o "$TB_DIR/tb_bpsk_upsampler_8x.out" \
  "$RTL_DIR/bpsk_upsampler_8x.v" \
  "$TB_DIR/tb_bpsk_upsampler_8x.v"
vvp "$TB_DIR/tb_bpsk_upsampler_8x.out"

iverilog -g2012 -o "$TB_DIR/tb_bpsk_rrc_tx_fir.out" \
  "$RTL_DIR/bpsk_rrc_tx_fir.v" \
  "$TB_DIR/tb_bpsk_rrc_tx_fir.v"
vvp "$TB_DIR/tb_bpsk_rrc_tx_fir.out"

iverilog -g2012 -o "$TB_DIR/tb_bpsk_rx_bit_recovery.out" \
  "$RTL_DIR/bpsk_rrc_tx_fir.v" \
  "$RTL_DIR/bpsk_rrc_rx_fir.v" \
  "$RTL_DIR/bpsk_symbol_timing_sampler.v" \
  "$RTL_DIR/bpsk_symbol_timing_recovery.v" \
  "$RTL_DIR/bpsk_hard_decision.v" \
  "$TB_DIR/tb_bpsk_rx_bit_recovery.v"
vvp "$TB_DIR/tb_bpsk_rx_bit_recovery.out"

iverilog -g2012 -o "$TB_DIR/tb_bpsk_framed_loopback.out" \
  "$RTL_DIR/bpsk_symbol_mapper.v" \
  "$RTL_DIR/bpsk_upsampler_8x.v" \
  "$RTL_DIR/bpsk_rrc_tx_fir.v" \
  "$RTL_DIR/bpsk_rrc_rx_fir.v" \
  "$RTL_DIR/bpsk_symbol_timing_sampler.v" \
  "$RTL_DIR/bpsk_symbol_timing_recovery.v" \
  "$RTL_DIR/bpsk_hard_decision.v" \
  "$RTL_DIR/bpsk_framed_tx_chain.v" \
  "$RTL_DIR/bpsk_rx_bit_recovery_chain.v" \
  "$TB_DIR/tb_bpsk_framed_loopback.v"
vvp "$TB_DIR/tb_bpsk_framed_loopback.out"

iverilog -g2012 -o "$TB_DIR/tb_bpsk_zynq_ber_top.out" \
  "$RTL_DIR/bpsk_symbol_mapper.v" \
  "$RTL_DIR/bpsk_upsampler_8x.v" \
  "$RTL_DIR/bpsk_rrc_tx_fir.v" \
  "$RTL_DIR/bpsk_rrc_rx_fir.v" \
  "$RTL_DIR/bpsk_symbol_timing_sampler.v" \
  "$RTL_DIR/bpsk_symbol_timing_recovery.v" \
  "$RTL_DIR/bpsk_hard_decision.v" \
  "$RTL_DIR/bpsk_framed_tx_chain.v" \
  "$RTL_DIR/bpsk_rx_bit_recovery_chain.v" \
  "$RTL_DIR/bpsk_frame_bit_source.v" \
  "$RTL_DIR/bpsk_ber_counter.v" \
  "$RTL_DIR/bpsk_zynq_ber_top.v" \
  "$TB_DIR/tb_bpsk_zynq_ber_top.v"
vvp "$TB_DIR/tb_bpsk_zynq_ber_top.out"

iverilog -g2012 -o "$TB_DIR/tb_bpsk_zynq_ber_top_multiframe.out" \
  "$RTL_DIR/bpsk_symbol_mapper.v" \
  "$RTL_DIR/bpsk_upsampler_8x.v" \
  "$RTL_DIR/bpsk_rrc_tx_fir.v" \
  "$RTL_DIR/bpsk_rrc_rx_fir.v" \
  "$RTL_DIR/bpsk_symbol_timing_sampler.v" \
  "$RTL_DIR/bpsk_symbol_timing_recovery.v" \
  "$RTL_DIR/bpsk_hard_decision.v" \
  "$RTL_DIR/bpsk_framed_tx_chain.v" \
  "$RTL_DIR/bpsk_rx_bit_recovery_chain.v" \
  "$RTL_DIR/bpsk_frame_bit_source.v" \
  "$RTL_DIR/bpsk_ber_counter.v" \
  "$RTL_DIR/bpsk_zynq_ber_top.v" \
  "$TB_DIR/tb_bpsk_zynq_ber_top_multiframe.v"
vvp "$TB_DIR/tb_bpsk_zynq_ber_top_multiframe.out"

test -s "$TB_DIR/bpsk_timing_recovery_mf_input.mem"
test -s "$TB_DIR/bpsk_timing_recovery_model_bits.txt"
test -s "$TB_DIR/bpsk_chain_drift_rx.mem"

# Bit-exact check of the Gardner timing-recovery datapath vs the fixed-point model.
iverilog -g2012 -o "$TB_DIR/tb_bpsk_symbol_timing_recovery.out" \
  "$RTL_DIR/bpsk_symbol_timing_recovery.v" \
  "$TB_DIR/tb_bpsk_symbol_timing_recovery.v"
vvp "$TB_DIR/tb_bpsk_symbol_timing_recovery.out"

# Full-chain: Gardner loop recovers an SPS=8.03 burst at BER=0 where fixed-phase cannot.
iverilog -g2012 -o "$TB_DIR/tb_bpsk_zynq_ber_timing_recovery.out" \
  "$RTL_DIR/bpsk_symbol_mapper.v" \
  "$RTL_DIR/bpsk_upsampler_8x.v" \
  "$RTL_DIR/bpsk_rrc_tx_fir.v" \
  "$RTL_DIR/bpsk_rrc_rx_fir.v" \
  "$RTL_DIR/bpsk_symbol_timing_sampler.v" \
  "$RTL_DIR/bpsk_symbol_timing_recovery.v" \
  "$RTL_DIR/bpsk_hard_decision.v" \
  "$RTL_DIR/bpsk_framed_tx_chain.v" \
  "$RTL_DIR/bpsk_rx_bit_recovery_chain.v" \
  "$RTL_DIR/bpsk_frame_bit_source.v" \
  "$RTL_DIR/bpsk_ber_counter.v" \
  "$RTL_DIR/bpsk_zynq_ber_top.v" \
  "$TB_DIR/tb_bpsk_zynq_ber_timing_recovery.v"
vvp "$TB_DIR/tb_bpsk_zynq_ber_timing_recovery.out"

iverilog -g2012 -o "$TB_DIR/tb_bpsk_zynq_ber_axi_lite.out" \
  "$RTL_DIR/bpsk_symbol_mapper.v" \
  "$RTL_DIR/bpsk_upsampler_8x.v" \
  "$RTL_DIR/bpsk_rrc_tx_fir.v" \
  "$RTL_DIR/bpsk_rrc_rx_fir.v" \
  "$RTL_DIR/bpsk_symbol_timing_sampler.v" \
  "$RTL_DIR/bpsk_symbol_timing_recovery.v" \
  "$RTL_DIR/bpsk_hard_decision.v" \
  "$RTL_DIR/bpsk_framed_tx_chain.v" \
  "$RTL_DIR/bpsk_rx_bit_recovery_chain.v" \
  "$RTL_DIR/bpsk_frame_bit_source.v" \
  "$RTL_DIR/bpsk_ber_counter.v" \
  "$RTL_DIR/bpsk_zynq_ber_top.v" \
  "$RTL_DIR/bpsk_zynq_ber_axi_lite.v" \
  "$TB_DIR/tb_bpsk_zynq_ber_axi_lite.v"
vvp "$TB_DIR/tb_bpsk_zynq_ber_axi_lite.out"

iverilog -g2012 -o "$TB_DIR/tb_axis_iq_passthrough.out" \
  "$RTL_DIR/axis_iq_passthrough.v" \
  "$TB_DIR/tb_axis_iq_passthrough.v"
vvp "$TB_DIR/tb_axis_iq_passthrough.out"
