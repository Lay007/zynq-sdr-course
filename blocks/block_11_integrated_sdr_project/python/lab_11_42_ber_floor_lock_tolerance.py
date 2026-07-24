#!/usr/bin/env python3
"""Lab 11.42 - characterise and close the two-board Gardner BER floor.

After the DC-blocker fix the link is ~92% clean, but a residual few percent of bursts decode at ~46%
BER from bit 0 -- a whole-burst 90-degree rotation, not marginal SNR. This tool measures the floor and
proves it is a frame-sync FALSE LOCK rather than any channel effect. The operating-point map that
falsified the "just turn a knob" hypotheses (coarse CFO, costas_hold_phase, start_offset, and TX/RX
gain, all of which leave a ~3% floor) is recorded in Lab 11.42; the arithmetic below is what pins the
cause.

Mechanism, confirmed by both hardware and arithmetic: the frame-sync arbitration is first-past-the-post
over a sliding 24-bit preamble correlation. A wrong quadrant matches each preamble bit with prob ~0.5,
so a chance window with <= LOCK_ERR_TOL errors has probability C(24, <=tol)/2^24 per position; over the
~140 sliding positions of a burst that is ~2% at tol=3 -- matching the measured floor. Tightening
LOCK_ERR_TOL to 1 cuts it ~100x. See spurious_lock_probability() below and dc_blocker_margin.py's
sibling reasoning.

Modes:
  (default)  run Gardner bursts, split clean / single-bit / gross, and anatomise the gross frames via
             the gp_ctrl[15] position telemetry (which quarter fails first, where the first error is).
  --predict  print the spurious-lock probability vs LOCK_ERR_TOL -- no bench needed.

Bench: A TX1 -> 30 dB -> B RX1. RF-safe: TX -30 dB, both quieted on exit.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from math import comb

sys.path.insert(0, "g:/Programs/zynq-sdr-course/blocks/block_11_integrated_sdr_project/python")

BASE = 0x79040000
RF_MODE = 0x10 | 0x20 | 0x200 | 0x400 | 0x1000
GARDNER = 0x4000
PREAMBLE_BITS = 24
SLIDING_POSITIONS = 140          # ~ symbols the sampler emits per burst that the correlator scans
GROSS = 8                        # > this many payload errors = a gross (whole-burst) failure


def spurious_lock_probability(tol: int, preamble: int = PREAMBLE_BITS,
                              positions: int = SLIDING_POSITIONS) -> float:
    """P(a wrong-rotation branch false-locks somewhere in the burst) for a given LOCK_ERR_TOL.

    A wrong quadrant matches each preamble bit with prob 1/2, so the per-position chance of <= tol
    mismatches is C(preamble, <=tol) / 2^preamble; independent-ish over `positions` sliding windows.
    """
    per_pos = sum(comb(preamble, k) for k in range(tol + 1)) / (2 ** preamble)
    return 1.0 - (1.0 - per_pos) ** positions


def predict() -> int:
    print(f"spurious wrong-rotation lock probability vs LOCK_ERR_TOL "
          f"(preamble {PREAMBLE_BITS} bits, ~{SLIDING_POSITIONS} sliding positions):")
    for tol in range(4):
        per_pos = sum(comb(PREAMBLE_BITS, k) for k in range(tol + 1)) / (2 ** PREAMBLE_BITS)
        print(f"   LOCK_ERR_TOL={tol}: per-position {per_pos:.2e} -> per-burst "
              f"{spurious_lock_probability(tol):.2e}")
    print("\nMeasured two-board floor at tol=3 was ~2-3% of bursts, matching the ~2% above.")
    return 0


def run(frames: int) -> int:
    import time

    import lab_11_30_two_board_cfo_validation as L
    import lab_11_32_two_board_fabric_coarse_cfo as B
    from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat
    from lab_11_27_runtime_qpsk_digital_loopback import (
        QPSK_PAYLOAD_POSITION_BITS as POS,
        qpsk_ber_once,
    )

    iq = B.make_cyclic_frame(29)
    n = len(iq) // 2
    ra = L.runner_for("192.168.40.1", "root", "analog", 22, 25.0)
    rb = L.runner_for("192.168.20.1", "root", "analog", 22, 40.0)

    def sh(r, c):
        return L.sh(r, c)

    clean = single = gross = 0
    q_first = Counter()
    q0_clean = 0
    first_bin = Counter()
    try:
        L.quiet_board(rb)
        sh(rb, f"echo 915000000 > {B.PHY}/out_altvoltage0_RX_LO_frequency")
        sh(rb, f"echo {int(L.SAMPLE_RATE)} > {B.PHY}/in_voltage_sampling_frequency 2>/dev/null")
        sh(rb, f"echo manual > {B.PHY}/in_voltage0_gain_control_mode 2>/dev/null")
        sh(rb, f"echo 50 > {B.PHY}/in_voltage0_hardwaregain 2>/dev/null")
        L.quiet_board(ra)
        L.reset_tx_dma(ra)
        upload_bytes_via_ssh_cat(ra, payload=iq.tobytes(), remote_path="/tmp/floor42.bin")
        sh(ra, f"echo {int(L.SAMPLE_RATE)} > {B.PHY}/out_voltage_sampling_frequency 2>/dev/null")
        sh(ra, f"echo 915000000 > {B.PHY}/out_altvoltage1_TX_LO_frequency")
        sh(ra, f"echo -30.00 > {B.PHY}/out_voltage0_hardwaregain")
        sh(ra, f"echo 0 > {B.PHY}/out_altvoltage1_TX_LO_powerdown 2>/dev/null")
        L.start_detached(ra, f"nohup iio_writedev -c -b {n} -s {n} cf-ad9361-dds-core-lpc "
                             "voltage0 voltage1 < /tmp/floor42.bin > /tmp/floor42.log 2>&1 &")
        time.sleep(3.0)
        dac = sh(ra, f"devmem {L.DAC_CHAN_CNTRL_7_CH0}").strip()
        if dac not in ("0x00000002", "0x2"):
            raise RuntimeError(f"transmitter not on DMA: {dac}")
        print(f"board A streaming (DAC={dac})\n")

        mode = RF_MODE | POS | GARDNER
        for i in range(frames):
            row = qpsk_ber_once(rb, BASE, 140, i % 8, mode_bits=mode, preamble_bits=PREAMBLE_BITS)
            if row.get("received_symbols") != 140:
                continue
            pe = row.get("payload_errors") or 0
            if pe == 0:
                clean += 1
                continue
            if pe <= GROSS:
                single += 1
                continue
            gross += 1
            pos = row.get("payload_error_position")
            if isinstance(pos, dict):
                seg = pos.get("segment_errors") or [None] * 4
                if seg[0] == 0:
                    q0_clean += 1
                for qi, c in enumerate(seg):
                    if c:
                        q_first[qi] += 1
                        break
                fi = pos.get("first_error_index")
                if fi is not None:
                    first_bin[fi // 32] += 1

        lk = clean + single + gross
        print(f"locked {lk}/{frames}: clean {clean} ({100*clean/lk:.1f}%), "
              f"single-bit {single}, GROSS {gross} ({100*gross/lk:.1f}%)")
        if gross:
            print(f"gross anatomy: quarter-0 clean in {q0_clean}/{gross} "
                  f"({100*q0_clean/gross:.0f}% -> low means the whole burst is wrong from bit 0, a "
                  f"rotation not a mid-frame slip)")
            print(f"  first errored quarter: {dict(sorted(q_first.items()))}")
            print(f"  first_error_index by 32-bit bin: {dict(sorted(first_bin.items()))}")
        print("\nexpected spurious-lock floor at the SHIPPED LOCK_ERR_TOL: see --predict")
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--predict", action="store_true", help="print the false-lock math, no bench")
    ap.add_argument("--frames", type=int, default=400)
    args = ap.parse_args()
    return predict() if args.predict else run(args.frames)


if __name__ == "__main__":
    raise SystemExit(main())
