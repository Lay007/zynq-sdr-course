#!/usr/bin/env python3
"""Does the bit-189 failure move with the carrier?

start_offset is already ruled out: in the 160-pair campaign the single-bit error sits at index 189
at all eight offsets. This varies the carrier instead, which changes the analog conditions (LO, DC
offset, filter response, AGC point) while leaving the frame data and the bit indexing untouched.

  - index stays at 189 across carriers -> the failure is locked to the data or to the index, not to
    the analog path;
  - index moves -> it is an analog/channel-dependent decision after all.

Gardner (gp_ctrl[14]) is used as the probe because it yields ~5x more single-bit frames than fixed.
RF-safe: TX -30 dB behind the 30 dB pad, both boards quieted on exit.
"""
import collections
import sys
import time


sys.path.insert(0, "g:/Programs/zynq-sdr-course/blocks/block_11_integrated_sdr_project/python")
import lab_11_30_two_board_cfo_validation as L
import lab_11_32_two_board_fabric_coarse_cfo as B
from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat
from lab_11_27_runtime_qpsk_digital_loopback import qpsk_ber_once, QPSK_PAYLOAD_POSITION_BITS

BASE = 0x79040000
RF_MODE = 0x10 | 0x20 | 0x200 | 0x400 | 0x1000
POS = QPSK_PAYLOAD_POSITION_BITS
GARDNER = B.TIMING_RECOVERY_BIT
CARRIERS = [910e6, 915e6, 920e6]
ATTEMPTS = 100


def main() -> int:
    iq = B.make_cyclic_frame(29)
    n_samples = len(iq) // 2
    ra = L.runner_for("192.168.40.1", "root", "analog", 22, 25.0)
    rb = L.runner_for("192.168.20.1", "root", "analog", 22, 40.0)

    def sh(r, c):
        return L.sh(r, c)

    try:
        L.quiet_board(ra)
        L.quiet_board(rb)
        sh(rb, f"echo {int(L.SAMPLE_RATE)} > {B.PHY}/in_voltage_sampling_frequency 2>/dev/null")
        sh(rb, f"echo manual > {B.PHY}/in_voltage0_gain_control_mode 2>/dev/null")
        sh(rb, f"echo 50 > {B.PHY}/in_voltage0_hardwaregain 2>/dev/null")

        L.reset_tx_dma(ra)
        upload_bytes_via_ssh_cat(ra, payload=iq.tobytes(), remote_path="/tmp/csweep.bin")
        sh(ra, f"echo {int(L.SAMPLE_RATE)} > {B.PHY}/out_voltage_sampling_frequency 2>/dev/null")
        sh(ra, f"echo -30.00 > {B.PHY}/out_voltage0_hardwaregain")
        sh(ra, f"echo 0 > {B.PHY}/out_altvoltage1_TX_LO_powerdown 2>/dev/null")
        L.start_detached(ra, f"nohup iio_writedev -c -b {n_samples} -s {n_samples} "
                             "cf-ad9361-dds-core-lpc voltage0 voltage1 < /tmp/csweep.bin "
                             "> /tmp/csweep.log 2>&1 &")
        time.sleep(3.0)
        dac = sh(ra, f"devmem {L.DAC_CHAN_CNTRL_7_CH0}").strip()
        if dac not in ("0x00000002", "0x2"):
            raise RuntimeError(f"transmitter not on DMA: {dac}")
        print(f"board A streaming (DAC={dac})\n")

        for carrier in CARRIERS:
            sh(ra, f"echo {int(carrier)} > {B.PHY}/out_altvoltage1_TX_LO_frequency")
            sh(rb, f"echo {int(carrier)} > {B.PHY}/out_altvoltage0_RX_LO_frequency")
            time.sleep(1.0)
            singles = collections.Counter()
            locked = dirty = 0
            for i in range(ATTEMPTS):
                row = qpsk_ber_once(rb, BASE, 140, i % 8,
                                    mode_bits=RF_MODE | POS | GARDNER, preamble_bits=24)
                if row.get("received_symbols") != 140:
                    continue
                locked += 1
                pe = row.get("payload_errors") or 0
                if pe:
                    dirty += 1
                pos = row.get("payload_error_position")
                if pe == 1 and isinstance(pos, dict) and pos.get("first_error_index") is not None:
                    singles[pos["first_error_index"]] += 1
            rssi = sh(rb, f"cat {B.PHY}/in_voltage0_rssi 2>/dev/null").strip()
            top = ", ".join(f"{k}:{v}" for k, v in sorted(singles.items(), key=lambda kv: -kv[1])[:6])
            share = (100 * singles.get(189, 0) / sum(singles.values())) if singles else float("nan")
            print(f"{carrier/1e6:7.1f} MHz  RSSI={rssi:>10}  locked={locked}/{ATTEMPTS} dirty={dirty} "
                  f"single-bit={sum(singles.values())}")
            print(f"              indices -> {top or '(none)'}   bit189 share={share:.0f}%")
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
