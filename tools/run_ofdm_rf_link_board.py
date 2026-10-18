#!/usr/bin/env python3
"""Issue #48, stage 4a: an OFDM frame through a real radio path, decoded by the RTL receiver.

One board plays a frame of tools/ofdm_rf_link.py (sync preamble + the RTL transmitter's training and
data symbols) cyclically through its DDS/DMA core; the other board records its receiver with
iio_readdev; the PC finds a frame in the recording and runs it through the exact RTL receiver of the
board's modem (Icarus Verilog). The modem itself does not run on the board in this stage: the point
is the receiver on real samples (CFO, timing, DC, I/Q imbalance, noise of the AD9361 path), before
the modem is built into the radio image (stage 4b).

    python tools/run_ofdm_rf_link_board.py --tx-board 192.168.40.1 --rx-board 192.168.20.1 \\
        --lo 915e6 --tx-gain -30 --rx-gain 71 --frames 5 --json-out reports/hardware/ofdm-rf-link-YYYYMMDD.json

Both boards are set to the modem rate (2.083 MS/s, the lowest AD9361 rate without a FIR), the given
LO and manual RX gain; any zmbox / zmsg writer is stopped first (on the course image a listening
mailbox would route the DAC FIFO to the QPSK modem instead of the DMA). On exit both boards are
quieted and their sample rate is restored. Written 2026-10-19 without the bench; to be run first at
the next bench session.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "blocks/block_11_integrated_sdr_project/python"))
sys.path.insert(0, str(ROOT / "tools"))

import lab_11_30_two_board_cfo_validation as L  # noqa: E402
import ofdm_rf_link as O  # noqa: E402
from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat  # noqa: E402
from two_board_agc_step_transient import fetch  # noqa: E402

PHY = L.PHY
RATE = 2_083_334          # the driver rejects 2083333 (below its 2083333.33 minimum)


def setup_radio(r, lo: float, rx_gain: int) -> str:
    L.sh(r, "cd /root && ./zmbox stop >/dev/null 2>&1; ./zmsg stop >/dev/null 2>&1; true")
    L.quiet_board(r)
    for attr, value in (("in_voltage_sampling_frequency", RATE), ("out_voltage_sampling_frequency", RATE),
                        ("out_altvoltage0_RX_LO_frequency", int(lo)), ("out_altvoltage1_TX_LO_frequency", int(lo)),
                        ("in_voltage0_gain_control_mode", "manual"), ("in_voltage0_hardwaregain", rx_gain)):
        L.sh(r, f"echo {value} > {PHY}/{attr} 2>/dev/null")
    return L.sh(r, f"cat {PHY}/in_voltage_sampling_frequency").strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tx-board", default="192.168.40.1")
    ap.add_argument("--rx-board", default="192.168.20.1")
    ap.add_argument("--lo", type=float, default=915e6)
    ap.add_argument("--tx-gain", type=float, default=-30.0)
    ap.add_argument("--rx-gain", type=int, default=71)
    ap.add_argument("--tx-scale-db", type=float, default=7.0)
    ap.add_argument("--data-symbols", type=int, default=20)
    ap.add_argument("--frames", type=int, default=5, help="recordings, each decoded once")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--json-out", type=Path, required=True)
    args = ap.parse_args()

    res = {"issue": 48, "stage": "4a", "lo_hz": args.lo, "rate": RATE, "tx_board": args.tx_board,
           "rx_board": args.rx_board, "tx_gain_db": args.tx_gain, "rx_gain_db": args.rx_gain, "records": []}
    rt = L.runner_for(args.tx_board, "root", "analog", 22, 60.0)
    rr = L.runner_for(args.rx_board, "root", "analog", 22, 120.0)
    with tempfile.TemporaryDirectory(prefix="ofdm-link-") as tmp:
        work = Path(tmp)
        link = argparse.Namespace(data_symbols=args.data_symbols, train_symbols=1, tx_scale_db=args.tx_scale_db,
                                  save_tx=work / "frame", seed=args.seed, backoff=4, fs=RATE, rx_rms=3700.0,
                                  tx_dir=work / "frame", rx_capture=None)
        meta = O.save_tx(work, np.random.default_rng(args.seed), link)
        res["frame"] = meta
        try:
            res["rate_readback"] = [setup_radio(rt, args.lo, args.rx_gain), setup_radio(rr, args.lo, args.rx_gain)]
            L.reset_tx_dma(rt)
            upload_bytes_via_ssh_cat(rt, payload=(work / "frame" / "tx_frame.bin").read_bytes(), remote_path="/tmp/ofdm_frame.bin")
            L.sh(rt, f"echo {args.tx_gain:.2f} > {PHY}/out_voltage0_hardwaregain; "
                     f"echo 0 > {PHY}/out_altvoltage1_TX_LO_powerdown")
            n = meta["samples"]
            L.start_detached(rt, f"nohup iio_writedev -c -b {n} -s {n} cf-ad9361-dds-core-lpc voltage0 voltage1 "
                                 "< /tmp/ofdm_frame.bin > /tmp/ofdm_tx.log 2>&1 &")
            time.sleep(2.0)
            cap = 3 * n
            for k in range(args.frames):
                L.sh(rr, f"iio_readdev -b {cap} -s {cap} cf-ad9361-lpc voltage0 voltage1 > /tmp/ofdm_rx.bin")
                z = fetch(rr.client, "/tmp/ofdm_rx.bin")
                iq = np.zeros(2 * len(z), dtype=np.int16)
                iq[0::2], iq[1::2] = np.round(z.real), np.round(z.imag)
                rec = work / f"rx{k}.bin"
                iq.tofile(rec)
                link.rx_capture = rec
                row = O.rx_capture(work, link)
                row["peak_abs"] = float(np.abs(z).max())
                res["records"].append(row)
                print(json.dumps(row), flush=True)
        finally:
            for r in (rt, rr):
                try:
                    L.quiet_board(r)
                    L.sh(r, f"echo {int(L.SAMPLE_RATE)} > {PHY}/in_voltage_sampling_frequency 2>/dev/null")
                except Exception as exc:  # noqa: BLE001
                    print("cleanup warning:", exc)
                r.client.close()
    bits = sum(x.get("bits", 0) for x in res["records"])
    errs = sum(x.get("bit_errors", 0) for x in res["records"])
    res["summary"] = {"records": len(res["records"]), "bits": bits, "bit_errors": errs}
    print(json.dumps(res["summary"]))
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
