#!/usr/bin/env python3
"""Lab 11.44 - does differential QPSK remove the two-board rotation floor on hardware?

After the lock-tolerance fix the link sits at ~1% whole-burst rotation failures -- a genuine
carrier-marginal mis-resolution the frame sync cannot avoid. Differential QPSK (gp_ctrl[17]) removes
the ambiguity: the info is the phase difference between consecutive symbols, so a whole-burst rotation
cancels. The offline model and the RTL codec both show BER 0 under all four rotations (Lab 11.43).

This is the falsifiable hardware test. A/B on the SAME bench, each with its matching transmit frame:
  - diff OFF: absolute frame, mode without bit 17     -> the ~1% floor should still be there;
  - diff ON:  differential frame, mode with bit 17    -> the gross-rotation floor should collapse.

Board B must run the differential-capable image (gp_ctrl[17] wired). Bench: A TX1 -> 30 dB -> B RX1.
RF-safe: TX -30 dB, both quieted on exit.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import lab_11_30_two_board_cfo_validation as L
import lab_11_32_two_board_fabric_coarse_cfo as B
from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat
from lab_11_27_runtime_qpsk_digital_loopback import (
    QPSK_PAYLOAD_POSITION_BITS as POS,
    qpsk_ber_once,
)

ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"
BASE = 0x79040000
RF_MODE = 0x10 | 0x20 | 0x200 | 0x400 | 0x1000
GARDNER = 0x4000
DIFF = 0x20000                 # gp_ctrl[17]
GROSS = 8                      # > this many payload errors = a whole-burst rotation failure


def stream_frame(ra, sh, iq):
    """(Re)start board A's continuous cyclic transmit of the given int16 IQ frame."""
    n = len(iq) // 2
    sh(ra, "pkill -9 -f iio_writedev 2>/dev/null")
    time.sleep(0.5)
    L.reset_tx_dma(ra)
    upload_bytes_via_ssh_cat(ra, payload=iq.tobytes(), remote_path="/tmp/diff.bin")
    sh(ra, f"echo {int(L.SAMPLE_RATE)} > {B.PHY}/out_voltage_sampling_frequency 2>/dev/null")
    sh(ra, f"echo 915000000 > {B.PHY}/out_altvoltage1_TX_LO_frequency")
    sh(ra, f"echo -30.00 > {B.PHY}/out_voltage0_hardwaregain")
    sh(ra, f"echo 0 > {B.PHY}/out_altvoltage1_TX_LO_powerdown 2>/dev/null")
    L.start_detached(ra, f"nohup iio_writedev -c -b {n} -s {n} cf-ad9361-dds-core-lpc "
                         "voltage0 voltage1 < /tmp/diff.bin > /tmp/diff.log 2>&1 &")
    time.sleep(3.0)
    dac = sh(ra, f"devmem {L.DAC_CHAN_CNTRL_7_CH0}").strip()
    if dac not in ("0x00000002", "0x2"):
        raise RuntimeError(f"transmitter not on DMA: {dac}")


def sweep(rb, mode, frames, label):
    clean = single = gross = lost = err = bits = 0
    for i in range(frames):
        row = qpsk_ber_once(rb, BASE, 140, i % 8, mode_bits=mode, preamble_bits=24)
        if row.get("received_symbols") != 140:
            lost += 1
            continue
        pe = row.get("payload_errors") or 0
        err += pe
        bits += 256
        if pe == 0:
            clean += 1
        elif pe <= GROSS:
            single += 1
        else:
            gross += 1
    lk = clean + single + gross
    res = {"label": label, "frames": frames, "locked": lk, "lost": lost,
           "clean": clean, "single": single, "gross": gross,
           "clean_pct": 100 * clean / lk if lk else None,
           "gross_pct": 100 * gross / lk if lk else None,
           "payload_ber": err / bits if bits else None}
    print(f"{label:14s} lock {lk:3d}/{frames} clean {clean:3d} "
          f"({res['clean_pct']:.1f}%) single {single:3d} GROSS {gross:3d} "
          f"({res['gross_pct']:.1f}%) BER {res['payload_ber']:.2e}")
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=400)
    ap.add_argument("--json-out", type=Path, default=ASSET_DIR / "lab1144_diff_qpsk_live.json")
    args = ap.parse_args()

    iq_abs = B.make_cyclic_frame(29, differential=False)
    iq_diff = B.make_cyclic_frame(29, differential=True)
    ra = L.runner_for("192.168.40.1", "root", "analog", 22, 25.0)
    rb = L.runner_for("192.168.20.1", "root", "analog", 22, 40.0)

    def sh(r, c):
        return L.sh(r, c)

    payload = {"lab": "11.44"}
    try:
        L.quiet_board(rb)
        sh(rb, f"echo 915000000 > {B.PHY}/out_altvoltage0_RX_LO_frequency")
        sh(rb, f"echo {int(L.SAMPLE_RATE)} > {B.PHY}/in_voltage_sampling_frequency 2>/dev/null")
        sh(rb, f"echo manual > {B.PHY}/in_voltage0_gain_control_mode 2>/dev/null")
        sh(rb, f"echo 50 > {B.PHY}/in_voltage0_hardwaregain 2>/dev/null")
        L.quiet_board(ra)

        base = RF_MODE | POS | GARDNER
        print("board A: absolute frame")
        stream_frame(ra, sh, iq_abs)
        off = sweep(rb, base, args.frames, "diff OFF")

        print("board A: differential frame")
        stream_frame(ra, sh, iq_diff)
        on = sweep(rb, base | DIFF, args.frames, "diff ON")

        payload["diff_off"] = off
        payload["diff_on"] = on
        print("\nverdict:")
        if off["gross"] and on["gross"] <= max(1, 0.25 * off["gross"]):
            print(f"  differential QPSK removes the rotation floor: gross "
                  f"{off['gross_pct']:.1f}% -> {on['gross_pct']:.1f}%, clean "
                  f"{off['clean_pct']:.1f}% -> {on['clean_pct']:.1f}%")
        elif on["gross"] >= off["gross"]:
            print("  no improvement -- check the diff frame/gate pairing (both halves must be differential)")
        else:
            print(f"  partial: gross {off['gross_pct']:.1f}% -> {on['gross_pct']:.1f}%")
    finally:
        try:
            sh(ra, "pkill -9 -f iio_writedev 2>/dev/null")
            L.quiet_board(ra)
            L.quiet_board(rb)
            print("\nboth boards quiet (-89.75 dB)")
        except Exception as exc:
            print("cleanup warning:", exc)
        ra.client.close()
        rb.client.close()

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
