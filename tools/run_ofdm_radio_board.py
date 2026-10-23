#!/usr/bin/env python3
"""Issue #48 stage 4b on the bench: OFDM frames through the radio with the OFDM image (ofdm-txrx-48-v2).

Two modes, both driving blocks/block_08_modulation_and_synchronization/sw/zofdm.c on the boards:

  loop        one board, TX1 cabled to RX1 through at least 30 dB. The image is loaded at run time
              through fpga_manager (board A only: the vendor shell survives it there; on board B a
              runtime PL load breaks the AD9361 until a cold power cycle), `zofdm loop` runs for every
              point of the level ladder (--tx-gains x --rx-shifts), and the board is warm-rebooted
              back to its own bitstream at the end (--no-reboot keeps the OFDM image).
  two-board   the RX board listens (`zofdm rx`), the TX board sends (`zofdm tx`). Both must run the
              OFDM image already: the TX board may be loaded at run time when it is board A
              (--hot-load-tx); the RX board (B) needs the image on its card, which this script never
              writes. It checks the core ID on both and stops if one is missing.

Every command runs detached on the board (board_detached), so a reset SSH session costs a retry, not
the run. Board B has no fan: its Zynq temperature is read before and after, and the run stops at
--max-temp-c. Results (every RESULT line of zofdm, the registers, temperatures) go to --json-out.

    python tools/run_ofdm_radio_board.py loop --host 192.168.40.1 \
        --bit ../zynq-sdr-course-artifacts/bitstreams/ofdm-txrx-48-v2/system_top.bit \
        --tx-gains -30 -20 -10 --rx-shifts 4 5 --frames 100 --symbols 10 --json-out tmp/ofdm_loop.json
    python tools/run_ofdm_radio_board.py two-board --tx-host 192.168.40.1 --rx-host 192.168.20.1 \
        --hot-load-tx --bit ... --frames 200 --symbols 10 --json-out tmp/ofdm_ab.json
    python tools/run_ofdm_radio_board.py loop --dry-run ...      the plan, without a board
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "blocks" / "block_11_integrated_sdr_project" / "python"))

SOURCE = ROOT / "blocks" / "block_08_modulation_and_synchronization" / "sw" / "zofdm.c"
GCC = Path(r"G:\Xilinx\Vitis\2021.1\gnu\aarch32\nt\gcc-arm-linux-gnueabi\bin\arm-linux-gnueabihf-gcc.exe")
CORE_ID = 0x4F464452
CORE_ADDR = 0x79060000
REMOTE_BIN = "/tmp/zofdm"
FIRMWARE = "ofdm_txrx_48.bin"

RESULT_RE = re.compile(r"^RESULT (.*)$", re.MULTILINE)


def parse_result(text: str) -> dict[str, object]:
    """The last `RESULT k=v ...` line of zofdm's output as a dict (numbers converted)."""
    found = RESULT_RE.findall(text)
    if not found:
        return {}
    row: dict[str, object] = {}
    for item in found[-1].split():
        key, _, value = item.partition("=")
        try:
            row[key] = int(value)
        except ValueError:
            try:
                row[key] = float(value)
            except ValueError:
                row[key] = value
    return row


def ber(row: dict[str, object]) -> float | None:
    bits = row.get("bits")
    return (row["bit_errors"] / bits) if isinstance(bits, int) and bits > 0 else None  # type: ignore[operator]


def zofdm_args(args: argparse.Namespace) -> str:
    return (f"--frames {args.frames} --symbols {args.symbols} --rate {args.rate} --lo {args.lo} "
            f"--rx-gain {args.rx_gain} --core-gain {args.core_gain}")


def plan(args: argparse.Namespace) -> list[str]:
    """The board commands in order (also what --dry-run prints)."""
    steps: list[str] = []
    common = zofdm_args(args)
    if args.mode == "loop":
        steps.append(f"[{args.host}] stop IIO writers, TX gain to minimum")
        steps.append(f"[{args.host}] fpga_manager load {FIRMWARE}; check 0x{CORE_ADDR:08x} == 0x{CORE_ID:08x}")
        steps.append(f"[{args.host}] upload {REMOTE_BIN}")
        for tx in args.tx_gains:
            for shift in args.rx_shifts:
                steps.append(f"[{args.host}] {REMOTE_BIN} loop {common} --tx-gain {tx} --rx-shift {shift}")
        steps.append(f"[{args.host}] {REMOTE_BIN} regs; {REMOTE_BIN} stop")
        if not args.no_reboot:
            steps.append(f"[{args.host}] warm reboot back to the card's bitstream")
    else:
        if args.hot_load_tx:
            steps.append(f"[{args.tx_host}] fpga_manager load {FIRMWARE}")
        steps.append(f"[{args.tx_host}, {args.rx_host}] check 0x{CORE_ADDR:08x} == 0x{CORE_ID:08x}; upload {REMOTE_BIN}")
        steps.append(f"[{args.rx_host}] temperature (stop at {args.max_temp_c} C)")
        for tx in args.tx_gains:
            for shift in args.rx_shifts:
                steps.append(f"[{args.rx_host}] {REMOTE_BIN} rx {common} --rx-shift {shift} --timeout {args.rx_timeout}"
                             " (detached)")
                steps.append(f"[{args.tx_host}] {REMOTE_BIN} tx {common} --tx-gain {tx} --period-ms {args.period_ms}")
        steps.append(f"[{args.tx_host}, {args.rx_host}] {REMOTE_BIN} stop")
        if args.hot_load_tx and not args.no_reboot:
            steps.append(f"[{args.tx_host}] warm reboot back to the card's bitstream")
    return steps


# --------------------------------------------------------------------------------------------- board

def build_binary(binary: Path) -> bytes:
    if not binary.exists() or binary.stat().st_mtime < SOURCE.stat().st_mtime:
        binary.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(GCC), "-O2", "-Wall", "-Wextra", "-static", "-o", str(binary), str(SOURCE), "-lm"],
                       check=True)
    return binary.read_bytes()


def temperature_c(host: str) -> float | None:
    """The Zynq XADC temperature, (raw + offset) * scale / 1000."""
    from board_detached import board_sh
    out = board_sh(host, "for d in /sys/bus/iio/devices/iio:device*; do "
                         "if [ \"$(cat $d/name)\" = xadc ]; then "
                         "echo $(cat $d/in_temp0_raw) $(cat $d/in_temp0_offset) $(cat $d/in_temp0_scale); fi; done")
    try:
        raw, offset, scale = (float(x) for x in out.split()[:3])
    except ValueError:
        return None
    return round((raw + offset) * scale / 1000.0, 1)


def core_present(host: str) -> bool:
    from board_detached import board_sh
    out = board_sh(host, f"devmem 0x{CORE_ADDR:08x}").strip().lower()
    return out == f"0x{CORE_ID:08x}"


def hot_load(host: str, bit: Path) -> dict[str, object]:
    from bit_to_fpga_manager_bin import convert
    from board_detached import board_sh
    import lab_11_30_two_board_cfo_validation as L
    from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat

    fw = convert(bit.read_bytes())
    r = L.runner_for(host, "root", "analog", 22, 60.0)
    try:
        L.quiet_board(r)
        upload_bytes_via_ssh_cat(r, payload=fw, remote_path=f"/lib/firmware/{FIRMWARE}")
    finally:
        r.client.close()
    board_sh(host, f"echo 0 > /sys/class/fpga_manager/fpga0/flags; echo {FIRMWARE} > /sys/class/fpga_manager/fpga0/firmware")
    state = board_sh(host, "cat /sys/class/fpga_manager/fpga0/state").strip()
    if state != "operating" or not core_present(host):
        raise RuntimeError(f"{host}: fpga_manager state {state!r}, core present {core_present(host)}")
    return {"fpga_state": state, "fpga_manager_bin_sha256": hashlib.sha256(fw).hexdigest(),
            "iio_names": board_sh(host, "cat /sys/bus/iio/devices/iio:device*/name").split()}


def upload_binary(host: str, prog: bytes) -> None:
    from board_detached import board_sh
    import lab_11_30_two_board_cfo_validation as L
    from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat

    r = L.runner_for(host, "root", "analog", 22, 60.0)
    try:
        upload_bytes_via_ssh_cat(r, payload=prog, remote_path=REMOTE_BIN)
    finally:
        r.client.close()
    board_sh(host, f"chmod +x {REMOTE_BIN}")


def warm_reboot(host: str) -> None:
    from board_detached import board_sh
    board_sh(host, "sync; (sleep 1; reboot) > /dev/null 2>&1 &")


def run_loop(args: argparse.Namespace, prog: bytes, res: dict) -> None:
    from board_detached import board_sh, run_detached, wait_detached

    res["load"] = hot_load(args.host, args.bit)
    upload_binary(args.host, prog)
    for tx in args.tx_gains:
        for shift in args.rx_shifts:
            tag = f"ofdm_loop_{int(abs(tx) * 100)}_{shift}"
            run_detached(args.host, f"{REMOTE_BIN} loop {zofdm_args(args)} --tx-gain {tx} --rx-shift {shift}", tag)
            out = wait_detached(args.host, tag, timeout_s=60 + args.frames * 2)
            row = {"tx_gain": tx, "rx_shift": shift, **parse_result(out), "log": out.splitlines()[-40:]}
            row["ber"] = ber(row)
            res["points"].append(row)
            print(json.dumps({k: row.get(k) for k in ("tx_gain", "rx_shift", "frames", "lost", "bits", "bit_errors", "ber")}),
                  flush=True)
    res["regs"] = board_sh(args.host, f"{REMOTE_BIN} regs").splitlines()
    board_sh(args.host, f"{REMOTE_BIN} stop")


def run_two_board(args: argparse.Namespace, prog: bytes, res: dict) -> None:
    from board_detached import board_sh, run_detached, wait_detached

    if args.hot_load_tx:
        res["load_tx"] = hot_load(args.tx_host, args.bit)
    for host in (args.tx_host, args.rx_host):
        if not core_present(host):
            raise RuntimeError(f"{host}: no ofdm_radio_core at 0x{CORE_ADDR:08x}; the RX board needs the OFDM image "
                               "on its card (not written by this script)")
        upload_binary(host, prog)
    for tx in args.tx_gains:
        for shift in args.rx_shifts:
            temp = temperature_c(args.rx_host)
            if temp is not None and temp >= args.max_temp_c:
                res["stopped"] = f"{args.rx_host} at {temp} C"
                return
            tag = f"ofdm_ab_{int(abs(tx) * 100)}_{shift}"
            run_detached(args.rx_host, f"{REMOTE_BIN} rx {zofdm_args(args)} --rx-shift {shift} "
                                       f"--timeout {args.rx_timeout}", tag + "_rx")
            time.sleep(2.0)
            run_detached(args.tx_host, f"{REMOTE_BIN} tx {zofdm_args(args)} --tx-gain {tx} --period-ms {args.period_ms}",
                         tag + "_tx")
            tx_out = wait_detached(args.tx_host, tag + "_tx", timeout_s=60 + args.frames * args.period_ms / 100)
            rx_out = wait_detached(args.rx_host, tag + "_rx", timeout_s=args.rx_timeout + 60)
            row = {"tx_gain": tx, "rx_shift": shift, "rx_temp_c_before": temp, **parse_result(rx_out),
                   "tx_log": tx_out.splitlines()[-5:], "rx_log": rx_out.splitlines()[-40:]}
            row["ber"] = ber(row)
            res["points"].append(row)
            print(json.dumps({k: row.get(k) for k in ("tx_gain", "rx_shift", "expected", "received", "garbled",
                                                      "bits", "bit_errors", "ber", "rx_temp_c_before")}), flush=True)
    res["rx_temp_c_after"] = temperature_c(args.rx_host)
    for host in (args.tx_host, args.rx_host):
        board_sh(host, f"{REMOTE_BIN} stop")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mode", choices=["loop", "two-board"])
    ap.add_argument("--host", default="192.168.40.1", help="loop: the board (A)")
    ap.add_argument("--tx-host", default="192.168.40.1")
    ap.add_argument("--rx-host", default="192.168.20.1")
    ap.add_argument("--hot-load-tx", action="store_true", help="two-board: load the image on the TX board (A only)")
    ap.add_argument("--bit", type=Path, default=ROOT.parent / "zynq-sdr-course-artifacts" / "bitstreams" / "ofdm-txrx-48-v2" / "system_top.bit")
    ap.add_argument("--binary", type=Path, default=Path(r"C:\tmp\ofdm_sw\zofdm"))
    ap.add_argument("--frames", type=int, default=100)
    ap.add_argument("--symbols", type=int, default=10)
    ap.add_argument("--rate", type=int, default=2083334)
    ap.add_argument("--lo", type=int, default=915000000)
    ap.add_argument("--rx-gain", type=int, default=71)
    ap.add_argument("--core-gain", type=int, default=9170)
    ap.add_argument("--tx-gains", type=float, nargs="+", default=[-10.0])
    ap.add_argument("--rx-shifts", type=int, nargs="+", default=[4])
    ap.add_argument("--period-ms", type=float, default=50.0)
    ap.add_argument("--rx-timeout", type=float, default=120.0)
    ap.add_argument("--max-temp-c", type=float, default=76.0)
    ap.add_argument("--no-reboot", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    if args.dry_run:
        for step in plan(args):
            print(step)
        return 0
    if args.json_out is None:
        ap.error("--json-out is required unless --dry-run")
    prog = build_binary(args.binary)
    bit = args.bit.read_bytes()
    res: dict = {"issue": 48, "stage": "4b", "mode": args.mode, "bit": str(args.bit),
                 "bit_sha256": hashlib.sha256(bit).hexdigest(), "program_sha256": hashlib.sha256(prog).hexdigest(),
                 "args": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}, "points": []}
    reboot_host = args.host if args.mode == "loop" else (args.tx_host if args.hot_load_tx else None)
    try:
        if args.mode == "loop":
            run_loop(args, prog, res)
        else:
            run_two_board(args, prog, res)
    except Exception as exc:  # noqa: BLE001 -- keep what was measured
        res["error"] = f"{type(exc).__name__}: {exc}"
        print("ERROR", res["error"], flush=True)
    finally:
        if reboot_host and not args.no_reboot:
            try:
                warm_reboot(reboot_host)
                res["rebooted"] = reboot_host
            except Exception as exc:  # noqa: BLE001
                res["reboot_error"] = str(exc)
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
        print("wrote", args.json_out)
    return 1 if "error" in res else 0


if __name__ == "__main__":
    raise SystemExit(main())
