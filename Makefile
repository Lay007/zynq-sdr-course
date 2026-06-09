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
	bash tools/run_block5_hdl_smoke.sh

smoke: docs labs hdl

clean:
	rm -rf site
	rm -f blocks/block_05_fpga_hdl_flow/tb/*.out
	rm -f blocks/block_05_fpga_hdl_flow/tb/*.vcd
	rm -f blocks/block_05_fpga_hdl_flow/tb/*_vectors.txt
