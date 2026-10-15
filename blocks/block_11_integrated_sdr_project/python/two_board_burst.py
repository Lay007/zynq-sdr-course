#!/usr/bin/env python3
"""Packet mode on two boards: does the Lab 11.45 receiver catch a frame that follows silence?

    board A TX1 -> attenuators -> splitter -> board B RX1   (conducted)

Board A replays ONE long differential frame (152 symbols, 317 us) followed by --gaps frame
lengths of silence, cyclically; gap 0 is the continuous stream of the other two-board labs. Board
B arms the receiver at a random moment and decodes the next burst. Between bursts the receiver
sees only noise: the DC blocker estimate, the Costas and Gardner loops and the AGC all drift, and
must settle again within the 24-symbol preamble. Per point: locked, clean, gross, payload BER.

--listen sets gp_ctrl[18] (issue #68): the receiver then waits up to 65535 symbols for the packet
instead of the fixed frame + 256-symbol window; it needs an image built with that bit.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

import lab_11_30_two_board_cfo_validation as L
import lab_11_32_two_board_fabric_coarse_cfo as B
from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat
from two_board_agc_ber import MODE, PHY, score

LISTEN_BIT = 1 << 18


def burst_iq(gap_frames: int, ref: bool = False, lead: int = 0) -> np.ndarray:
    """int16 IQ: one RRC-shaped frame then gap_frames frame lengths of zeros, circular.

    ref=True puts one reference symbol (phase state 0, the differential encoder's starting state)
    in front of the frame. A differential receiver decodes each symbol against the one before it;
    after silence that one is noise, so without the reference the first frame symbol decodes
    wrong in about 3 cases of 4 and the frame sync, which needs 23 of the first 24 bits, misses.

    lead > 0 (implies the reference) puts that many training symbols before the reference,
    alternating between phase states 2 and 0 (180-degree flips, a transition every symbol for the
    timing loop). After silence the receiver's timing and carrier loops need some symbols to
    settle; without a lead-in that happens on the first preamble symbols, which the frame sync
    needs (issue #68).
    """
    fb = B.diff_encode_bits(B.long_frame_bits())
    frame = ((1.0 - 2.0 * fb[0::2]) + 1j * (1.0 - 2.0 * fb[1::2])) / np.sqrt(2.0)
    # A continuous stream (gap 0) needs no reference: the previous frame provides it.
    s0 = (1 + 1j) / np.sqrt(2.0)
    train = np.array([-s0 if (lead - k) % 2 else s0 for k in range(lead)], dtype=complex)
    head = np.concatenate([train, [s0]]) if (ref or lead) and gap_frames > 0 else np.zeros(0, dtype=complex)
    sym = np.concatenate([head, frame, np.zeros(len(frame) * gap_frames - len(head), dtype=complex)])
    if gap_frames == 0:
        sym = np.tile(frame, 28)
    taps = L.load_rrc_taps()
    up = np.zeros(len(sym) * L.SPS, dtype=complex)
    up[:: L.SPS] = sym
    ker = np.zeros(len(up), dtype=complex)
    ker[: len(taps)] = taps
    wave = np.fft.ifft(np.fft.fft(up) * np.fft.fft(ker))
    wave = wave * (0.70 * 32767 / np.max(np.abs(wave)))
    iq = np.zeros(len(wave) * 2, dtype=np.int16)
    iq[0::2] = np.round(wave.real).astype(np.int16)
    iq[1::2] = np.round(wave.imag).astype(np.int16)
    return iq


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--carrier", type=float, default=915e6)
    ap.add_argument("--gaps", type=int, nargs="+", default=[0, 1, 4, 19, 99])
    ap.add_argument("--tx-levels", type=float, nargs="+", default=[-30.0, -10.0, -50.0])
    ap.add_argument("--rx", nargs="+", default=["manual:71", "slow_attack"])
    ap.add_argument("--frames", type=int, default=100)
    ap.add_argument("--listen", action="store_true", help="receiver listen mode, gp_ctrl[18] (#68)")
    ap.add_argument("--ref", action="store_true", help="reference symbol before each burst")
    ap.add_argument("--lead", type=int, default=0, help="training symbols before the reference (implies --ref)")
    ap.add_argument("--json-out", type=Path, required=True)
    args = ap.parse_args()

    ra = L.runner_for("192.168.40.1", "root", "analog", 22, 30.0)
    rb = L.runner_for("192.168.20.1", "root", "analog", 22, 40.0)
    mode_bits = MODE | (LISTEN_BIT if args.listen else 0)
    res = {"carrier_hz": args.carrier, "mode_bits": hex(mode_bits), "listen": args.listen, "ref_symbol": args.ref or args.lead > 0, "lead_symbols": args.lead, "frames": args.frames,
           "frame_us": B.LONG_FRAME_SYMBOLS * L.SPS / L.SAMPLE_RATE * 1e6, "points": []}
    try:
        L.quiet_board(ra)
        L.reset_tx_dma(ra)
        L.sh(ra, f"echo {int(L.SAMPLE_RATE)} > {PHY}/out_voltage_sampling_frequency; "
                 f"echo {int(args.carrier)} > {PHY}/out_altvoltage1_TX_LO_frequency")
        L.sh(rb, f"echo {int(L.SAMPLE_RATE)} > {PHY}/in_voltage_sampling_frequency; "
                 f"echo {int(args.carrier)} > {PHY}/out_altvoltage0_RX_LO_frequency")
        for gap in args.gaps:
            iq = burst_iq(gap, ref=args.ref, lead=args.lead)
            n = len(iq) // 2
            L.sh(ra, "for p in $(ps | grep '[i]io_writedev' | awk '{print $1}'); do kill -9 $p; done")
            L.reset_tx_dma(ra)
            upload_bytes_via_ssh_cat(ra, payload=iq.tobytes(), remote_path="/tmp/burst.bin")
            L.sh(ra, f"echo {args.tx_levels[0]:.2f} > {PHY}/out_voltage0_hardwaregain; "
                     f"echo 0 > {PHY}/out_altvoltage1_TX_LO_powerdown")
            L.start_detached(ra, f"nohup iio_writedev -c -b {n} -s {n} cf-ad9361-dds-core-lpc voltage0 voltage1 "
                                 "< /tmp/burst.bin > /tmp/burst.log 2>&1 &")
            time.sleep(3.0)
            for rx in args.rx:
                mode, _, gain = rx.partition(":")
                L.sh(rb, f"echo {mode} > {PHY}/in_voltage0_gain_control_mode")
                if gain:
                    L.sh(rb, f"echo {gain} > {PHY}/in_voltage0_hardwaregain")
                for tx in args.tx_levels:
                    L.sh(ra, f"echo {tx:.2f} > {PHY}/out_voltage0_hardwaregain")
                    time.sleep(0.5)
                    gains: list[float] = []
                    r = score(rb, args.frames, gains, mode_bits=mode_bits, poll=3000 if args.listen else 300)
                    row = {"gap_frames": gap, "rx": rx, "tx_db": tx, "rx_gain_min": min(gains), "rx_gain_max": max(gains), **r}
                    res["points"].append(row)
                    ber = r["payload_bit_errors"] / r["payload_bits"] if r["payload_bits"] else None
                    print(f"gap {gap:3d} {rx:12s} TX {tx:+6.1f}: locked {r['locked']:3d} clean {r['clean']:3d} "
                          f"gross {r['gross']:3d} BER {ber if ber is None else f'{ber:.1e}'} gain {min(gains)}-{max(gains)}",
                          flush=True)
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
