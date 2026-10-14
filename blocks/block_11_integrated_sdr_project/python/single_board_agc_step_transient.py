#!/usr/bin/env python3
"""Issue #58: AD9361 receive gain transients on ONE board, TX and RX sharing the LO reference.

    board B TX1 -> attenuators -> splitter -> board B RX1   (conducted)

two_board_agc_step_transient.py measured the same thing with board A transmitting. There the
two boards' oscillators wander against each other by 5-14 degrees RMS over the 15 ms that
slow_attack needs to settle, so its phase step could not be resolved. Here board B transmits a
tone from its own DAC DDS and receives it itself: both LOs come from one reference, so that wander
is gone and what remains in the residual phase is the receiver (and the TX gain step itself).

Board B has no DAC driver, so the DDS is set up by registers (axi_ad9361 DAC core at 0x79024000:
DDS scale, phase increment and initial phase per channel, source select). Each run records a
continuous capture with `iio_readdev` while board B steps its own TX gain; the analysis is the one
of the two-board script (envelope settling, phase step with the drift fitted on both stable
regions, gap check). A "nostep" run records the same capture with no step: its phase step is the
floor of the method.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

import lab_11_30_two_board_cfo_validation as L
from two_board_agc_step_transient import CAPTURE, FS, analyse, fetch

PHY = L.PHY
DAC = 0x79024000
TONE_HZ = 300e3


def dds_tone(rb, tone_hz: float = TONE_HZ, scale: int = 0x1000) -> None:
    """TX1 I/Q from DDS tone 1 (quadrature by a 90-degree initial phase on Q); TX2 zero."""
    incr = int(round(tone_hz * 65536 / FS)) & 0xFFFF
    cmds = []
    for ch, init in ((0, 0x0000), (1, 0x4000)):
        base = DAC + 0x400 + 0x40 * ch
        cmds += [f"devmem 0x{base:X} 32 {scale}", f"devmem 0x{base + 0x04:X} 32 {(init << 16) | incr}",
                 f"devmem 0x{base + 0x08:X} 32 0", f"devmem 0x{base + 0x18:X} 32 0"]
    cmds += [f"devmem 0x{DAC + 0x418 + 0x40 * ch:X} 32 3" for ch in (2, 3)]
    cmds.append(f"devmem 0x{DAC + 0x44:X} 32 1")
    L.sh(rb, "; ".join(cmds))


def robust_phase(z: np.ndarray, k: int) -> dict:
    """Phase step without unwrapping.

    The unwrapped per-sample residual phase of analyse() slips whole turns where the tone is weak
    (after a drop, before the gain control has raised the gain), which gave meaningless steps of
    thousands of degrees. Here the tone frequency comes from the FFT peak of the whole capture
    (about 2 Hz resolution), the derotated tone is averaged over 1024-sample blocks (about 30 dB
    more SNR per point), and the block phases, which now unwrap safely, are fitted on the two
    stable regions with one common slope and a step at the transient. The excursion is the
    largest deviation of 256-sample block phases from that fit during the transient.
    """
    n = np.arange(z.size)
    spec = np.abs(np.fft.fft(z))
    f0 = float(np.fft.fftfreq(z.size, 1 / FS)[int(np.argmax(spec))])
    y = z * np.exp(-2j * np.pi * f0 / FS * n)

    def block_phase(lo: int, hi: int, size: int) -> tuple[np.ndarray, np.ndarray]:
        m = y[lo:lo + (hi - lo) // size * size].reshape(-1, size).mean(axis=1)
        return lo + size * (np.arange(m.size) + 0.5), m

    tb, mb = block_phase(max(k - 60000, 0), k - 20000, 1024)
    ta, ma = block_phase(k + 100000, min(k + 200000, z.size), 1024)
    ref = mb.mean()
    pb = np.unwrap(np.angle(mb / ref))
    pa = np.unwrap(np.angle(ma / ref))
    pa -= 2 * np.pi * np.round((pa[0] - pb[-1]) / (2 * np.pi))     # keep the two regions within half a turn
    t = np.r_[tb, ta]
    a = np.c_[np.ones(t.size), t, np.r_[np.zeros(tb.size), np.ones(ta.size)]]
    coef = np.linalg.lstsq(a, np.r_[pb, pa], rcond=None)[0]
    tt, mt = block_phase(k - 2000, k + 40000, 256)
    fit = coef[0] + coef[1] * tt
    dev = np.angle(mt / ref * np.exp(-1j * fit))
    return {"tone_offset_hz": round(f0 + coef[1] * FS / (2 * np.pi), 2),
            "phase_step_deg_robust": round(float(np.degrees(coef[2])), 2),
            "phase_excursion_deg_robust": round(float(np.degrees(np.max(np.abs(dev)))), 2)}


def dds_off(rb) -> None:
    L.sh(rb, "; ".join(f"devmem 0x{DAC + 0x400 + 0x40 * ch:X} 32 0" for ch in (0, 1)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--carrier", type=float, default=915e6)
    ap.add_argument("--low", type=float, default=-30.0, help="TX gain before/after the step, dB")
    ap.add_argument("--high", type=float, default=-10.0)
    ap.add_argument("--manual-rx-gain", type=int, default=50)
    ap.add_argument("--modes", nargs="+", default=["nostep", "manual", "slow_attack", "fast_attack"])
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--bench", required=True)
    ap.add_argument("--json-out", type=Path, required=True)
    ap.add_argument("--keep-captures", type=Path, default=None)
    args = ap.parse_args()

    rb = L.runner_for("192.168.20.1", "root", "analog", 22, 120.0)
    sh = L.sh
    res = {"issue": 58, "bench": args.bench, "carrier_hz": args.carrier, "sample_rate": FS, "tone_hz": TONE_HZ,
           "tx_low_db": args.low, "tx_high_db": args.high, "capture_samples": CAPTURE, "runs": []}
    try:
        L.quiet_board(rb)
        sh(rb, f"echo {int(FS)} > {PHY}/in_voltage_sampling_frequency 2>/dev/null")
        sh(rb, f"echo {int(args.carrier)} > {PHY}/out_altvoltage0_RX_LO_frequency; "
               f"echo {int(args.carrier)} > {PHY}/out_altvoltage1_TX_LO_frequency; "
               f"echo 0 > {PHY}/out_altvoltage1_TX_LO_powerdown")
        dds_tone(rb)
        for mode in args.modes:
            for direction in (("up", "down") if mode != "nostep" else ("none",)):
                for rep in range(args.repeats):
                    start, end = (args.low, args.high) if direction != "down" else (args.high, args.low)
                    if direction == "none":
                        end = start
                    sh(rb, f"echo {start:.2f} > {PHY}/out_voltage0_hardwaregain")
                    rx_mode = "manual" if mode == "nostep" else mode
                    sh(rb, f"echo {rx_mode} > {PHY}/in_voltage0_gain_control_mode")
                    if rx_mode == "manual":
                        sh(rb, f"echo {args.manual_rx_gain} > {PHY}/in_voltage0_hardwaregain")
                    time.sleep(1.5)
                    g0 = sh(rb, f"cat {PHY}/in_voltage0_hardwaregain").strip()
                    sh(rb, "rm -f /tmp/agc.done")
                    rb.client.exec_command(
                        # One buffer for the whole capture: with several, iio_readdev leaves gaps between them
                        # (measured: 0.7-1 rad phase jumps at the 65536-sample boundaries on board B).
                        f"rm -f /tmp/agc.bin; iio_readdev -b {CAPTURE} -s {CAPTURE} cf-ad9361-lpc voltage0 voltage1 "
                        "> /tmp/agc.bin 2>/tmp/agc.err; echo done > /tmp/agc.done")
                    time.sleep(0.20)
                    sh(rb, f"echo {end:.2f} > {PHY}/out_voltage0_hardwaregain")
                    for _ in range(60):
                        if sh(rb, "cat /tmp/agc.done 2>/dev/null").strip() == "done":
                            break
                        time.sleep(0.5)
                    g1 = sh(rb, f"cat {PHY}/in_voltage0_hardwaregain").strip()
                    z = fetch(rb.client, "/tmp/agc.bin")
                    row = {"mode": mode, "direction": direction, "repeat": rep, "tx_from_db": start, "tx_to_db": end,
                           "rx_gain_before": g0, "rx_gain_after": g1, "samples": int(z.size)}
                    if args.keep_captures:
                        args.keep_captures.mkdir(parents=True, exist_ok=True)
                        np.save(args.keep_captures / f"sb_{mode}_{direction}_{rep}.npy", z.astype(np.complex64))
                    if z.size < CAPTURE // 2:
                        row["error"] = "short capture"
                    else:
                        row.update(analyse(z, int(0.2 * FS)))
                        row.update(robust_phase(z, row["step_sample"]))
                    res["runs"].append(row)
                    print(json.dumps(row), flush=True)
    finally:
        try:
            dds_off(rb)
            sh(rb, f"echo manual > {PHY}/in_voltage0_gain_control_mode; echo 71 > {PHY}/in_voltage0_hardwaregain")
            L.quiet_board(rb)
            print("board B quiet (-89.75 dB), DDS off, manual 71 dB")
        except Exception as exc:  # noqa: BLE001
            print("cleanup warning:", exc)
        rb.client.close()
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
        print("wrote", args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
