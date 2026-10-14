#!/usr/bin/env python3
"""Lab 11.47 - one board receives its own fabric QPSK burst through a cable.

    board B TX1 -> attenuators (>= 30 dB) -> board B RX1

Board B's fabric modem transmits a Lab 11.45 frame through its own DAC and decodes it from its
own ADC. TX and RX share the LO reference, so there is no carrier offset between them.

Two things have to be set up on board B, whose device tree has no DAC driver:

1. The DAC channels take the internal DDS after boot; the modem burst is muxed into the DAC FIFO on
   the DMA input, so the channels are switched to it (`devmem`, DAC core at 0x79024000).
2. The DAC FIFO is written on the vendor DMA stream's strobe. With no stream running it is written
   only during a burst, and between bursts the DAC holds the last burst sample: a carrier at the
   LO about as strong as the burst. `sw/dac_zero_stream.c` runs the TX DMA cyclically over a page
   of zeros so the FIFO is written with zeros between bursts.

`--no-zero-stream` skips step 2 to show what the held sample does to the link. The script checks
board B's temperature (it has no fan) before and after, and always stops the zero stream with
SIGTERM, which disables the DMA before the program exits.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from collections import Counter
from pathlib import Path

import lab_11_30_two_board_cfo_validation as L
import lab_11_32_two_board_fabric_coarse_cfo as B
from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat
from lab_11_27_runtime_qpsk_digital_loopback import QPSK_PAYLOAD_POSITION_BITS as POS, qpsk_ber_once

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "blocks" / "block_11_integrated_sdr_project" / "sw" / "dac_zero_stream.c"
GCC = Path(r"G:\Xilinx\Vitis\2021.1\gnu\aarch32\nt\gcc-arm-linux-gnueabi\bin\arm-linux-gnueabihf-gcc.exe")
PHY = L.PHY
BASE = 0x79040000
DAC_CH_SEL = ("0x79024418", "0x79024458", "0x79024498", "0x790244D8")
MODE = 0x10 | 0x20 | 0x200 | 0x400 | 0x1000 | POS | 0x4000 | 0x20000    # Lab 11.45
TEMP_STOP_C = 80.0


def zynq_temp(r) -> float:
    out = L.sh(r, "x=$(grep -l xadc /sys/bus/iio/devices/iio:device*/name | xargs dirname); "
                  "echo $(cat $x/in_temp0_raw) $(cat $x/in_temp0_offset) $(cat $x/in_temp0_scale)").split()
    raw, off, scale = (float(v) for v in out[-3:])
    return round((raw + off) * scale / 1000, 1)


def stop_zero_stream(r) -> None:
    L.sh(r, "for p in $(ps | grep '[d]ac_zero_stream' | awk '{print $1}'); do kill $p; done; sleep 0.3")


def start_zero_stream(r, binary: Path) -> str:
    upload_bytes_via_ssh_cat(r, payload=binary.read_bytes(), remote_path="/tmp/dac_zero_stream")
    L.sh(r, "chmod +x /tmp/dac_zero_stream")
    drv = L.sh(r, "readlink -f /sys/bus/platform/devices/7c420000.dma/driver").strip()
    if drv:
        L.sh(r, f"echo 7c420000.dma > {drv}/unbind")
    stop_zero_stream(r)
    L.start_detached(r, "nohup /tmp/dac_zero_stream > /tmp/dzs.log 2>&1 &")
    time.sleep(1.0)
    log = L.sh(r, "cat /tmp/dzs.log").strip()
    if "cyclic zeros" not in log:
        raise RuntimeError(f"zero stream did not start: {log}")
    return log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default="192.168.20.1")
    ap.add_argument("--carrier", type=float, default=915e6)
    ap.add_argument("--tx-gain", type=float, default=0.0)
    ap.add_argument("--rx-gain", type=int, default=60)
    ap.add_argument("--frames", type=int, default=60)
    ap.add_argument("--offsets", type=int, nargs="+", default=[0, 1, 2, 5, 6, 7],
                    help="start_offset values; with one board the latency is fixed and 3, 4 sit on the symbol edge")
    ap.add_argument("--no-dc-blocker", action="store_true", help="clear mode bit 0x200")
    ap.add_argument("--no-zero-stream", action="store_true", help="show the held DAC sample (carrier) instead")
    ap.add_argument("--binary", type=Path, default=Path(r"C:\tmp\dac_zero_stream"))
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args()

    if not args.no_zero_stream and (not args.binary.exists() or args.binary.stat().st_mtime < SOURCE.stat().st_mtime):
        args.binary.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(GCC), "-O2", "-Wall", "-Wextra", "-static", "-o", str(args.binary), str(SOURCE)], check=True)
    mode = MODE & ~0x200 if args.no_dc_blocker else MODE
    r = L.runner_for(args.host, "root", "analog", 22, 40.0)
    res = {"lab": "11.47", "carrier_hz": args.carrier, "tx_gain_db": args.tx_gain, "rx_gain_db": args.rx_gain,
           "mode_bits": hex(mode), "zero_stream": not args.no_zero_stream, "offsets": args.offsets}
    try:
        res["temp_before_c"] = zynq_temp(r)
        if res["temp_before_c"] >= TEMP_STOP_C:
            raise SystemExit(f"board at {res['temp_before_c']} C, not starting")
        L.quiet_board(r)
        L.sh(r, f"echo {int(L.SAMPLE_RATE)} > {PHY}/in_voltage_sampling_frequency 2>/dev/null; "
                f"echo {int(args.carrier)} > {PHY}/out_altvoltage0_RX_LO_frequency; "
                f"echo {int(args.carrier)} > {PHY}/out_altvoltage1_TX_LO_frequency; "
                f"echo manual > {PHY}/in_voltage0_gain_control_mode; echo {args.rx_gain} > {PHY}/in_voltage0_hardwaregain")
        if not args.no_zero_stream:
            res["zero_stream_log"] = start_zero_stream(r, args.binary)
        L.sh(r, "; ".join(f"devmem {a} 32 2" for a in DAC_CH_SEL) + "; devmem 0x79024044 32 1")
        L.sh(r, f"echo 0 > {PHY}/out_altvoltage1_TX_LO_powerdown; echo {args.tx_gain:.2f} > {PHY}/out_voltage0_hardwaregain")
        locked, clean, errors, bits = Counter(), 0, 0, 0
        for k in range(args.frames):
            off = args.offsets[k % len(args.offsets)]
            row = qpsk_ber_once(r, BASE, B.LONG_FRAME_SYMBOLS, off, mode_bits=mode, preamble_bits=B.LONG_PREAMBLE_BITS)
            if row.get("received_symbols") == B.LONG_FRAME_SYMBOLS:
                locked[off] += 1
                pe = row.get("payload_errors") or 0
                errors, bits, clean = errors + pe, bits + 256, clean + (pe == 0)
        res.update({"frames": args.frames, "locked": sum(locked.values()), "clean": clean,
                    "payload_bit_errors": errors, "payload_bits": bits,
                    "locked_per_offset": {str(o): locked[o] for o in args.offsets}})
    finally:
        try:
            L.quiet_board(r)
            stop_zero_stream(r)
            res["zero_stream_running_after"] = int(L.sh(r, "ps | grep -c '[d]ac_zero_stream'").strip() or 0)
            res["temp_after_c"] = zynq_temp(r)
        finally:
            r.client.close()
    print(json.dumps(res, indent=2))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
