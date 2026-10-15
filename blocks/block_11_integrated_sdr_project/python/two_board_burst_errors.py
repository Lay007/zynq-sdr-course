#!/usr/bin/env python3
"""Where are the errors in the gross frames of the listening receiver (#68)? Per-frame record.

    board A TX1 -> attenuators -> splitter -> board B RX1   (conducted)

Board A sends the burst of two_board_burst.py (one frame with a reference symbol, then silence);
board B receives in listen mode (gp_ctrl[18]) and records, for every frame, the payload error
count and the payload-position telemetry of mode bit 15 (errors per quarter of the 256-bit payload,
first and last error index). A frame locked at the wrong place has errors spread over the whole
payload from bit 0; a loop that slips in the middle of the frame has clean early quarters.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import lab_11_30_two_board_cfo_validation as L
import lab_11_32_two_board_fabric_coarse_cfo as B
from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat
from lab_11_27_runtime_qpsk_digital_loopback import qpsk_ber_once
from two_board_agc_ber import BASE, MODE, PHY
from two_board_burst import LISTEN_BIT, burst_iq


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--carrier", type=float, default=915e6)
    ap.add_argument("--gap", type=int, default=19)
    ap.add_argument("--tx", type=float, default=-30.0)
    ap.add_argument("--rx-gain", type=int, default=71)
    ap.add_argument("--frames", type=int, default=1000)
    ap.add_argument("--no-listen", action="store_true")
    ap.add_argument("--lead", type=int, default=0, help="training symbols before the reference")
    ap.add_argument("--json-out", type=Path, required=True)
    args = ap.parse_args()
    mode_bits = MODE | (0 if args.no_listen else LISTEN_BIT)

    ra = L.runner_for("192.168.40.1", "root", "analog", 22, 30.0)
    rb = L.runner_for("192.168.20.1", "root", "analog", 22, 40.0)
    rows = []
    try:
        L.quiet_board(ra)
        L.reset_tx_dma(ra)
        iq = burst_iq(args.gap, ref=True, lead=args.lead)
        n = len(iq) // 2
        upload_bytes_via_ssh_cat(ra, payload=iq.tobytes(), remote_path="/tmp/burst.bin")
        L.sh(ra, f"echo {int(L.SAMPLE_RATE)} > {PHY}/out_voltage_sampling_frequency; "
                 f"echo {int(args.carrier)} > {PHY}/out_altvoltage1_TX_LO_frequency; "
                 f"echo {args.tx:.2f} > {PHY}/out_voltage0_hardwaregain; echo 0 > {PHY}/out_altvoltage1_TX_LO_powerdown")
        L.start_detached(ra, f"nohup iio_writedev -c -b {n} -s {n} cf-ad9361-dds-core-lpc voltage0 voltage1 "
                             "< /tmp/burst.bin > /tmp/burst.log 2>&1 &")
        L.sh(rb, f"echo {int(L.SAMPLE_RATE)} > {PHY}/in_voltage_sampling_frequency; "
                 f"echo {int(args.carrier)} > {PHY}/out_altvoltage0_RX_LO_frequency; "
                 f"echo manual > {PHY}/in_voltage0_gain_control_mode; echo {args.rx_gain} > {PHY}/in_voltage0_hardwaregain")
        time.sleep(3.0)
        for k in range(args.frames):
            r = qpsk_ber_once(rb, BASE, B.LONG_FRAME_SYMBOLS, k % 8, poll=3000, mode_bits=mode_bits,
                              preamble_bits=B.LONG_PREAMBLE_BITS)
            rows.append({key: r.get(key) for key in ("received_symbols", "payload_errors", "total_bit_errors",
                                                     "timed_out", "payload_error_position")})
        locked = [r for r in rows if r["received_symbols"] == B.LONG_FRAME_SYMBOLS]
        gross = [r for r in locked if (r["payload_errors"] or 0) > 8]
        print(f"locked {len(locked)}/{len(rows)}, clean {sum(1 for r in locked if not r['payload_errors'])}, gross {len(gross)}")
        for r in gross[:40]:
            pos = r["payload_error_position"] or {}
            print(f"  errors {r['payload_errors']:3d} total {r['total_bit_errors']:3d} quarters {pos.get('segment_errors')} "
                  f"first {pos.get('first_error_index')} last {pos.get('last_error_index')}")
    finally:
        L.sh(ra, "for p in $(ps | grep '[i]io_writedev' | awk '{print $1}'); do kill -9 $p; done")
        L.quiet_board(ra)
        L.sh(ra, f"echo 1 > {PHY}/out_altvoltage1_TX_LO_powerdown")
        L.sh(rb, f"echo manual > {PHY}/in_voltage0_gain_control_mode; echo 71 > {PHY}/in_voltage0_hardwaregain")
        L.quiet_board(rb)
        ra.client.close()
        rb.client.close()
        args.json_out.write_text(json.dumps({"args": {k: str(v) for k, v in vars(args).items()}, "mode_bits": hex(mode_bits),
                                             "rows": rows}, indent=2) + "\n", encoding="utf-8")
        print("wrote", args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
