#!/usr/bin/env python3
"""Resolve the bit-189 fork: does the decoder really get that bit wrong, or is the index wrong?

Everything else is excluded. The index arithmetic is correct, the delivered signal carries a healthy
mid-ranked margin at symbol 106, the offline waveform never makes that bit the first to fail, and the
failure is invariant to start offset and carrier. What was missing was the decoder's own output.

Board B now exports it (gp_ctrl[16]). For every burst the on-chip telemetry flags as a single payload
error at index 189, this reads the decoded frame back and compares it to the ROM:

  - bit 189 genuinely differs        -> the decoder errs; the cause is inside the receive chain
  - bit 189 matches, another differs -> the reported INDEX is wrong, and every conclusion drawn
                                        about "symbol 106" has to be revisited

Bench: board A TX1 -> 30 dB attenuator -> board B RX1. RF-safe: TX -30 dB, both quieted on exit.
"""
import time
from collections import Counter

import lab_11_30_two_board_cfo_validation as L
import lab_11_32_two_board_fabric_coarse_cfo as B
from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat
from lab_11_27_runtime_qpsk_digital_loopback import qpsk_ber_once, QPSK_PAYLOAD_POSITION_BITS as POS
from decoded_bit_readout import align_to_rom, frame_rom, read_decoded

BASE = 0x79040000
RF_MODE = 0x10 | 0x20 | 0x200 | 0x400 | 0x1000
PREAMBLE_BITS = 24
PREAMBLE_BITS_CONST = 24
TARGET = 189                      # payload index reported by the chip
TARGET_FRAME_BIT = TARGET + PREAMBLE_BITS_CONST  # align_to_rom returns FRAME bit indices
WANT_FAIL = 10
WANT_CLEAN = 3
# A readout only counts as evidence if it actually captured the frame. The register keeps the
# last 288 bits and the frame is 280, so if the shift froze more than 4 symbols past the frame
# end the frame is partly outside the window and the comparison is noise (~140 mismatches).
MAX_CREDIBLE_MISMATCH = 8


def main() -> int:
    rom = frame_rom()
    iq = B.make_cyclic_frame(29)
    n_samples = len(iq) // 2
    ra = L.runner_for("192.168.40.1", "root", "analog", 22, 25.0)
    rb = L.runner_for("192.168.20.1", "root", "analog", 22, 40.0)

    def sh(r, c):
        return L.sh(r, c)

    fails, cleans = [], []
    try:
        L.quiet_board(rb)
        sh(rb, f"echo 915000000 > {B.PHY}/out_altvoltage0_RX_LO_frequency")
        sh(rb, f"echo {int(L.SAMPLE_RATE)} > {B.PHY}/in_voltage_sampling_frequency 2>/dev/null")
        sh(rb, f"echo manual > {B.PHY}/in_voltage0_gain_control_mode 2>/dev/null")
        sh(rb, f"echo 50 > {B.PHY}/in_voltage0_hardwaregain 2>/dev/null")

        L.quiet_board(ra)
        L.reset_tx_dma(ra)
        upload_bytes_via_ssh_cat(ra, payload=iq.tobytes(), remote_path="/tmp/b189.bin")
        sh(ra, f"echo {int(L.SAMPLE_RATE)} > {B.PHY}/out_voltage_sampling_frequency 2>/dev/null")
        sh(ra, f"echo 915000000 > {B.PHY}/out_altvoltage1_TX_LO_frequency")
        sh(ra, f"echo -30.00 > {B.PHY}/out_voltage0_hardwaregain")
        sh(ra, f"echo 0 > {B.PHY}/out_altvoltage1_TX_LO_powerdown 2>/dev/null")
        L.start_detached(ra, f"nohup iio_writedev -c -b {n_samples} -s {n_samples} "
                             "cf-ad9361-dds-core-lpc voltage0 voltage1 < /tmp/b189.bin "
                             "> /tmp/b189.log 2>&1 &")
        time.sleep(3.0)
        dac = sh(ra, f"devmem {L.DAC_CHAN_CNTRL_7_CH0}").strip()
        if dac not in ("0x00000002", "0x2"):
            raise RuntimeError(f"transmitter not on DMA: {dac}")
        print(f"board A streaming (DAC={dac})\n")

        mode = RF_MODE | POS
        for attempt in range(700):
            row = qpsk_ber_once(rb, BASE, 140, attempt % 8, mode_bits=mode,
                                preamble_bits=PREAMBLE_BITS)
            if row.get("received_symbols") != 140:
                continue
            pe = row.get("payload_errors") or 0
            pos = row.get("payload_error_position")
            single_189 = (pe == 1 and isinstance(pos, dict)
                          and pos.get("first_error_index") == TARGET)
            if not (single_189 and len(fails) < WANT_FAIL) and not (pe == 0 and len(cleans) < WANT_CLEAN):
                continue
            value, count = read_decoded(rb, mode)          # before any further burst resets it
            best = align_to_rom(value, count, rom)
            rec = {"attempt": attempt, "offset": attempt % 8, "payload_errors": pe,
                   "count": count, "align": best}
            (fails if single_189 else cleans).append(rec)
            if len(fails) >= WANT_FAIL and len(cleans) >= WANT_CLEAN:
                break

        print(f"collected {len(fails)} single-error-at-{TARGET} frames, {len(cleans)} clean frames\n")
        hits = Counter()
        credible = 0
        for rec in fails:
            if rec["align"] is None:
                print(f"  attempt {rec['attempt']}: readout did not align (count={rec['count']})")
                continue
            rot, soff, bad = rec["align"]
            if len(bad) > MAX_CREDIBLE_MISMATCH:
                print(f"  attempt {rec['attempt']:3d} count={rec['count']}: frame NOT in the capture "
                      f"window ({len(bad)} mismatches) -- discarded, not evidence")
                continue
            credible += 1
            hits.update(bad)
            says = ("payload bit 189 IS wrong (frame bit 213)" if TARGET_FRAME_BIT in bad
                    else "payload bit 189 is CORRECT -- index misreported")
            print(f"  attempt {rec['attempt']:3d} off={rec['offset']} count={rec['count']} soff={soff}: "
                  f"rot={rot:9s} decoder disagrees with the ROM at {len(bad)} bit(s) {bad[:6]} -> {says}")
        for rec in cleans:
            _rot, _soff, bad = rec["align"] or (None, None, None)
            print(f"  [clean] attempt {rec['attempt']:3d}: mismatching bits = "
                  f"{len(bad) if bad is not None else 'n/a'}")

        if hits:
            print("\nframe bits where the decoder disagreed with the ROM:")
            for bit, n in hits.most_common(8):
                mark = "   <== the index the chip reported" if bit == TARGET_FRAME_BIT else ""
                print(f"   frame bit {bit:3d} (payload {bit - PREAMBLE_BITS_CONST:3d}): "
                      f"{n}/{credible} credible frames{mark}")
            unanimous = credible > 0 and hits.get(TARGET_FRAME_BIT, 0) == credible
            only_target = set(hits) == {TARGET_FRAME_BIT}
            print(f"\ncredible readouts: {credible} of {len(fails)}")
            print("VERDICT:", "index CORRECT -- the decoder really does get payload "
                  f"{TARGET} wrong ({credible}/{credible} frames, and no other bit differs)"
                  if unanimous and only_target else
                  "NOT unanimous -- read the per-frame lines above before concluding anything")
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
