#!/usr/bin/env python3
"""Issue #58: what the AD9361 receive gain control does to the modem, on two boards.

Board A streams the Lab 11.45 frame; board B decodes it in the fabric. For each receive gain
mode (manual at a fixed gain, slow_attack, fast_attack):

* static: N frames at each of several TX levels, with the gain left to settle first;
* dynamic: N frames while board A toggles its TX gain between two levels every `--period`
  seconds (a shell loop on board A), so some frames straddle a gain transition.

Reports locked / clean / single-bit / gross frames and the payload BER, plus the receive gain
readback range seen during the dynamic run. Both boards are quieted on exit.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import lab_11_30_two_board_cfo_validation as L
import lab_11_32_two_board_fabric_coarse_cfo as B
from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat
from lab_11_27_runtime_qpsk_digital_loopback import QPSK_PAYLOAD_POSITION_BITS as POS, qpsk_ber_once

PHY = L.PHY
BASE = 0x79040000
MODE = 0x10 | 0x20 | 0x200 | 0x400 | 0x1000 | POS | 0x4000 | 0x20000   # Lab 11.45
GROSS = 8


def score(rb, frames: int, gain_samples: list | None = None) -> dict:
    clean = single = gross = err = bits = 0
    for k in range(frames):
        row = qpsk_ber_once(rb, BASE, B.LONG_FRAME_SYMBOLS, k % 8, mode_bits=MODE,
                            preamble_bits=B.LONG_PREAMBLE_BITS)
        if gain_samples is not None and k % 5 == 0:
            gain_samples.append(float(L.sh(rb, f"cat {PHY}/in_voltage0_hardwaregain").split()[0]))
        if row.get("received_symbols") != B.LONG_FRAME_SYMBOLS:
            continue
        pe = row.get("payload_errors") or 0
        err, bits = err + pe, bits + 256
        clean += pe == 0
        single += 0 < pe <= GROSS
        gross += pe > GROSS
    return {"frames": frames, "locked": clean + single + gross, "clean": clean, "single_bit": single,
            "gross": gross, "payload_bit_errors": err, "payload_bits": bits}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--carrier", type=float, default=915e6)
    ap.add_argument("--modes", nargs="+", default=["manual", "slow_attack", "fast_attack"])
    ap.add_argument("--manual-rx-gain", type=int, default=50)
    ap.add_argument("--levels", type=float, nargs="+", default=[-40, -30, -20, -10, 0])
    ap.add_argument("--toggle", type=float, nargs=2, default=[-30, -10], help="dynamic run: two TX gains")
    ap.add_argument("--period", type=float, default=0.3, help="dynamic run: seconds per level")
    ap.add_argument("--frames", type=int, default=60)
    ap.add_argument("--dynamic-only", action="store_true", help="skip the static levels")
    ap.add_argument("--bench", required=True)
    ap.add_argument("--json-out", type=Path, required=True)
    args = ap.parse_args()

    iq = B.make_long_preamble_frame(29, differential=True)
    n = len(iq) // 2
    ra = L.runner_for("192.168.40.1", "root", "analog", 22, 25.0)
    rb = L.runner_for("192.168.20.1", "root", "analog", 22, 40.0)
    sh = L.sh
    res = {"issue": 58, "bench": args.bench, "carrier_hz": args.carrier, "mode_bits": hex(MODE),
           "manual_rx_gain_db": args.manual_rx_gain, "toggle_db": args.toggle, "period_s": args.period,
           "static": [], "dynamic": []}
    try:
        L.quiet_board(rb)
        sh(rb, f"echo {int(args.carrier)} > {PHY}/out_altvoltage0_RX_LO_frequency")
        sh(rb, f"echo {int(L.SAMPLE_RATE)} > {PHY}/in_voltage_sampling_frequency 2>/dev/null")
        L.quiet_board(ra)
        L.reset_tx_dma(ra)
        upload_bytes_via_ssh_cat(ra, payload=iq.tobytes(), remote_path="/tmp/lp.bin")
        sh(ra, f"echo {int(L.SAMPLE_RATE)} > {PHY}/out_voltage_sampling_frequency 2>/dev/null")
        sh(ra, f"echo {int(args.carrier)} > {PHY}/out_altvoltage1_TX_LO_frequency")
        sh(ra, f"echo {min(args.levels):.2f} > {PHY}/out_voltage0_hardwaregain")
        sh(ra, f"echo 0 > {PHY}/out_altvoltage1_TX_LO_powerdown 2>/dev/null")
        L.start_detached(ra, f"nohup iio_writedev -c -b {n} -s {n} cf-ad9361-dds-core-lpc "
                             "voltage0 voltage1 < /tmp/lp.bin > /tmp/lp.log 2>&1 &")
        time.sleep(3.0)
        if sh(ra, f"devmem {L.DAC_CHAN_CNTRL_7_CH0}").strip() not in ("0x00000002", "0x2"):
            raise RuntimeError("transmitter not on DMA")
        lo, hi = args.toggle
        sh(ra, "cat > /tmp/toggle.sh << 'EOF'\n"
               f"while true; do echo {lo:.2f} > {PHY}/out_voltage0_hardwaregain; sleep {args.period}; "
               f"echo {hi:.2f} > {PHY}/out_voltage0_hardwaregain; sleep {args.period}; done\nEOF")
        for mode in args.modes:
            sh(rb, f"echo {mode} > {PHY}/in_voltage0_gain_control_mode")
            if mode == "manual":
                sh(rb, f"echo {args.manual_rx_gain} > {PHY}/in_voltage0_hardwaregain")
            for tx in ([] if args.dynamic_only else args.levels):
                sh(ra, f"echo {tx:.2f} > {PHY}/out_voltage0_hardwaregain")
                time.sleep(1.0)
                g = sh(rb, f"cat {PHY}/in_voltage0_hardwaregain").strip()
                r = {"mode": mode, "tx_gain_db": tx, "rx_gain": g, **score(rb, args.frames)}
                res["static"].append(r)
                print(json.dumps(r))
            gains: list[float] = []
            L.start_detached(ra, "nohup sh /tmp/toggle.sh > /dev/null 2>&1 &")
            try:
                r = {"mode": mode, **score(rb, args.frames, gains)}
            finally:
                sh(ra, "for p in $(ps | grep '[t]oggle.sh' | awk '{print $1}'); do kill -9 $p; done")
            r["rx_gain_min"] = min(gains) if gains else None
            r["rx_gain_max"] = max(gains) if gains else None
            res["dynamic"].append(r)
            print(json.dumps(r))
    finally:
        try:
            sh(ra, "for p in $(ps | grep '[t]oggle.sh' | awk '{print $1}'); do kill -9 $p; done; for p in $(ps | grep '[i]io_writedev' | awk '{print $1}'); do kill -9 $p; done")
            L.quiet_board(ra)
            sh(rb, f"echo manual > {PHY}/in_voltage0_gain_control_mode")
            sh(rb, f"echo 71 > {PHY}/in_voltage0_hardwaregain")
            L.quiet_board(rb)
            print("both boards quiet (-89.75 dB), board B back to manual 71 dB")
        except Exception as exc:  # noqa: BLE001
            print("cleanup warning:", exc)
        ra.client.close()
        rb.client.close()
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
        print("wrote", args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
