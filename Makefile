.PHONY: install docs serve labs hdl smoke clean

PYTHON ?= python
PIP ?= pip

install:
	$(PIP) install -r requirements.txt

docs:
	mkdocs build --strict

serve:
	mkdocs serve

labs:
	$(PYTHON) tools/run_all_labs.py

hdl:
	iverilog -g2012 -o blocks/block_05_fpga_hdl_flow/tb/tb_iq_passthrough.out \
		blocks/block_05_fpga_hdl_flow/rtl/iq_passthrough.v \
		blocks/block_05_fpga_hdl_flow/tb/tb_iq_passthrough.v
	vvp blocks/block_05_fpga_hdl_flow/tb/tb_iq_passthrough.out
	$(PYTHON) blocks/block_05_fpga_hdl_flow/python/generate_fir_iq_4tap_vectors.py
	iverilog -g2012 -o blocks/block_05_fpga_hdl_flow/tb/tb_fir_iq_4tap.out \
		blocks/block_05_fpga_hdl_flow/rtl/fir_iq_4tap.v \
		blocks/block_05_fpga_hdl_flow/tb/tb_fir_iq_4tap.v
	vvp blocks/block_05_fpga_hdl_flow/tb/tb_fir_iq_4tap.out
	$(PYTHON) blocks/block_05_fpga_hdl_flow/python/generate_nco_mixer_iq_vectors.py
	iverilog -g2012 -o blocks/block_05_fpga_hdl_flow/tb/tb_nco_mixer_iq.out \
		blocks/block_05_fpga_hdl_flow/rtl/nco_mixer_iq.v \
		blocks/block_05_fpga_hdl_flow/tb/tb_nco_mixer_iq.v
	vvp blocks/block_05_fpga_hdl_flow/tb/tb_nco_mixer_iq.out
	iverilog -g2012 -o blocks/block_05_fpga_hdl_flow/tb/tb_axis_iq_passthrough.out \
		blocks/block_05_fpga_hdl_flow/rtl/axis_iq_passthrough.v \
		blocks/block_05_fpga_hdl_flow/tb/tb_axis_iq_passthrough.v
	vvp blocks/block_05_fpga_hdl_flow/tb/tb_axis_iq_passthrough.out

smoke: docs labs hdl

clean:
	rm -rf site
	rm -f blocks/block_05_fpga_hdl_flow/tb/*.out
	rm -f blocks/block_05_fpga_hdl_flow/tb/*.vcd
