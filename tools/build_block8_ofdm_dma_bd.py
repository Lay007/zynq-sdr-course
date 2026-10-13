#!/usr/bin/env python3
"""Build the issue #48 PS + AXI DMA + OFDM modem Block Design with Vivado (no board needed).

Same recipe as tools/build_block5_mailbox_bd.py: the Zynq PS gets the course
board's own PCW_* settings from its known-good hardware handoff, then the
design's additions (M_AXI_GP0, S_AXI_HP0, FCLK_CLK0 = 100 MHz, fabric
interrupts). The modem sits behind ofdm_axi_modem_vivado_wrapper, which loops
its TX samples back into its RX inside the fabric. The Vivado project,
bitstream and XSA stay in the build directory; only normalized reports are
written to --report-dir. Building proves that the design assembles, validates,
routes and meets timing; it does not load anything onto a board.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

from build_block5_mailbox_bd import BOARD_XSA, board_ps7_params, tcl_quote
from generate_block5_vivado_reports import detect_vivado, normalize_reports

ROOT = Path(__file__).resolve().parents[1]
TCL_SCRIPT = ROOT / "tools" / "vivado_block8_ofdm_dma_bd.tcl"
DEFAULT_REPORT_DIR = ROOT / "reports" / "fpga" / "block8_ofdm_dma_bd_raw"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--board-xsa", type=Path, default=BOARD_XSA)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--build-dir", type=Path, default=None, help="default: a new temporary directory")
    parser.add_argument("--train-symbols", type=int, choices=(1, 2, 4, 8), default=1,
                        help="the modem's CE_TRAIN_SYMBOLS")
    args = parser.parse_args()

    params = board_ps7_params(args.board_xsa)
    if not params:
        raise SystemExit(f"no processing_system7 PCW_* parameters found in {args.board_xsa}")
    build_dir = args.build_dir or Path(tempfile.mkdtemp(prefix="ofdm_dma_bd_"))
    build_dir.mkdir(parents=True, exist_ok=True)
    report_dir = args.report_dir.resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    params_tcl = build_dir / "ps7_board_params.tcl"
    params_tcl.write_text(
        "set ps7_board_params [list \\\n"
        + "".join(f"    {name} {tcl_quote(value)} \\\n" for name, value in params)
        + "]\n",
        encoding="utf-8",
    )
    print(f"board PS7 parameters: {len(params)} from {args.board_xsa.name}")
    print(f"build directory: {build_dir}")

    vivado = detect_vivado()
    log_path = build_dir / "vivado_build.log"
    result = subprocess.run(
        ["cmd.exe", "/c", str(vivado), "-mode", "batch", "-nojournal", "-nolog",
         "-source", str(TCL_SCRIPT), "-tclargs", str(build_dir), str(params_tcl), str(report_dir),
         str(args.train_symbols)],
        cwd=build_dir,
        capture_output=True,
        text=True,
    )
    log_path.write_text(result.stdout + result.stderr, encoding="utf-8")
    print(f"Vivado log: {log_path}")
    if result.returncode != 0:
        raise SystemExit(f"Vivado failed with exit code {result.returncode}; see {log_path}")
    normalize_reports(report_dir)
    log_text = log_path.read_text(encoding="utf-8")
    rejected = sorted(set(re.findall(r"Cannot set the parameter (\w+) on /processing_system7_0", log_text)))
    build_json = report_dir / "ofdm_dma_build.json"
    build = json.loads(build_json.read_text(encoding="utf-8"))
    build["ps7_params_rejected_read_only"] = rejected
    build["critical_warnings"] = len(re.findall(r"^CRITICAL WARNING", log_text, flags=re.MULTILINE))
    build_json.write_text(json.dumps(build, indent=2) + "\n", encoding="utf-8")
    print(build_json.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
