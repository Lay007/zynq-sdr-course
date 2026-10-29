.PHONY: install install-dev docs serve labs hdl test lint smoke clean

PYTHON ?= python
PIP ?= pip

install:
	$(PIP) install -r requirements.txt

install-dev:
	$(PIP) install -r requirements-dev.txt

docs:
	mkdocs build --strict

serve:
	mkdocs serve

labs:
	$(PYTHON) tools/run_all_labs.py

hdl:
	$(PYTHON) tools/run_block5_hdl_smoke.py
	$(PYTHON) tools/run_block8_css_rtl.py

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check blocks tools tests

smoke: docs labs hdl

clean:
	$(PYTHON) tools/tasks.py clean
