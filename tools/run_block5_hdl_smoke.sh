#!/usr/bin/env bash
# Run the Block 5 HDL smoke suite used by local checks and GitHub Actions.
# The script intentionally keeps all generated vectors and VCD files deterministic.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TB_DIR="blocks/block_05_fpga_hdl_flow/tb"
RTL_DIR="blocks/block_05_fpga_hdl_flow/rtl"
PY_DIR="blocks/block_05_fpga_hdl_flow/python"

python "$PY_DIR/generate_fir_iq_4tap_vectors.py"
python "$PY_DIR/generate_nco_mixer_iq_vectors.py"

test -s "$TB_DIR/fir_iq_4tap_input_vectors.txt"
test -s "$TB_DIR/fir_iq_4tap_expected_vectors.txt"
test -s "$TB_DIR/nco_mixer_iq_input_vectors.txt"
test -s "$TB_DIR/nco_mixer_iq_expected_vectors.txt"

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

iverilog -g2012 -o "$TB_DIR/tb_axis_iq_passthrough.out" \
  "$RTL_DIR/axis_iq_passthrough.v" \
  "$TB_DIR/tb_axis_iq_passthrough.v"
vvp "$TB_DIR/tb_axis_iq_passthrough.out"
