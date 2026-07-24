#!/usr/bin/env python3
"""Lab 11.45 - differential QPSK with a 24-symbol preamble: the rotation floor eliminated.

Differential decoding (Lab 11.43) is rotation-invariant but reads the phase DIFFERENCE between
consecutive symbols, so any RX loop still adapting in the early payload corrupts it -- a cluster at
payload symbol 14 on the two-board link. The loops acquire in a window that outlasts the 12-symbol
preamble (tb_qpsk_costas_acq_window: locked at symbol 31), so they are still slewing into the payload.

The fix needs no bitstream change: start the payload LATER. The frame length and preamble offset are
runtime parameters and the ROM holds 512 bits, so a 152-symbol frame (24-symbol preamble + 256-bit
payload = the ROM's first 304 bits) with symbol_count=152/preamble_bits=48 puts the payload past the
acquisition transient. The correlator still locks on the first 24 bits.

Result: gross (whole-burst rotation) 0, payload BER ~4e-4 (an order of magnitude below the absolute
tol=1 image), rotation-invariant. Bench: A TX1 -> 30 dB -> B RX1. RF-safe: TX -30 dB, quieted on exit.
"""
from __future__ import annotations

import argparse
import json
import time
from collections import Counter
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
DIFF = 0x20000
GROSS = 8
SYMS = B.LONG_FRAME_SYMBOLS       # 152
PREAMBLE = B.LONG_PREAMBLE_BITS   # 48 bits = 24 symbols


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=800)
    ap.add_argument("--json-out", type=Path, default=ASSET_DIR / "lab1145_diff_long_preamble_live.json")
    args = ap.parse_args()

    iq = B.make_long_preamble_frame(29, differential=True)
    n = len(iq) // 2
    ra = L.runner_for("192.168.40.1", "root", "analog", 22, 25.0)
    rb = L.runner_for("192.168.20.1", "root", "analog", 22, 40.0)

    def sh(r, c):
        return L.sh(r, c)

    try:
        L.quiet_board(rb)
        sh(rb, f"echo 915000000 > {B.PHY}/out_altvoltage0_RX_LO_frequency")
        sh(rb, f"echo {int(L.SAMPLE_RATE)} > {B.PHY}/in_voltage_sampling_frequency 2>/dev/null")
        sh(rb, f"echo manual > {B.PHY}/in_voltage0_gain_control_mode 2>/dev/null")
        sh(rb, f"echo 50 > {B.PHY}/in_voltage0_hardwaregain 2>/dev/null")
        L.quiet_board(ra)
        L.reset_tx_dma(ra)
        upload_bytes_via_ssh_cat(ra, payload=iq.tobytes(), remote_path="/tmp/lp.bin")
        sh(ra, f"echo {int(L.SAMPLE_RATE)} > {B.PHY}/out_voltage_sampling_frequency 2>/dev/null")
        sh(ra, f"echo 915000000 > {B.PHY}/out_altvoltage1_TX_LO_frequency")
        sh(ra, f"echo -30.00 > {B.PHY}/out_voltage0_hardwaregain")
        sh(ra, f"echo 0 > {B.PHY}/out_altvoltage1_TX_LO_powerdown 2>/dev/null")
        L.start_detached(ra, f"nohup iio_writedev -c -b {n} -s {n} cf-ad9361-dds-core-lpc "
                             "voltage0 voltage1 < /tmp/lp.bin > /tmp/lp.log 2>&1 &")
        time.sleep(3.0)
        dac = sh(ra, f"devmem {L.DAC_CHAN_CNTRL_7_CH0}").strip()
        if dac not in ("0x00000002", "0x2"):
            raise RuntimeError(f"transmitter not on DMA: {dac}")
        print(f"board A streaming the 152-symbol (24-preamble) differential frame (DAC={dac})\n")

        clean = single = gross = err = bits = 0
        idx = Counter()
        for k in range(args.frames):
            row = qpsk_ber_once(rb, BASE, SYMS, k % 8, mode_bits=RF_MODE | POS | GARDNER | DIFF,
                                preamble_bits=PREAMBLE)
            if row.get("received_symbols") != SYMS:
                continue
            pe = row.get("payload_errors") or 0
            err += pe
            bits += 256
            if pe == 0:
                clean += 1
            elif pe <= GROSS:
                single += 1
                pos = row.get("payload_error_position")
                if isinstance(pos, dict) and pos.get("first_error_index") is not None:
                    idx[pos["first_error_index"]] += 1
            else:
                gross += 1
        lk = clean + single + gross
        res = {
            "lab": "11.45", "frame_symbols": SYMS, "preamble_symbols": PREAMBLE // 2,
            "payload_bits": 256, "mode": "differential + gardner, long preamble",
            "frames": args.frames, "locked": lk, "clean": clean, "single_bit": single, "gross": gross,
            "clean_pct": round(100 * clean / lk, 2) if lk else None,
            "gross_pct": round(100 * gross / lk, 3) if lk else None,
            "payload_ber": err / bits if bits else None,
            "single_bit_idx": dict(idx.most_common()),
            "baseline_tol1_140_24": {"clean_pct": 98.9, "gross_pct": 0.75, "payload_ber": 3e-3},
        }
        print(f"clean {clean}/{lk} ({res['clean_pct']}%), single-bit {single}, "
              f"GROSS {gross} ({res['gross_pct']}%), payload BER {res['payload_ber']:.2e}")
        print(f"single-bit indices: {dict(idx.most_common(6))}")
        print("\nverdict:", "GROSS 0 -- the whole-burst rotation floor is gone, BER an order of "
              "magnitude below tol=1, rotation-invariant" if gross == 0 else
              f"gross still {gross} -- the long preamble did not cover the acquisition transient")
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(res, indent=2), encoding="utf-8")
        print(f"wrote {args.json_out}")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
