#!/usr/bin/env python3
"""Issue #29: how large is each 1 dB step of the AD9361 receive gain, measured on a real input.

    board A TX1 -> attenuators -> splitter -> board B RX1   (conducted)

Board A transmits a 300 kHz tone (cyclic iio_writedev buffer). Board B sweeps its manual RX gain
from 0 to the maximum in 1 dB steps and records a short gap-free capture at each step (one
iio_readdev buffer). The tone amplitude is the FFT bin of the tone, so noise and the DC offset do
not enter it; the noise floor is the median of the other bins. A point is used only if the tone is
at least --min-snr dB above the floor and the ADC peak stays below --max-peak of full scale.

One TX level cannot cover 73 dB of gain between the noise floor and the ADC rail, so the sweep runs
at several TX levels, and the segments are joined by their mean difference over the gains where
both are valid. The result is the received tone level versus the gain setting, its deviation from a
straight 1 dB per step line, and the size of each individual step.

    python two_board_rx_gain_steps.py --carriers 433e6 915e6 2400e6 --json-out out.json
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

import lab_11_30_two_board_cfo_validation as L
from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat
from two_board_agc_step_transient import TONE_HZ, TONE_LEN, fetch, tone_buffer

PHY = L.PHY
FS = L.SAMPLE_RATE
N = 16384


def tone_level(z: np.ndarray) -> tuple[float, float, float]:
    """(tone dBFS, noise floor dBFS per bin, peak fraction of full scale) of one capture."""
    zz = z - z.mean()
    spec = np.abs(np.fft.fft(zz * np.hanning(zz.size))) / (zz.size * 0.5)
    f = np.fft.fftfreq(zz.size, 1 / FS)
    # The tone sits at +TONE_HZ or -TONE_HZ depending on the I/Q convention: take the stronger one.
    cands = [int(np.argmin(np.abs(f - TONE_HZ))), int(np.argmin(np.abs(f + TONE_HZ)))]
    k = max((i for c in cands for i in range(max(c - 3, 0), min(c + 4, spec.size))), key=lambda i: spec[i])
    tone = spec[max(k - 2, 0):k + 3].max()
    mask = np.ones(spec.size, bool)
    mask[max(k - 20, 0):k + 21] = False
    mask[:20] = False
    mask[-20:] = False
    floor = np.median(spec[mask])
    peak = max(np.abs(z.real).max(), np.abs(z.imag).max()) / 2048.0
    return 20 * np.log10(tone / 2048.0), 20 * np.log10(floor / 2048.0), float(peak)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--carriers", type=float, nargs="+", default=[915e6])
    ap.add_argument("--tx-levels", type=float, nargs="+", default=[-5.0, -35.0, -65.0])
    ap.add_argument("--max-gain", type=int, default=73)
    ap.add_argument("--min-snr", type=float, default=30.0)
    ap.add_argument("--max-peak", type=float, default=0.8)
    ap.add_argument("--json-out", type=Path, required=True)
    args = ap.parse_args()

    ra = L.runner_for("192.168.40.1", "root", "analog", 22, 30.0)
    rb = L.runner_for("192.168.20.1", "root", "analog", 22, 60.0)
    res = {"issue": 29, "sample_rate": FS, "tone_hz": TONE_HZ, "capture_samples": N, "tx_levels_db": args.tx_levels,
           "min_snr_db": args.min_snr, "max_peak_fs": args.max_peak, "carriers": []}
    try:
        L.quiet_board(ra)
        L.reset_tx_dma(ra)
        upload_bytes_via_ssh_cat(ra, payload=tone_buffer().tobytes(), remote_path="/tmp/tone.bin")
        L.sh(ra, f"echo {int(FS)} > {PHY}/out_voltage_sampling_frequency 2>/dev/null")
        L.sh(rb, f"echo {int(FS)} > {PHY}/in_voltage_sampling_frequency 2>/dev/null; "
                 f"echo manual > {PHY}/in_voltage0_gain_control_mode")
        L.start_detached(ra, f"nohup iio_writedev -c -b {TONE_LEN} -s {TONE_LEN} cf-ad9361-dds-core-lpc "
                             "voltage0 voltage1 < /tmp/tone.bin > /tmp/tone.log 2>&1 &")
        time.sleep(3.0)
        for carrier in args.carriers:
            L.sh(ra, f"echo {int(carrier)} > {PHY}/out_altvoltage1_TX_LO_frequency; echo 0 > {PHY}/out_altvoltage1_TX_LO_powerdown")
            L.sh(rb, f"echo {int(carrier)} > {PHY}/out_altvoltage0_RX_LO_frequency")
            segments = {}
            for tx in args.tx_levels:
                L.sh(ra, f"echo {tx:.2f} > {PHY}/out_voltage0_hardwaregain")
                pts = []
                for g in range(0, args.max_gain + 1):
                    L.sh(rb, f"echo {g} > {PHY}/in_voltage0_hardwaregain")
                    rb_read = L.sh(rb, f"cat {PHY}/in_voltage0_hardwaregain").split()[0]
                    L.sh(rb, f"iio_readdev -b {N} -s {N} cf-ad9361-lpc voltage0 voltage1 > /tmp/g.bin 2>/dev/null")
                    z = fetch(rb.client, "/tmp/g.bin")
                    if z.size < N // 2:
                        pts.append({"gain": g, "error": "short capture"})
                        continue
                    lvl, floor, peak = tone_level(z)
                    pts.append({"gain": g, "readback": float(rb_read), "tone_dbfs": round(lvl, 2),
                                "floor_dbfs": round(floor, 2), "peak_fs": round(peak, 3),
                                "valid": bool(lvl - floor >= args.min_snr and peak < args.max_peak)})
                segments[str(tx)] = pts
                nv = sum(p.get("valid", False) for p in pts)
                print(f"{carrier / 1e6:.0f} MHz TX {tx:+.0f} dB: {nv} valid points", flush=True)
            # Join the segments: level(g) - g per segment, shifted onto the first by the overlap mean.
            curve = {}
            ref = None
            for tx in args.tx_levels:
                seg = {p["gain"]: p["tone_dbfs"] for p in segments[str(tx)] if p.get("valid")}
                if not seg:
                    continue
                if ref is None:
                    shift = -tx
                else:
                    common = [g for g in seg if g in curve]
                    if not common:
                        continue
                    shift = float(np.mean([curve[g] - seg[g] for g in common]))
                for g, v in seg.items():
                    curve.setdefault(g, v + shift)
                ref = True
            gains = sorted(curve)
            lv = np.array([curve[g] for g in gains])
            fit = np.polyfit(gains, lv, 1) if len(gains) > 2 else [None, None]
            steps = {gains[i + 1]: round(curve[gains[i + 1]] - curve[gains[i]], 2)
                     for i in range(len(gains) - 1) if gains[i + 1] == gains[i] + 1}
            dev = {g: round(curve[g] - np.polyval(fit, g), 2) for g in gains} if len(gains) > 2 else {}
            row = {"carrier_hz": carrier, "segments": segments, "joined_level_db": {g: round(curve[g], 2) for g in gains},
                   "fit_slope_db_per_step": round(float(fit[0]), 4) if fit[0] is not None else None,
                   "deviation_from_fit_db": dev, "step_db": steps,
                   "gain_range_covered": [gains[0], gains[-1]] if gains else None}
            res["carriers"].append(row)
            if steps:
                sv = np.array(list(steps.values()))
                print(f"   joined {gains[0]}..{gains[-1]} dB: slope {fit[0]:.3f} dB/step, steps {sv.min():.2f}..{sv.max():.2f} dB, "
                      f"max deviation {max(abs(v) for v in dev.values()):.2f} dB", flush=True)
    finally:
        L.sh(ra, "for p in $(ps | grep '[i]io_writedev' | awk '{print $1}'); do kill -9 $p; done")
        L.quiet_board(ra)
        L.sh(ra, f"echo 1 > {PHY}/out_altvoltage1_TX_LO_powerdown")
        L.sh(rb, f"echo 71 > {PHY}/in_voltage0_hardwaregain")
        L.quiet_board(rb)
        ra.client.close()
        rb.client.close()
        args.json_out.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
        print("wrote", args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
