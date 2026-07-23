#!/usr/bin/env python3
"""Read the RF-path capture tap and measure symbol 106's Q decision directly.

The bridge records core_rx into a 4096-sample BRAM during every burst (reset on start_edge). Readout
is gp_ctrl[7]=1: gp_start_offset carries the address, gp_capture_debug returns {rx_i, rx_q}. So we
can see exactly what the AD9361 delivered for a frame whose on-chip telemetry says bit 189 failed.

Grabs two captures -- one frame with payload_errors==1 at index 189, one clean frame -- then, on the
host: matched filter, frame alignment against the known symbols, data-aided removal of carrier phase
AND CFO (a 140-symbol frame at ~300 Hz accumulates ~30 degrees, so a constant-phase fit would smear
the very margin we are measuring), and finally symbol 106's Q against every other symbol's margin.
"""
import sys
import time

import numpy as np

sys.path.insert(0, "g:/Programs/zynq-sdr-course/blocks/block_11_integrated_sdr_project/python")
import lab_11_30_two_board_cfo_validation as L
import lab_11_32_two_board_fabric_coarse_cfo as B
from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat
from lab_11_27_runtime_qpsk_digital_loopback import qpsk_ber_once, QPSK_PAYLOAD_POSITION_BITS

BASE = 0x79040000
A_OFF = f"0x{BASE + 0x4C4:X}"     # gp_start_offset doubles as the BRAM read address
A_CAP = f"0x{BASE + 0x5C8:X}"     # gp_capture_debug returns the sample when gp_ctrl[7]=1
A_CTRL = f"0x{BASE + 0x404:X}"
RF_MODE = 0x10 | 0x20 | 0x200 | 0x400 | 0x1000
POS = QPSK_PAYLOAD_POSITION_BITS
CAP_READ_BIT = 0x80               # gp_ctrl[7]
N_READ = 4096                     # the WHOLE BRAM: the frame lands at a varying offset,
                                  # and a short window simply misses it on most bursts
TARGET_BIT = 189
SYM = 106
SAVE_DIR = "."                    # captures are written here as cap_<kind>.npy


def read_capture(run, n=N_READ):
    """Batch the whole BRAM readout into one remote shell loop (per-sample SSH would take minutes)."""
    cmd = (f"for a in $(seq 0 {n - 1}); do /sbin/devmem {A_OFF} 32 $a; "
           f"/sbin/devmem {A_CAP} 32; done")
    rc, out, err = run(cmd)
    words = [w for w in out.split() if w.startswith("0x")]
    # each iteration prints nothing for the write and one word for the read
    vals = [int(w, 16) for w in words]
    iq = []
    for v in vals:
        i = (v >> 16) & 0xFFFF
        q = v & 0xFFFF
        iq.append(complex(i - 65536 if i >= 32768 else i, q - 65536 if q >= 32768 else q))
    return np.array(iq)


def analyse(rx, tag):
    taps = L.load_rrc_taps()
    tx_sym = B.frame_symbols()                       # the 140 known symbols
    mf = np.convolve(rx - rx.mean(), taps, mode="full")

    # brute-force frame alignment: try every start sample, decimate by SPS, keep the best |corr|
    best = None
    n = np.arange(len(tx_sym))
    for start in range(0, max(1, len(mf) - len(tx_sym) * L.SPS)):
        seg = mf[start:start + len(tx_sym) * L.SPS:L.SPS]
        if len(seg) < len(tx_sym):
            break
        c = abs(np.vdot(tx_sym, seg)) / (np.linalg.norm(seg) or 1)
        if best is None or c > best[0]:
            best = (c, start, seg)
    corr, start, seg = best
    # data-aided: unwrap arg(rx * conj(tx)) and fit a line -> constant phase AND CFO in one step.
    # (Estimating CFO per candidate BEFORE correlating was tried and is WORSE: the 4th-power
    # estimate is noisy over 140 symbols and destroys the correlation at the true start.)
    ph = np.unwrap(np.angle(seg * np.conj(tx_sym)))
    slope, intercept = np.polyfit(n, ph, 1)
    aligned = seg * np.exp(-1j * (slope * n + intercept))
    aligned = aligned / (np.mean(np.abs(aligned)) or 1)

    ideal = tx_sym / np.mean(np.abs(tx_sym))
    # margin = how far the decision variable sits from zero, in units of its own axis amplitude
    q_margin = aligned.imag * np.sign(ideal.imag)
    i_margin = aligned.real * np.sign(ideal.real)
    errs_q = int(np.sum(q_margin < 0))
    errs_i = int(np.sum(i_margin < 0))

    print(f"\n--- {tag} --- align start={start} |corr|={corr:.3f} "
          f"CFO={slope/(2*np.pi)*L.SYMBOL_RATE:+.1f} Hz")
    print(f"    decision errors in this capture: I={errs_i} Q={errs_q}")
    print(f"    symbol {SYM} Q margin = {q_margin[SYM]:+.3f}   (negative = wrong decision)")
    order = np.argsort(q_margin)
    print("    five smallest Q margins: " +
          ", ".join(f"sym{int(k)}={q_margin[k]:+.3f}" for k in order[:5]))
    print(f"    symbol {SYM} rank among Q margins: {int(np.where(order == SYM)[0][0]) + 1} of {len(order)}"
          f"   (median margin {np.median(q_margin):+.3f})")
    return q_margin


def main() -> int:
    iq = B.make_cyclic_frame(29)
    n_samples = len(iq) // 2
    run_a = L.runner_for("192.168.40.1", "root", "analog", 22, 25.0)
    run_b = L.runner_for("192.168.20.1", "root", "analog", 22, 60.0)

    def sh(r, c):
        return L.sh(r, c)

    try:
        L.quiet_board(run_b)
        sh(run_b, f"echo 915000000 > {B.PHY}/out_altvoltage0_RX_LO_frequency")
        sh(run_b, f"echo {int(L.SAMPLE_RATE)} > {B.PHY}/in_voltage_sampling_frequency 2>/dev/null")
        sh(run_b, f"echo manual > {B.PHY}/in_voltage0_gain_control_mode 2>/dev/null")
        sh(run_b, f"echo 50 > {B.PHY}/in_voltage0_hardwaregain 2>/dev/null")

        L.quiet_board(run_a)
        L.reset_tx_dma(run_a)
        upload_bytes_via_ssh_cat(run_a, payload=iq.tobytes(), remote_path="/tmp/cap106.bin")
        sh(run_a, f"echo {int(L.SAMPLE_RATE)} > {B.PHY}/out_voltage_sampling_frequency 2>/dev/null")
        sh(run_a, f"echo 915000000 > {B.PHY}/out_altvoltage1_TX_LO_frequency")
        sh(run_a, "echo -30.00 > %s/out_voltage0_hardwaregain" % B.PHY)
        sh(run_a, f"echo 0 > {B.PHY}/out_altvoltage1_TX_LO_powerdown 2>/dev/null")
        L.start_detached(run_a, f"nohup iio_writedev -c -b {n_samples} -s {n_samples} "
                                "cf-ad9361-dds-core-lpc voltage0 voltage1 < /tmp/cap106.bin "
                                "> /tmp/cap106.log 2>&1 &")
        time.sleep(3.0)
        dac = sh(run_a, f"devmem {L.DAC_CHAN_CNTRL_7_CH0}").strip()
        print(f"board A streaming, DAC={dac}")

        wanted = {"fail": None, "clean": None}
        for attempt in range(240):
            off = attempt % 8
            row = qpsk_ber_once(run_b, BASE, 140, off, mode_bits=RF_MODE | POS, preamble_bits=24)
            if row.get("received_symbols") != 140:
                continue
            pe = row.get("payload_errors") or 0
            pos = row.get("payload_error_position")
            kind = None
            if pe == 1 and isinstance(pos, dict) and pos.get("first_error_index") == TARGET_BIT:
                kind = "fail"
            elif pe == 0:
                kind = "clean"
            if kind and wanted[kind] is None:
                # read the BRAM back BEFORE any further burst resets it
                sh(run_b, f"/sbin/devmem {A_CTRL} 32 0x{(RF_MODE | POS | CAP_READ_BIT):X}")
                cap = read_capture(run_b)
                sh(run_b, f"/sbin/devmem {A_CTRL} 32 0x{(RF_MODE | POS):X}")
                wanted[kind] = cap
                np.save(SAVE_DIR + f"/cap_{kind}.npy", cap)
                print(f"captured {kind}: offset={off} payload_errors={pe} pos={pos} "
                      f"samples={len(cap)} rms={np.sqrt(np.mean(abs(cap)**2)):.1f} -> cap_{kind}.npy")
            if all(v is not None for v in wanted.values()):
                break

        for kind, cap in wanted.items():
            if cap is None:
                print(f"\n--- {kind}: not observed in 240 attempts ---")
            else:
                analyse(cap, kind)
    finally:
        try:
            sh(run_a, "pkill -9 -f iio_writedev 2>/dev/null")
            L.quiet_board(run_a)
            L.quiet_board(run_b)
            print("\nboth boards quiet (-89.75 dB)")
        except Exception as exc:
            print("cleanup warning:", exc)
        run_a.client.close()
        run_b.client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
