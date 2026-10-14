#!/usr/bin/env python3
"""Issue #58: receive gain control against a level step placed at a known point of the frame.

The earlier dynamic runs (two_board_agc_ber.py) toggle board A's TX gain from a shell loop, so a
transition lands at a random point of a random frame. Here the step is written into the transmitted
waveform itself: board A replays a cyclic buffer of Lab 11.45 frames whose digital amplitude
switches by `--step-db` at symbol `--positions` of a frame. The step is therefore locked to the frame
to the sample, and the sweep over positions shows where in the frame a step hurts.

* `--shapes alternate --frames-per-level 1`: the level alternates every frame, so every received
  frame contains one step (up or down) at the given position.
* `--shapes saw_up saw_down triangle --frames-per-level K`: one abrupt step per K frames in one
  direction only, the level returning by a slow ramp; the triangle has the ramps and no step. One
  received frame in K contains the step, so the excess over the triangle is the step's effect.

Reference points: the same buffer at a constant high or low level (no step). Board B decodes in the
fabric with the Lab 11.45 differential mode. Both boards are quieted on exit.
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

FRAME_SAMPLES = B.LONG_FRAME_SYMBOLS * L.SPS


def stepped_buffer(n_frames: int, frames_per_level: int, position: int | None, step_db: float,
                   shape: str = "alternate") -> np.ndarray:
    """int16 IQ of n_frames long-preamble frames under a level envelope.

    position is the frame symbol where the abrupt step lands. The envelope is applied after the
    causal RRC filter of make_long_preamble_frame, whose output lags the symbols by half its length
    (32 samples, 4 symbols), so the envelope is delayed by the same amount. Shapes, over a block of
    frames_per_level frames (alternate: two blocks per period):
      high / low      constant level, no step (references);
      alternate       the level switches by step_db at `position`, up and down in turn;
      saw_up          abrupt step UP at `position`, then a linear-in-dB ramp down over the block;
      saw_down        abrupt step DOWN at `position`, then a ramp up over the block;
      triangle        ramp down and up over the block, no abrupt step (reference for the saws)."""
    iq = B.make_long_preamble_frame(n_frames, differential=True).astype(np.float64)
    n = len(iq) // 2
    delay = (len(L.load_rrc_taps()) - 1) // 2
    block = frames_per_level * FRAME_SAMPLES
    t = np.arange(n) - delay - (position or 0) * L.SPS
    x = (t % block) / block
    if shape == "high":
        level_db = np.zeros(n)
    elif shape == "low":
        level_db = np.full(n, -step_db)
    elif shape == "alternate":
        level_db = np.where((t // block) % 2 == 0, 0.0, -step_db)
    elif shape == "saw_up":
        level_db = -step_db * x
    elif shape == "saw_down":
        level_db = -step_db * (1.0 - x)
    elif shape == "triangle":
        level_db = -step_db * (1.0 - np.abs(2.0 * x - 1.0))
    else:
        raise ValueError(shape)
    env = 10 ** (level_db / 20)
    iq[0::2] *= env
    iq[1::2] *= env
    return np.round(iq).astype(np.int16)


def start_tx(ra, iq: np.ndarray, carrier: float, tx_gain: float) -> None:
    sh = L.sh
    sh(ra, "for p in $(ps | grep '[i]io_writedev' | awk '{print $1}'); do kill -9 $p; done")
    L.reset_tx_dma(ra)
    upload_bytes_via_ssh_cat(ra, payload=iq.tobytes(), remote_path="/tmp/lp.bin")
    sh(ra, f"echo {int(L.SAMPLE_RATE)} > {PHY}/out_voltage_sampling_frequency 2>/dev/null")
    sh(ra, f"echo {int(carrier)} > {PHY}/out_altvoltage1_TX_LO_frequency")
    sh(ra, f"echo {tx_gain:.2f} > {PHY}/out_voltage0_hardwaregain")
    sh(ra, f"echo 0 > {PHY}/out_altvoltage1_TX_LO_powerdown 2>/dev/null")
    n = len(iq) // 2
    L.start_detached(ra, f"nohup iio_writedev -c -b {n} -s {n} cf-ad9361-dds-core-lpc "
                         "voltage0 voltage1 < /tmp/lp.bin > /tmp/lp.log 2>&1 &")
    time.sleep(3.0)
    if sh(ra, f"devmem {L.DAC_CHAN_CNTRL_7_CH0}").strip() not in ("0x00000002", "0x2"):
        raise RuntimeError("transmitter not on DMA")
    if sh(ra, "ps | grep -c '[i]io_writedev'").strip() != "1":
        raise RuntimeError("expected exactly one iio_writedev on board A")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--carrier", type=float, default=915e6)
    ap.add_argument("--tx-gain", type=float, default=-10.0)
    ap.add_argument("--step-db", type=float, default=20.0)
    ap.add_argument("--modes", nargs="+", default=["manual", "slow_attack", "fast_attack"])
    ap.add_argument("--manual-rx-gain", type=int, default=50)
    ap.add_argument("--positions", type=int, nargs="+", default=[2, 14, 26, 60, 96, 136, 148],
                    help="frame symbol where the step lands (preamble 0-23, payload 24-151)")
    ap.add_argument("--shapes", nargs="+", default=["alternate"],
                    choices=["alternate", "saw_up", "saw_down", "triangle"])
    ap.add_argument("--frames-per-level", type=int, default=1)
    ap.add_argument("--n-frames", type=int, default=30, help="frames in the cyclic buffer")
    ap.add_argument("--frames", type=int, default=100, help="frames scored per point")
    ap.add_argument("--no-reference", action="store_true", help="skip the constant-level points")
    ap.add_argument("--clear-mode-bits", type=lambda s: int(s, 0), default=0,
                    help="receiver mode bits to clear, e.g. 0x200 = DC blocker off")
    ap.add_argument("--bench", required=True)
    ap.add_argument("--json-out", type=Path, required=True)
    args = ap.parse_args()
    if args.n_frames % (2 * args.frames_per_level):
        raise SystemExit("--n-frames must be a multiple of 2 * --frames-per-level (seamless cycle)")

    ra = L.runner_for("192.168.40.1", "root", "analog", 22, 25.0)
    rb = L.runner_for("192.168.20.1", "root", "analog", 22, 40.0)
    sh = L.sh
    res = {"issue": 58, "bench": args.bench, "carrier_hz": args.carrier, "mode_bits": hex(MODE & ~args.clear_mode_bits),
           "tx_gain_db": args.tx_gain, "step_db": args.step_db, "frames_per_level": args.frames_per_level,
           "n_frames": args.n_frames, "manual_rx_gain_db": args.manual_rx_gain, "points": []}
    cases = [] if args.no_reference else [("high", None), ("low", None)]
    cases += [(s, None if s == "triangle" else p) for s in args.shapes
              for p in (args.positions if s != "triangle" else [None])]
    try:
        L.quiet_board(rb)
        res["board_b_image_md5"] = sh(rb, "mkdir -p /tmp/sd; mount -t vfat /dev/mmcblk0p1 /tmp/sd 2>/dev/null; "
                                          "md5sum /tmp/sd/system_top.bit").split()[0]
        if sh(ra, "ps | grep -c '[t]oggle.sh'").strip() != "0":
            raise RuntimeError("a TX toggling loop is running on board A")
        sh(rb, f"echo {int(args.carrier)} > {PHY}/out_altvoltage0_RX_LO_frequency")
        sh(rb, f"echo {int(L.SAMPLE_RATE)} > {PHY}/in_voltage_sampling_frequency 2>/dev/null")
        L.quiet_board(ra)
        for level, pos in cases:
            start_tx(ra, stepped_buffer(args.n_frames, args.frames_per_level, pos, args.step_db, level),
                     args.carrier, args.tx_gain)
            for mode in args.modes:
                sh(rb, f"echo {mode} > {PHY}/in_voltage0_gain_control_mode")
                if mode == "manual":
                    sh(rb, f"echo {args.manual_rx_gain} > {PHY}/in_voltage0_hardwaregain")
                time.sleep(1.0)
                gains: list[float] = []
                r = {"shape": level, "position_symbols": pos, "mode": mode, **score(rb, args.frames, gains, MODE & ~args.clear_mode_bits)}
                r["rx_gain_min"], r["rx_gain_max"] = min(gains), max(gains)
                res["points"].append(r)
                print(json.dumps(r), flush=True)
    finally:
        try:
            sh(ra, "for p in $(ps | grep '[i]io_writedev' | awk '{print $1}'); do kill -9 $p; done")
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
