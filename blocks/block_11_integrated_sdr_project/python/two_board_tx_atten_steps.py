#!/usr/bin/env python3
"""Issue #29: how accurate is the AD9361 TX attenuator, measured on a second board.

    board A TX1 -> attenuators -> splitter -> board B RX1   (conducted)

Board A transmits the 300 kHz tone of two_board_rx_gain_steps.py and steps its TX gain from 0 dB
down in --step dB; board B keeps a fixed manual RX gain and measures the tone with the same FFT
estimate. Two RX gains cover the range (a low one for the strong end, a high one for the weak end)
and are joined over their common valid points, as in the RX sweep.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

import lab_11_30_two_board_cfo_validation as L
from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat
from two_board_agc_step_transient import TONE_LEN, fetch, tone_buffer
from two_board_rx_gain_steps import FS, N, tone_level

PHY = L.PHY


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--carriers", type=float, nargs="+", default=[915e6])
    ap.add_argument("--rx-gains", type=int, nargs="+", default=[10, 50])
    ap.add_argument("--step", type=float, default=1.0)
    ap.add_argument("--lowest", type=float, default=-80.0)
    ap.add_argument("--min-snr", type=float, default=30.0)
    ap.add_argument("--max-peak", type=float, default=0.8)
    ap.add_argument("--json-out", type=Path, required=True)
    args = ap.parse_args()
    tx_grid = [round(-k * args.step, 2) for k in range(int(round(-args.lowest / args.step)) + 1)]

    ra = L.runner_for("192.168.40.1", "root", "analog", 22, 30.0)
    rb = L.runner_for("192.168.20.1", "root", "analog", 22, 60.0)
    res = {"issue": 29, "sample_rate": FS, "rx_gains": args.rx_gains, "step_db": args.step, "carriers": []}
    try:
        L.quiet_board(ra)
        L.reset_tx_dma(ra)
        upload_bytes_via_ssh_cat(ra, payload=tone_buffer().tobytes(), remote_path="/tmp/tone.bin")
        L.sh(ra, f"echo {int(FS)} > {PHY}/out_voltage_sampling_frequency 2>/dev/null")
        L.sh(rb, f"echo {int(FS)} > {PHY}/in_voltage_sampling_frequency 2>/dev/null; "
                 f"echo manual > {PHY}/in_voltage0_gain_control_mode")
        L.start_detached(ra, f"nohup iio_writedev -c -b {TONE_LEN} -s {TONE_LEN} cf-ad9361-dds-core-lpc "
                             "voltage0 voltage1 < /tmp/tone.bin > /tmp/tone.log 2>&1 &")
        time.sleep(3.0)
        for carrier in args.carriers:
            L.sh(ra, f"echo {int(carrier)} > {PHY}/out_altvoltage1_TX_LO_frequency; echo 0 > {PHY}/out_altvoltage1_TX_LO_powerdown")
            L.sh(rb, f"echo {int(carrier)} > {PHY}/out_altvoltage0_RX_LO_frequency")
            segments = {}
            for g in args.rx_gains:
                L.sh(rb, f"echo {g} > {PHY}/in_voltage0_hardwaregain")
                pts = []
                for tx in tx_grid:
                    L.sh(ra, f"echo {tx:.2f} > {PHY}/out_voltage0_hardwaregain")
                    readback = float(L.sh(ra, f"cat {PHY}/out_voltage0_hardwaregain").split()[0])
                    L.sh(rb, f"iio_readdev -b {N} -s {N} cf-ad9361-lpc voltage0 voltage1 > /tmp/t.bin 2>/dev/null")
                    z = fetch(rb.client, "/tmp/t.bin")
                    lvl, floor, peak = tone_level(z)
                    pts.append({"tx_db": tx, "readback": readback, "tone_dbfs": round(lvl, 2), "floor_dbfs": round(floor, 2),
                                "peak_fs": round(peak, 3), "valid": bool(lvl - floor >= args.min_snr and peak < args.max_peak)})
                segments[str(g)] = pts
                print(f"{carrier / 1e6:.0f} MHz RX {g} dB: {sum(p['valid'] for p in pts)} valid points", flush=True)
            curve = {}
            for i, g in enumerate(args.rx_gains):
                seg = {p["tx_db"]: p["tone_dbfs"] for p in segments[str(g)] if p["valid"]}
                if not seg:
                    continue
                if not curve:
                    shift = 0.0
                else:
                    common = [t for t in seg if t in curve]
                    if not common:
                        continue
                    shift = float(np.mean([curve[t] - seg[t] for t in common]))
                for t, v in seg.items():
                    curve.setdefault(t, v + shift)
            txs = sorted(curve, reverse=True)
            lv = np.array([curve[t] for t in txs])
            fit = np.polyfit(txs, lv, 1) if len(txs) > 2 else None
            dev = {t: round(curve[t] - np.polyval(fit, t), 2) for t in txs} if fit is not None else {}
            res["carriers"].append({"carrier_hz": carrier, "segments": segments, "joined_level_db": {t: round(curve[t], 2) for t in txs},
                                    "fit_slope_db_per_db": round(float(fit[0]), 4) if fit is not None else None,
                                    "deviation_from_fit_db": dev, "range_covered_db": [txs[0], txs[-1]] if txs else None})
            if fit is not None:
                print(f"   joined {txs[0]}..{txs[-1]} dB: slope {fit[0]:.4f} dB/dB, max deviation "
                      f"{max(abs(v) for v in dev.values()):.2f} dB", flush=True)
    finally:
        L.sh(ra, "for p in $(ps | grep '[i]io_writedev' | awk '{print $1}'); do kill -9 $p; done")
        L.quiet_board(ra)
        L.sh(ra, f"echo 1 > {PHY}/out_altvoltage1_TX_LO_powerdown")
        L.sh(rb, f"echo 71 > {PHY}/in_voltage0_hardwaregain")
        L.quiet_board(rb)
        ra.client.close()
        rb.client.close()
        args.json_out.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
        print("wrote", args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
