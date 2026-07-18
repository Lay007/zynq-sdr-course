#!/usr/bin/env python3
"""Lab 11.31 - Stress the coarse-CFO estimator across its full +-60 kHz range on real hardware.

Lab 11.30 proved the estimator on a live two-board link, but the two AD9361s happened to sit only
~0.3 ppm apart -- an inter-board CFO of ~-290 Hz. That is *inside* a Costas loop's pull-in, so the
coarse estimator's reason for existing -- acquiring the tens-of-kHz offset a Costas loop cannot --
was never actually exercised on silicon.

This lab injects a CONTROLLED CFO by detuning the transmitter's LO: board A transmits the same
cyclic QPSK at `carrier + delta`, board B receives at `carrier`, so the recovered signal carries a
known `delta` (plus the ~-290 Hz intrinsic). Sweeping delta over +-70 kHz shows three things at
once:

  1. the 4th-power estimator tracks the injected CFO across the whole +-60 kHz unambiguous range;
  2. the fixed-point RTL model agrees with the float reference at every offset, not just near 0;
  3. beyond +-60 kHz the estimate FOLDS (aliases) by 120 kHz, exactly as `4*omega in (-pi,pi]`
     predicts -- the design boundary, demonstrated on a live signal.

Measured 2026-07-18 (915 MHz base, -30 dB TX into 30 dB attenuator, RX 50 dB), abridged:

    dTX      measured      float-vs-fixed(RTL)   note
    +10 kHz  +9 368 Hz     1.39 Hz
    +30 kHz  +29 371 Hz    4.53 Hz
    +50 kHz  +49 565 Hz    1.80 Hz
    +60 kHz  +59 708 Hz    0.25 Hz               boundary
    +70 kHz  -50 106 Hz    1.07 Hz               ALIAS -> folds to -50.2 kHz

The estimate's error stays a few hundred Hz across the range -- well inside a Costas loop's
pull-in, which is the point: coarse removes the bulk, the loop closes the residual.

`--self-test` runs the whole sweep on the GENERATED waveform with a synthetic CFO applied in
software (no radio): the estimator must track it and fold at the boundary. Run it first.

RF-SAFETY: conducted lab -- board A TX1 -> 30 dB attenuator -> board B RX1, nothing radiates.
Default TX -30 dB behind the attenuator. Both boards are quieted (-89.75 dB) on exit, including
after a failure. This lab reuses Lab 11.30's transmitter/receiver plumbing (reset_tx_dma,
detached streaming, DAC-source check, single contiguous capture); see that lab for the traps.
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_11_30_two_board_cfo_validation as lab  # noqa: E402  (shared bench plumbing)

ref = lab.ref  # coarse_cfo_ref, already on the path via lab_11_30

UNAMBIGUOUS_HZ = 60_000.0  # +-1/8 cycle/symbol at 480 kSym/s
DEFAULT_DELTAS_KHZ = [0, 5, 10, 20, 30, 40, 50, -10, -30, -50, 55, 60, 70, -70]


def fold(hz: float) -> float:
    """Fold a frequency into the estimator's (-60, +60] kHz unambiguous window."""
    while hz > UNAMBIGUOUS_HZ:
        hz -= 2 * UNAMBIGUOUS_HZ
    while hz <= -UNAMBIGUOUS_HZ:
        hz += 2 * UNAMBIGUOUS_HZ
    return hz


def fold_err(measured: float, expected_folded: float) -> float:
    """Error between two frequencies, itself folded into +-60 kHz. At the +-60 kHz singularity
    the estimate may report either sign (4*omega sits on +-pi), so a raw subtraction there reads
    ~120 kHz while the estimator is in fact correct; folding the *error* removes that artifact."""
    return abs(fold(measured - expected_folded))


def recover(rx: np.ndarray, taps: np.ndarray, window: int = 256) -> dict:
    """Matched filter -> best integer sub-symbol phase -> per-window coarse CFO (float + fixed).

    Mirrors the RTL estimator's own pipeline: strip DC, matched-filter, pick the sub-symbol
    sampling phase that minimises EVM, then run the 4th-power estimate over successive
    `window`-symbol blocks. The fixed path applies the RTL's SQ_SHIFT=11 truncation to symbols
    rescaled to ~2000 LSB (the matched-filter magnitude seen on real captures), so
    `estimator_diff_hz` is the gap between the float reference and the RTL's integer arithmetic.
    This is byte-for-byte the analysis that produced the results table in the lab writeup."""
    rx = rx - rx.mean()
    mf = np.convolve(rx, taps, mode="same")
    best = None
    for ph in range(lab.SPS):
        sy = mf[ph::lab.SPS][20:-20]
        if len(sy) < 512:
            continue
        sy = sy / np.sqrt(np.mean(np.abs(sy) ** 2))
        wv = ref.cfo_4th_float(sy[:512])
        e = lab.evm_percent(sy[:512] * np.exp(-1j * wv * np.arange(512)))
        if best is None or e < best[1]:
            best = (ph, e)
    sym = mf[best[0]::lab.SPS][20:-20]
    sym = sym / np.sqrt(np.mean(np.abs(sym) ** 2))
    hz_f, hz_x, evm = [], [], []
    for k in range(min(30, len(sym) // window)):
        seg = sym[k * window:(k + 1) * window]
        wf = ref.cfo_4th_float(seg)
        hz_f.append(wf / (2 * np.pi) * lab.SYMBOL_RATE)
        om, _, _ = ref.cfo_4th_fixed(seg, win=window, sq_shift=11, amp=2000.0)
        hz_x.append(ref.phase_units_to_hz(om))
        evm.append(lab.evm_percent(seg * np.exp(-1j * wf * np.arange(len(seg)))))
    # Aggregate the per-window estimates in the 4*omega domain (a circular mean), not with a plain
    # average. Right at the +-60 kHz singularity a burst's windows split between +60 and -60 kHz --
    # the SAME point on the 4*omega circle, one full turn apart -- and an arithmetic mean of the two
    # lands at ~0 with a huge spread (seen on hardware as +48 kHz +-36 kHz). The circular mean folds
    # them back together. Away from the boundary the windows cluster and it equals the plain mean to
    # <1 Hz, so only the boundary row moves. This is the analysis that produced the results table.
    span = 2 * UNAMBIGUOUS_HZ  # one full turn of 4*omega, expressed in Hz
    z = np.mean(np.exp(1j * 2 * np.pi * np.asarray(hz_f) / span))
    cfo_hz = float(np.angle(z) / (2 * np.pi) * span)
    return {
        "cfo_hz": cfo_hz,
        "cfo_std_hz": float(np.std([fold(h - cfo_hz) for h in hz_f])),
        "estimator_diff_hz": float(np.mean([abs(fold(a - b)) for a, b in zip(hz_x, hz_f)])),
        "evm_percent": float(st.median(evm)),
        "windows": len(hz_f),
    }


def print_row(w, delta_hz, meas, expected_fold, intrinsic):
    err = meas["cfo_hz"] - expected_fold
    aliased = abs(delta_hz + intrinsic) > UNAMBIGUOUS_HZ
    note = f"ALIAS -> {expected_fold/1e3:+.1f} kHz" if aliased else (
        "boundary" if abs(delta_hz + intrinsic) >= UNAMBIGUOUS_HZ - 2000 else "ok")
    w(f" {delta_hz/1e3:+6.1f} | {meas['cfo_hz']:+11.1f} |{meas['cfo_std_hz']:6.1f} | "
      f"{expected_fold:+11.1f} | {err:+9.1f} |{meas['evm_percent']:6.1f} | "
      f"{meas['estimator_diff_hz']:8.2f} | {note}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host-a", default=lab.DEFAULT_HOST)
    ap.add_argument("--host-b", default=lab.DEFAULT_HOST_B)
    ap.add_argument("--carrier", type=float, default=915e6)
    ap.add_argument("--deltas-khz", type=float, nargs="+", default=DEFAULT_DELTAS_KHZ,
                    help="TX-LO offsets to inject, in kHz")
    ap.add_argument("--tx-gain", type=float, default=-30.0)
    ap.add_argument("--rx-gain", type=float, default=50.0)
    ap.add_argument("--capture", type=int, default=131072)
    ap.add_argument("--symbols", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=20260715)
    ap.add_argument("--self-test", action="store_true",
                    help="apply the CFO in software to the generated waveform, no radio")
    ap.add_argument("--out", type=Path, default=Path(__file__).with_name("coarse_cfo_stress_sweep.json"))
    args = ap.parse_args()

    iq, _ = lab.make_cyclic_qpsk(args.symbols, args.seed)
    clean = iq[0::2].astype(float) + 1j * iq[1::2].astype(float)
    taps = lab.load_rrc_taps()
    header = ("dTX(kHz)| meas CFO(Hz)|  std | expected(Hz)|  error(Hz) | EVM% | f-vs-fx(Hz) | note")

    if args.self_test:
        # Carry a small synthetic "intrinsic" offset, exactly as the two boards do (~-284 Hz in
        # Lab 11.30). It keeps every swept point off the +-60 kHz singularity, where 4*omega sits
        # on +-pi and the tone averages to ~0 within a window -- the same reason the hardware sweep
        # never lands a point exactly on the boundary. This makes the self-test a faithful digital
        # twin of the hardware run: same waveform, same offsets, same analysis, just noiseless.
        intrinsic = -284.0
        print(f"SELF-TEST: CFO injected in software (no radio), intrinsic {intrinsic:+.0f} Hz; "
              "estimator must track the range and fold at the boundary\n")
        print(header)
        base = np.tile(clean, 8)
        n = np.arange(len(base))
        worst = 0.0
        for dk in args.deltas_khz:
            d = dk * 1e3
            rx = base * np.exp(1j * 2 * np.pi * (d + intrinsic) / lab.SAMPLE_RATE * n)
            m = recover(rx, taps)
            exp_fold = fold(d + intrinsic)
            print_row(print, d, m, exp_fold, intrinsic)
            # fold the error: at the +-60 kHz boundary the estimate may legitimately take either sign
            worst = max(worst, fold_err(m["cfo_hz"], exp_fold))
        ok = worst < 400.0  # noiseless, so this is slack; a real bug moves it by kHz
        print(f"\nSELF-TEST {'PASS' if ok else 'FAIL'} - worst |error| = {worst:.1f} Hz "
              f"({'estimator tracks the whole range and folds at the boundary' if ok else 'host chain is off'})")
        return 0 if ok else 1

    run_a = lab.runner_for(args.host_a, lab.DEFAULT_USER, lab.DEFAULT_PASSWORD, lab.DEFAULT_PORT, 15.0)
    run_b = lab.runner_for(args.host_b, lab.DEFAULT_USER_B, lab.DEFAULT_PASSWORD_B, lab.DEFAULT_PORT, 15.0)
    n_samples = len(iq) // 2
    rows = []
    try:
        lab.quiet_board(run_b)
        run_b(f"echo {int(args.carrier)} > {lab.PHY}/out_altvoltage0_RX_LO_frequency")
        run_b(f"echo {int(lab.SAMPLE_RATE)} > {lab.PHY}/in_voltage_sampling_frequency 2>/dev/null")
        run_b(f"echo manual > {lab.PHY}/in_voltage0_gain_control_mode 2>/dev/null")
        run_b(f"echo {args.rx_gain:.0f} > {lab.PHY}/in_voltage0_hardwaregain 2>/dev/null")
        lab.quiet_board(run_a)
        lab.upload_bytes_via_ssh_cat(run_a, payload=iq.tobytes(), remote_path="/tmp/lab_11_31_wave.bin")

        def measure(delta):
            lab.quiet_board(run_a)
            lab.reset_tx_dma(run_a)
            run_a(f"echo {int(lab.SAMPLE_RATE)} > {lab.PHY}/out_voltage_sampling_frequency 2>/dev/null")
            run_a(f"echo {int(args.carrier + delta)} > {lab.PHY}/out_altvoltage1_TX_LO_frequency")
            run_a(f"echo {args.tx_gain:.2f} > {lab.PHY}/out_voltage0_hardwaregain")
            run_a(f"echo 0 > {lab.PHY}/out_altvoltage1_TX_LO_powerdown 2>/dev/null")
            lab.start_detached(run_a, f"nohup iio_writedev -c -b {n_samples} -s {n_samples} "
                               "cf-ad9361-dds-core-lpc voltage0 voltage1 < /tmp/lab_11_31_wave.bin "
                               "> /tmp/lab_11_31_wd.log 2>&1 &")
            time.sleep(3)
            if lab.sh(run_a, f"devmem {lab.DAC_CHAN_CNTRL_7_CH0}").strip() not in ("0x00000002", "0x2"):
                lab.quiet_board(run_a)
                return None
            time.sleep(1)
            run_b(f"iio_readdev -b {args.capture} -s {args.capture} cf-ad9361-lpc voltage0 voltage1 "
                  "> /tmp/lab_11_31_cap.bin 2>/dev/null")
            raw = lab.pull_binary(run_b, "/tmp/lab_11_31_cap.bin")
            lab.quiet_board(run_a)
            s = np.frombuffer(raw, dtype=np.int16)
            if s.size == 0 or np.count_nonzero(s) < s.size // 10:
                return None
            return recover(s[0::2].astype(float) + 1j * s[1::2].astype(float), taps)

        intrinsic = 0.0
        r0 = measure(0.0)
        if r0 is not None:
            intrinsic = r0["cfo_hz"]
        print(f"intrinsic inter-board CFO (dTX=0): {intrinsic:+.1f} Hz\n")
        print(header)
        for dk in args.deltas_khz:
            if dk == 0 and r0 is not None:
                m = r0
            else:
                m = measure(dk * 1e3)
            if m is None:
                print(f" {dk:+6.1f} | FAIL (transmitter not streaming or receiver wedged)")
                continue
            exp_fold = fold(dk * 1e3 + intrinsic)
            print_row(print, dk * 1e3, m, exp_fold, intrinsic)
            rows.append({"delta_hz": dk * 1e3, "expected_folded_hz": exp_fold, "intrinsic_hz": intrinsic, **m})
    finally:
        try:
            lab.quiet_board(run_a)
            lab.quiet_board(run_b)
            print("\nboth boards quiet (-89.75 dB)")
        except Exception as exc:  # pragma: no cover - best-effort safety
            print(f"WARNING: could not quiet a board: {exc}")

    args.out.write_text(json.dumps({"carrier_hz": args.carrier, "unambiguous_hz": UNAMBIGUOUS_HZ,
                                    "sweep": rows}, indent=2))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
