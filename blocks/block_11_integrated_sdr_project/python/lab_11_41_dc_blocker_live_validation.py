#!/usr/bin/env python3
"""Lab 11.41 - does fixing the DC blocker remove the bit-189 failure on hardware?

The offline model says the fixed-K blocker made payload bit 189 the weakest of 256 decisions (margin
0.336 against a 0.99 median) and that the running-average version restores it to 0.913. It also
predicted, and matched, the full live histogram. This is the measurement that decides whether the
model was right about the hardware.

The prediction is specific and falsifiable, which is the point: bit 189 should stop dominating the
single-bit errors. If it still takes the great majority of them, the model is wrong regardless of how
well it fits the old data.

Bench: board A TX1 -> 30 dB attenuator -> board B RX1. Board B must be running the rebuilt image.
RF-safe: TX -30 dB into a cable, both boards quieted to -89.75 dB on exit.
"""
from __future__ import annotations

import argparse
import hashlib
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
COURSE_BITSTREAM = (
    ROOT / "hardware" / "7020_ad936x_sdr" / "hdl" / "course_bpsk_fmcomms2_zc702" / "system.bit.bin"
)
ASSET_DIR = ROOT / "docs" / "assets"

BASE = 0x79040000
RF_MODE = 0x10 | 0x20 | 0x200 | 0x400 | 0x1000     # QPSK | raw | DC block | Costas | phase pick
GARDNER = 0x4000
TARGET = 189
PAYLOAD_BITS = 256

# The 160-pair campaign on the fixed-K image, counted per sampler run (see Lab 11.35).
BASELINE = {"single_bit": {189: 37, 2: 2, 173: 1}, "single_bit_total": 40}


def campaign(rb, mode: int, frames: int, label: str) -> dict:
    singles: Counter[int] = Counter()
    locked = clean = errors = 0
    for i in range(frames):
        row = qpsk_ber_once(rb, BASE, 140, i % 8, mode_bits=mode, preamble_bits=24)
        if row.get("received_symbols") != 140:
            continue
        locked += 1
        pe = row.get("payload_errors") or 0
        errors += pe
        if pe == 0:
            clean += 1
        pos = row.get("payload_error_position")
        if pe == 1 and isinstance(pos, dict) and pos.get("first_error_index") is not None:
            singles[pos["first_error_index"]] += 1
    total = sum(singles.values())
    at_target = singles.get(TARGET, 0)
    result = {
        "label": label, "attempts": frames, "locked": locked, "clean": clean,
        "payload_errors": errors,
        "payload_ber": errors / (PAYLOAD_BITS * locked) if locked else None,
        "single_bit_total": total, "single_bit_at_target": at_target,
        "single_bit_histogram": dict(sorted(singles.items())),
    }
    print(f"\n{label}")
    print(f"   locked {locked}/{frames}, clean {clean} "
          f"({100 * clean / locked:.1f}% of locked)" if locked else "   never locked")
    if locked:
        print(f"   payload BER {result['payload_ber']:.3e} ({errors} errors in {PAYLOAD_BITS * locked} bits)")
    print(f"   single-bit frames {total}, at bit {TARGET}: {at_target}"
          + (f" ({100 * at_target / total:.0f}%)" if total else ""))
    if total:
        print(f"   histogram {result['single_bit_histogram']}")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=300)
    ap.add_argument("--bitstream", type=Path, default=COURSE_BITSTREAM)
    ap.add_argument("--json-out", type=Path,
                    default=ASSET_DIR / "lab1141_dc_blocker_live_validation.json")
    args = ap.parse_args()

    payload = {"lab": "11.41", "target_bit": TARGET, "baseline_fixed_k": BASELINE}
    if args.bitstream.exists():
        digest = hashlib.sha256(args.bitstream.read_bytes()).hexdigest()
        payload["bitstream"] = {"path": str(args.bitstream), "sha256": digest}
        print(f"board B image under test: {digest}")

    iq = B.make_cyclic_frame(29)
    n_samples = len(iq) // 2
    ra = L.runner_for("192.168.40.1", "root", "analog", 22, 25.0)
    rb = L.runner_for("192.168.20.1", "root", "analog", 22, 40.0)

    try:
        L.quiet_board(rb)
        L.sh(rb, f"echo 915000000 > {B.PHY}/out_altvoltage0_RX_LO_frequency")
        L.sh(rb, f"echo {int(L.SAMPLE_RATE)} > {B.PHY}/in_voltage_sampling_frequency 2>/dev/null")
        L.sh(rb, f"echo manual > {B.PHY}/in_voltage0_gain_control_mode 2>/dev/null")
        L.sh(rb, f"echo 50 > {B.PHY}/in_voltage0_hardwaregain 2>/dev/null")

        L.quiet_board(ra)
        L.reset_tx_dma(ra)
        upload_bytes_via_ssh_cat(ra, payload=iq.tobytes(), remote_path="/tmp/dcb41.bin")
        L.sh(ra, f"echo {int(L.SAMPLE_RATE)} > {B.PHY}/out_voltage_sampling_frequency 2>/dev/null")
        L.sh(ra, f"echo 915000000 > {B.PHY}/out_altvoltage1_TX_LO_frequency")
        L.sh(ra, f"echo -30.00 > {B.PHY}/out_voltage0_hardwaregain")
        L.sh(ra, f"echo 0 > {B.PHY}/out_altvoltage1_TX_LO_powerdown 2>/dev/null")
        L.start_detached(ra, f"nohup iio_writedev -c -b {n_samples} -s {n_samples} "
                             "cf-ad9361-dds-core-lpc voltage0 voltage1 < /tmp/dcb41.bin "
                             "> /tmp/dcb41.log 2>&1 &")
        time.sleep(3.0)
        dac = L.sh(ra, f"devmem {L.DAC_CHAN_CNTRL_7_CH0}").strip()
        if dac not in ("0x00000002", "0x2"):
            raise RuntimeError(f"transmitter not on DMA: {dac}")
        print(f"board A streaming (DAC={dac})")

        runs = [
            campaign(rb, RF_MODE | POS, args.frames, "fixed-phase sampler"),
            campaign(rb, RF_MODE | POS | GARDNER, args.frames, "Gardner sampler"),
        ]
        payload["runs"] = runs

        total = sum(r["single_bit_total"] for r in runs)
        at_target = sum(r["single_bit_at_target"] for r in runs)
        base_share = BASELINE["single_bit"][TARGET] / BASELINE["single_bit_total"]
        share = at_target / total if total else None
        payload["verdict"] = {
            "single_bit_total": total, "single_bit_at_target": at_target,
            "share_at_target": share, "baseline_share_at_target": base_share,
        }
        print(f"\nbit {TARGET} share of single-bit errors: baseline {100 * base_share:.0f}% "
              f"({BASELINE['single_bit'][TARGET]}/{BASELINE['single_bit_total']}) -> now "
              + (f"{100 * share:.0f}% ({at_target}/{total})" if total else "no single-bit frames"))
        if total == 0:
            print("VERDICT: no single-bit frames at all -- inconclusive on the histogram, "
                  "read the BER and clean-frame counts above")
        elif share < 0.5 * base_share:
            print("VERDICT: bit 189 no longer dominates -- the model predicted the hardware")
        else:
            print("VERDICT: bit 189 STILL dominates. The DC blocker was not the cause, or not the "
                  "only one; do not let the offline model overrule this.")
    finally:
        try:
            L.sh(ra, "pkill -9 -f iio_writedev 2>/dev/null")
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
