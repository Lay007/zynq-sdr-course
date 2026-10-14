#!/usr/bin/env python3
"""Issue #48, Lab 8.14 stage 3 on a board: load the PS + AXI DMA + OFDM modem bitstream and run
the fabric loopback from Linux user space.

Steps, all over SSH:

1. stop the board's IIO users (iio_writedev, iiod) and quiet its transmitter;
2. unbind the drivers of the vendor PL cores (AD9361 ADC/DAC cores and their DMA controllers), so
   that no kernel code touches addresses that disappear with the new bitstream;
3. load the bitstream through fpga_manager (converted with tools/bit_to_fpga_manager_bin.py);
4. run blocks/block_08_modulation_and_synchronization/sw/ofdm_dma_loopback.c (cross-compiled with
   the Vitis arm-linux-gnueabihf-gcc, static) for several seeds;
5. warm-reboot the board so that it boots its own bitstream again, and check that the AD9361
   cores are back.

Meant for board A of the course bench (vendor image, survives a warm reboot). Do not use it on
board B: a runtime PL reload there breaks the AD9361 until a cold power cycle.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "blocks" / "block_11_integrated_sdr_project" / "python"))
import lab_11_30_two_board_cfo_validation as L  # noqa: E402
from bit_to_fpga_manager_bin import convert  # noqa: E402
from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat  # noqa: E402

SOURCE = ROOT / "blocks" / "block_08_modulation_and_synchronization" / "sw" / "ofdm_dma_loopback.c"
GCC = Path(r"G:\Xilinx\Vitis\2021.1\gnu\aarch32\nt\gcc-arm-linux-gnueabi\bin\arm-linux-gnueabihf-gcc.exe")
PL_DEVICES = ["79024000.cf-ad9361-dds-core-lpc", "79020000.cf-ad9361-lpc", "7c420000.dma", "7c400000.dma"]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def wait_ssh(host: str, timeout: float) -> float:
    t0 = time.time()
    seen_down = False
    while time.time() - t0 < timeout:
        s = socket.socket()
        s.settimeout(2)
        try:
            s.connect((host, 22))
            up = True
        except OSError:
            up = False
        finally:
            s.close()
        seen_down |= not up
        if seen_down and up:
            return time.time() - t0
        time.sleep(3)
    raise RuntimeError(f"{host} did not come back within {timeout} s")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default="192.168.40.1")
    ap.add_argument("--bit", type=Path, required=True)
    ap.add_argument("--binary", type=Path, default=Path(r"C:\tmp\ofdm_sw\ofdm_dma_loopback"))
    ap.add_argument("--symbols", type=int, default=80, help="OFDM data symbols per DMA run")
    ap.add_argument("--runs", type=int, default=100, help="DMA runs per seed")
    ap.add_argument("--seeds", type=lambda s: int(s, 0), nargs="+", default=[0x48D5, 0x1, 0xBEEF, 0x2026])
    ap.add_argument("--no-reboot", action="store_true")
    ap.add_argument("--json-out", type=Path, required=True)
    args = ap.parse_args()

    if not args.binary.exists() or args.binary.stat().st_mtime < SOURCE.stat().st_mtime:
        args.binary.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(GCC), "-O2", "-Wall", "-Wextra", "-static", "-o", str(args.binary), str(SOURCE)],
                       check=True)
    bit = args.bit.read_bytes()
    fw = convert(bit)
    prog = args.binary.read_bytes()
    res: dict = {"issue": 48, "stage": 3, "host": args.host, "bit": str(args.bit), "bit_sha256": sha256(bit),
                 "fpga_manager_bin_sha256": sha256(fw), "program_source": str(SOURCE.relative_to(ROOT)),
                 "program_sha256": sha256(prog), "runs": []}
    r = L.runner_for(args.host, "root", "analog", 22, 60.0)
    sh = L.sh
    rebooted = False
    try:
        res["before"] = {
            "uname": sh(r, "uname -a").strip(),
            "fclk0_ctrl": sh(r, "devmem 0xF8000170").strip(),
            "iio_names": sh(r, "cat /sys/bus/iio/devices/iio:device*/name").split(),
        }
        sh(r, "for p in $(ps | grep -E '[i]io_writedev|[i]io_readdev|[i]iod' | awk '{print $1}'); do kill -9 $p; done")
        L.quiet_board(r)
        for dev in PL_DEVICES:
            drv = sh(r, f"readlink -f /sys/bus/platform/devices/{dev}/driver 2>/dev/null").strip()
            if drv:
                sh(r, f"echo {dev} > {drv}/unbind")
        res["unbound"] = {dev: sh(r, f"[ -e /sys/bus/platform/devices/{dev}/driver ] && echo bound || echo unbound").strip()
                          for dev in PL_DEVICES}
        if any(v != "unbound" for v in res["unbound"].values()):
            raise RuntimeError(f"driver still bound: {res['unbound']}")

        upload_bytes_via_ssh_cat(r, payload=fw, remote_path="/lib/firmware/ofdm_dma_bd.bin")
        upload_bytes_via_ssh_cat(r, payload=prog, remote_path="/tmp/ofdm_dma_loopback")
        sh(r, "chmod +x /tmp/ofdm_dma_loopback")
        sh(r, "echo 0 > /sys/class/fpga_manager/fpga0/flags; echo ofdm_dma_bd.bin > /sys/class/fpga_manager/fpga0/firmware")
        res["fpga_state"] = sh(r, "cat /sys/class/fpga_manager/fpga0/state").strip()
        res["dmesg_after_load"] = sh(r, "dmesg | tail -5").splitlines()
        if res["fpga_state"] != "operating":
            raise RuntimeError(f"fpga_manager state {res['fpga_state']}")
        res["modem_id"] = sh(r, "devmem 0x40000000").strip()
        if res["modem_id"].lower() not in ("0x4f46444d",):
            raise RuntimeError(f"no OFDM modem ID at 0x40000000: {res['modem_id']}")

        for seed in args.seeds:
            out = sh(r, f"/tmp/ofdm_dma_loopback {args.symbols} {args.runs} {seed}; echo EXIT=$?")
            lines = out.strip().splitlines()
            row = {"seed": seed, "exit": int(lines[-1].split("=", 1)[1]), "stderr_or_extra": lines[:-2]}
            row.update(json.loads(lines[-2]))
            res["runs"].append(row)
            print(json.dumps({k: row[k] for k in ("seed", "exit", "bits", "bit_errors", "missing_or_duplicate_bytes",
                                                  "dma_errors", "saturations", "dma_time_us_per_run")}), flush=True)
        res["dmesg_after_runs"] = sh(r, "dmesg | tail -5").splitlines()
    finally:
        if not args.no_reboot:
            try:
                L.start_detached(r, "sync; (sleep 1; reboot) > /dev/null 2>&1 &")
            except Exception as exc:  # noqa: BLE001
                res["reboot_error"] = str(exc)
            r.client.close()
            try:
                res["reboot_seconds"] = round(wait_ssh(args.host, 300.0), 1)
                time.sleep(15)
                r2 = L.runner_for(args.host, "root", "analog", 22, 60.0)
                L.quiet_board(r2)
                res["after_reboot"] = {
                    "iio_names": sh(r2, "cat /sys/bus/iio/devices/iio:device*/name").split(),
                    "ad9361_dmesg": sh(r2, "dmesg | grep -iE 'ad9361|calib|tuning' | tail -6").splitlines(),
                }
                r2.client.close()
                rebooted = True
            except Exception as exc:  # noqa: BLE001
                res["after_reboot_error"] = str(exc)
        else:
            r.client.close()
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
        print("wrote", args.json_out, "| rebooted and checked:" if not args.no_reboot else "", rebooted if not args.no_reboot else "")
    ok = res["runs"] and all(x["exit"] == 0 for x in res["runs"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
