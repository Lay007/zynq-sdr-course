#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python tools/generate_ieee_plots.py

echo "Generated IEEE-style plots in docs/assets"
true
