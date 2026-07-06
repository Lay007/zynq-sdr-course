#!/usr/bin/env bash
# POSIX compatibility wrapper. The canonical suite is implemented in Python so
# the same test list runs from Linux CI, Git Bash, WSL, and native Windows.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if command -v python3 >/dev/null 2>&1; then
  exec python3 tools/run_block5_hdl_smoke.py "$@"
fi

exec python tools/run_block5_hdl_smoke.py "$@"
