#!/usr/bin/env python3
"""Build the Lab 5.12 PS/PL mailbox Block Design with Vivado (no board needed).

The Zynq PS gets the course board's own PCW_* settings (DDR, MIO, peripherals),
read from its known-good hardware handoff, so the build is not based on guessed
PS7 parameters. The lab's additions (M_AXI_GP0, FCLK_CLK0 = 100 MHz and its
reset) are applied on top. The Vivado project and bitstream stay in a
temporary build directory; only normalized reports are written to --report-dir.
Building proves the recipe and yields the real address map; it does not load
anything onto a board.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

from generate_block5_vivado_reports import detect_vivado, normalize_reports

ROOT = Path(__file__).resolve().parents[1]
TCL_SCRIPT = ROOT / "tools" / "vivado_block5_mailbox_bd.tcl"
BOARD_XSA = ROOT / "hardware" / "7020_ad936x_sdr" / "ps" / "bringup_tests" / "design_1_wrapper.xsa"
DEFAULT_REPORT_DIR = ROOT / "reports" / "fpga" / "block5_mailbox_bd_raw"


def board_ps7_params(xsa: Path) -> list[tuple[str, str]]:
    with zipfile.ZipFile(xsa) as archive:
        hwh = next(name for name in archive.namelist() if name.endswith(".hwh"))
        text = archive.read(hwh).decode("utf-8", errors="ignore")
    block = text[text.find('MODTYPE="processing_system7"'):]
    block = block[: block.find("</MODULE>")]
    return re.findall(r'<PARAMETER NAME="(PCW_[A-Z0-9_]+)" VALUE="([^"]*)"', block)


def tcl_quote(value: str) -> str:
    return "{" + value.replace("{", "").replace("}", "") + "}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--board-xsa", type=Path, default=BOARD_XSA)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--build-dir", type=Path, default=None, help="default: a new temporary directory")
    args = parser.parse_args()

    params = board_ps7_params(args.board_xsa)
    if not params:
        raise SystemExit(f"no processing_system7 PCW_* parameters found in {args.board_xsa}")
    build_dir = args.build_dir or Path(tempfile.mkdtemp(prefix="mailbox_bd_"))
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
    # Keep Vivado's full output in a log file next to the build instead of the console.
    log_path = build_dir / "vivado_build.log"
    result = subprocess.run(
        ["cmd.exe", "/c", str(vivado), "-mode", "batch", "-nojournal", "-nolog",
         "-source", str(TCL_SCRIPT), "-tclargs", str(build_dir), str(params_tcl), str(report_dir)],
        cwd=build_dir,
        capture_output=True,
        text=True,
    )
    log_path.write_text(result.stdout + result.stderr, encoding="utf-8")
    print(f"Vivado log: {log_path}")
    if result.returncode != 0:
        raise SystemExit(f"Vivado failed with exit code {result.returncode}; see {log_path}")
    normalize_reports(report_dir)
    # Read-only PS7 parameters are rejected with a CRITICAL WARNING, not a Tcl error,
    # so they are counted from the log.
    log_text = log_path.read_text(encoding="utf-8")
    rejected = sorted(set(re.findall(r"Cannot set the parameter (\w+) on /processing_system7_0", log_text)))
    build_json = report_dir / "mailbox_echo_build.json"
    build = json.loads(build_json.read_text(encoding="utf-8"))
    build["ps7_params_rejected_read_only"] = rejected
    build_json.write_text(json.dumps(build, indent=2) + "\n", encoding="utf-8")
    print(build_json.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
