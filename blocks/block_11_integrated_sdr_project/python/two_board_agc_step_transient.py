#!/usr/bin/env python3
"""Issue #58: amplitude and phase transients of the AD9361 receive gain control, on two boards.

    board A TX1 -> attenuators -> splitter -> board B RX1   (conducted)

Board A transmits a pure tone (a cyclic buffer through its DDS/DMA core), so board B's IQ has a
known form, A(t) exp(j(w t + phi(t))). Board B records a long continuous capture with
`iio_readdev` while board A steps its TX gain by a known amount. For each receive gain mode
(manual, slow_attack, fast_attack) and step direction the script reports, from the capture:

* the amplitude step and the time the envelope needs to settle within 1 dB of its final level;
* the phase step: the residual phase (tone frequency removed) averaged before and after the
  transient, and the largest phase excursion during it;
* the receive gain readback before and after (it changes only under AGC).

The manual-gain run is the control: whatever it shows comes from the transmitter's own gain
step and the channel, not from the receiver. The difference under AGC is the receiver's gain
transition, the effect issue #58 asks about.

The capture is checked for sample gaps first: the tone's phase must advance smoothly across the
DMA buffer boundaries of the pre-step region, or a "phase step" could be a dropped buffer.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

import lab_11_30_two_board_cfo_validation as L
from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat

PHY = L.PHY
FS = L.SAMPLE_RATE                 # 3.84 MS/s
TONE_HZ = 300e3                    # 300 whole cycles in a 3840-sample buffer: a seamless loop
TONE_LEN = 3840
CAPTURE = 2_000_000                # about 0.52 s at 3.84 MS/s
BUFFER = 65536


def tone_buffer() -> np.ndarray:
    n = np.arange(TONE_LEN)
    w = 0.70 * 32767 * np.exp(2j * np.pi * TONE_HZ * n / FS)
    iq = np.zeros(2 * TONE_LEN, dtype=np.int16)
    iq[0::2] = np.round(w.real).astype(np.int16)
    iq[1::2] = np.round(w.imag).astype(np.int16)
    return iq


def fetch(client, path: str) -> np.ndarray:
    _, out, _ = client.exec_command(f"cat {path}", timeout=120)
    data = out.read()
    x = np.frombuffer(data[: len(data) // 4 * 4], dtype="<i2").astype(np.float64)
    return x[0::2] + 1j * x[1::2]


def analyse(z: np.ndarray, step_hint: int) -> dict:
    """Envelope and residual-phase transient around the gain step."""
    pre = z[: max(step_hint - 20000, 50000)]
    # Frequency from the pre-step region: least-squares slope of the unwrapped phase.
    ph = np.unwrap(np.angle(pre))
    t = np.arange(pre.size)
    slope = np.polyfit(t, ph, 1)[0]
    freq_hz = slope * FS / (2 * np.pi)
    resid = np.unwrap(np.angle(z * np.exp(-1j * slope * np.arange(z.size))))
    # Gap check on the pre-step region: residual phase jumps at buffer boundaries.
    d = np.abs(np.diff(resid[: pre.size]))
    boundary_jumps = [float(d[k - 1]) for k in range(BUFFER, pre.size, BUFFER)]
    typical = float(np.median(d))
    env_db = 20 * np.log10(np.convolve(np.abs(z), np.ones(64) / 64, mode="same") + 1e-9)
    # Locate the step: largest change of the smoothed envelope.
    smooth = np.convolve(env_db, np.ones(256) / 256, mode="same")
    k = int(np.argmax(np.abs(np.diff(smooth[1000:-1000])))) + 1000
    before = slice(max(k - 60000, 0), k - 20000)
    after = slice(k + 100000, min(k + 200000, z.size))
    a0, a1 = float(np.median(env_db[before])), float(np.median(env_db[after]))
    settle = None
    for i in range(k, min(k + 400000, z.size)):
        if np.all(np.abs(env_db[i:i + 2000] - a1) < 1.0):
            settle = (i - k) / FS
            break
    p0 = float(np.mean(resid[before]))
    p1 = float(np.mean(resid[after]))
    # Phase drift from residual CFO: remove the linear trend fitted on both stable regions.
    tb = np.r_[np.arange(before.start, before.stop), np.arange(after.start, after.stop)]
    trend = np.polyfit(tb, np.r_[resid[before], resid[after]] - np.r_[np.zeros(before.stop - before.start),
                                                                        np.full(after.stop - after.start, p1 - p0)], 1)
    detr = resid - np.polyval(trend, np.arange(z.size))
    jump = float(np.mean(detr[after]) - np.mean(detr[before]))
    window = detr[k - 2000:k + 40000] - np.mean(detr[before])
    return {
        "tone_freq_measured_hz": round(freq_hz, 1),
        "gap_check": {"typical_phase_step_rad": round(typical, 5),
                      "max_boundary_phase_step_rad": round(max(boundary_jumps), 5) if boundary_jumps else None,
                      "boundaries_checked": len(boundary_jumps)},
        "step_sample": k,
        "amplitude_before_db": round(a0, 2),
        "amplitude_after_db": round(a1, 2),
        "amplitude_step_db": round(a1 - a0, 2),
        "settle_to_1db_s": None if settle is None else round(settle, 6),
        "phase_step_deg": round(float(np.degrees(jump)), 2),
        "phase_excursion_deg": round(float(np.degrees(np.max(np.abs(window)))), 2),
        "clipped_pct": round(float(np.mean((np.abs(z.real) >= 2047) | (np.abs(z.imag) >= 2047)) * 100), 4),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--carrier", type=float, default=915e6)
    ap.add_argument("--low", type=float, default=-30.0, help="TX gain before/after the step, dB")
    ap.add_argument("--high", type=float, default=-10.0)
    ap.add_argument("--manual-rx-gain", type=int, default=50)
    ap.add_argument("--modes", nargs="+", default=["manual", "slow_attack", "fast_attack"])
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--bench", required=True)
    ap.add_argument("--json-out", type=Path, required=True)
    ap.add_argument("--keep-captures", type=Path, default=None, help="directory for the raw .npy captures")
    args = ap.parse_args()

    ra = L.runner_for("192.168.40.1", "root", "analog", 22, 25.0)
    rb = L.runner_for("192.168.20.1", "root", "analog", 22, 120.0)
    sh = L.sh
    res = {"issue": 58, "bench": args.bench, "carrier_hz": args.carrier, "sample_rate": FS, "tone_hz": TONE_HZ,
           "tx_low_db": args.low, "tx_high_db": args.high, "capture_samples": CAPTURE, "runs": []}
    try:
        L.quiet_board(rb)
        sh(rb, f"echo {int(args.carrier)} > {PHY}/out_altvoltage0_RX_LO_frequency")
        sh(rb, f"echo {int(FS)} > {PHY}/in_voltage_sampling_frequency 2>/dev/null")
        L.quiet_board(ra)
        L.reset_tx_dma(ra)
        tone = tone_buffer()
        upload_bytes_via_ssh_cat(ra, payload=tone.tobytes(), remote_path="/tmp/tone.bin")
        sh(ra, f"echo {int(FS)} > {PHY}/out_voltage_sampling_frequency 2>/dev/null")
        sh(ra, f"echo {int(args.carrier)} > {PHY}/out_altvoltage1_TX_LO_frequency")
        sh(ra, f"echo {args.low:.2f} > {PHY}/out_voltage0_hardwaregain")
        sh(ra, f"echo 0 > {PHY}/out_altvoltage1_TX_LO_powerdown 2>/dev/null")
        L.start_detached(ra, f"nohup iio_writedev -c -b {TONE_LEN} -s {TONE_LEN} cf-ad9361-dds-core-lpc "
                             "voltage0 voltage1 < /tmp/tone.bin > /tmp/tone.log 2>&1 &")
        time.sleep(3.0)
        if sh(ra, f"devmem {L.DAC_CHAN_CNTRL_7_CH0}").strip() not in ("0x00000002", "0x2"):
            raise RuntimeError("transmitter not on DMA")
        for mode in args.modes:
            for direction in ("up", "down"):
                for rep in range(args.repeats):
                    start, end = (args.low, args.high) if direction == "up" else (args.high, args.low)
                    sh(ra, f"echo {start:.2f} > {PHY}/out_voltage0_hardwaregain")
                    sh(rb, f"echo {mode} > {PHY}/in_voltage0_gain_control_mode")
                    if mode == "manual":
                        sh(rb, f"echo {args.manual_rx_gain} > {PHY}/in_voltage0_hardwaregain")
                    time.sleep(1.5)
                    g0 = sh(rb, f"cat {PHY}/in_voltage0_hardwaregain").strip()
                    rb.client.exec_command(
                        f"rm -f /tmp/agc.bin; iio_readdev -b {BUFFER} -s {CAPTURE} cf-ad9361-lpc voltage0 voltage1 "
                        "> /tmp/agc.bin 2>/tmp/agc.err; echo done > /tmp/agc.done")
                    sh(rb, "rm -f /tmp/agc.done")
                    time.sleep(0.20)
                    t_step = time.time()
                    sh(ra, f"echo {end:.2f} > {PHY}/out_voltage0_hardwaregain")
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
                        np.save(args.keep_captures / f"agc_{mode}_{direction}_{rep}.npy", z.astype(np.complex64))
                    if z.size < CAPTURE // 2:
                        row["error"] = "short capture"
                    else:
                        row.update(analyse(z, int(0.2 * FS)))
                    res["runs"].append(row)
                    print(json.dumps(row))
                    del t_step
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
