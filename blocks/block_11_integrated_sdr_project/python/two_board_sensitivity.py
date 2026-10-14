#!/usr/bin/env python3
"""How weak can the signal get before the Lab 11.45 receiver stops decoding? Two boards, conducted.

    board A TX1 -> attenuators -> splitter -> board B RX1

Board A transmits the Lab 11.45 ROM frame (cyclic) and steps its TX attenuator, which was
measured to be accurate to about 0.5 dB over 60+ dB (ad9361-gain-steps-20261014.md), so the TX
setting is a trustworthy relative input level. Board B decodes in the fabric, in several receive
gain configurations; per point: locked frames, clean frames, gross frames, payload BER.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import lab_11_30_two_board_cfo_validation as L
import lab_11_32_two_board_fabric_coarse_cfo as B
from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat
from two_board_agc_ber import MODE, PHY, score


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--carrier", type=float, default=915e6)
    ap.add_argument("--tx-levels", type=float, nargs="+", default=[-10 - 5 * k for k in range(16)])
    ap.add_argument("--rx", nargs="+", default=["manual:71", "manual:50", "slow_attack"])
    ap.add_argument("--frames", type=int, default=100)
    ap.add_argument("--json-out", type=Path, required=True)
    args = ap.parse_args()

    ra = L.runner_for("192.168.40.1", "root", "analog", 22, 30.0)
    rb = L.runner_for("192.168.20.1", "root", "analog", 22, 40.0)
    res = {"carrier_hz": args.carrier, "mode_bits": hex(MODE), "frames": args.frames, "points": []}
    try:
        iq = B.make_long_preamble_frame(28, differential=True)
        n = len(iq) // 2
        L.quiet_board(ra)
        L.reset_tx_dma(ra)
        upload_bytes_via_ssh_cat(ra, payload=iq.tobytes(), remote_path="/tmp/lp.bin")
        L.sh(ra, f"echo {int(L.SAMPLE_RATE)} > {PHY}/out_voltage_sampling_frequency; "
                 f"echo {int(args.carrier)} > {PHY}/out_altvoltage1_TX_LO_frequency; "
                 f"echo {args.tx_levels[0]:.2f} > {PHY}/out_voltage0_hardwaregain; echo 0 > {PHY}/out_altvoltage1_TX_LO_powerdown")
        L.start_detached(ra, f"nohup iio_writedev -c -b {n} -s {n} cf-ad9361-dds-core-lpc voltage0 voltage1 "
                             "< /tmp/lp.bin > /tmp/lp.log 2>&1 &")
        time.sleep(3.0)
        L.sh(rb, f"echo {int(L.SAMPLE_RATE)} > {PHY}/in_voltage_sampling_frequency; "
                 f"echo {int(args.carrier)} > {PHY}/out_altvoltage0_RX_LO_frequency")
        for rx in args.rx:
            mode, _, gain = rx.partition(":")
            L.sh(rb, f"echo {mode} > {PHY}/in_voltage0_gain_control_mode")
            if gain:
                L.sh(rb, f"echo {gain} > {PHY}/in_voltage0_hardwaregain")
            for tx in args.tx_levels:
                L.sh(ra, f"echo {tx:.2f} > {PHY}/out_voltage0_hardwaregain")
                time.sleep(0.5)
                gains: list[float] = []
                r = score(rb, args.frames, gains)
                rssi = L.sh(rb, f"cat {PHY}/in_voltage0_rssi").split()[0]
                row = {"rx": rx, "tx_db": tx, "rssi_db": float(rssi), "rx_gain_min": min(gains), "rx_gain_max": max(gains), **r}
                res["points"].append(row)
                ber = r["payload_bit_errors"] / r["payload_bits"] if r["payload_bits"] else None
                print(f"{rx:12s} TX {tx:+6.1f}: locked {r['locked']:3d} clean {r['clean']:3d} gross {r['gross']:3d} "
                      f"BER {ber if ber is None else f'{ber:.1e}'} RSSI {rssi} gain {min(gains)}-{max(gains)}", flush=True)
                if r["locked"] == 0 and tx < args.tx_levels[0] - 20:
                    break
    finally:
        L.sh(ra, "for p in $(ps | grep '[i]io_writedev' | awk '{print $1}'); do kill -9 $p; done")
        L.quiet_board(ra)
        L.sh(ra, f"echo 1 > {PHY}/out_altvoltage1_TX_LO_powerdown")
        L.sh(rb, f"echo manual > {PHY}/in_voltage0_gain_control_mode; echo 71 > {PHY}/in_voltage0_hardwaregain")
        L.quiet_board(rb)
        ra.client.close()
        rb.client.close()
        args.json_out.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
        print("wrote", args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
