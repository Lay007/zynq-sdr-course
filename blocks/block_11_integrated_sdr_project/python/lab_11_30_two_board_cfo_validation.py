#!/usr/bin/env python3
"""Lab 11.30 - Validate the coarse-CFO estimator on a real two-board link.

The Block 05 feedforward coarse-CFO estimator (`qpsk_coarse_cfo.v`, modelled by
`coarse_cfo_ref.py`) was proven only against SYNTHETIC offsets: a float model, a fixed-point
model that matches it bit-exactly, and an RTL testbench fed a generated capture. All of that
shares one assumption -- that a real pair of AD9361s looks like the model. One board cannot
test it: TX_LO and RX_LO come from the same reference, so the CFO is ~0 and there is nothing to
estimate.

This lab closes that loop with TWO boards and INDEPENDENT references:

  board A  --  cyclic QPSK (course RRC, SPS=8, 480 kSym/s) out of the DAC via DMA
     |
     |  contained SMA cable + 30 dB attenuator  @ 915 MHz
     v
  board B  --  raw IQ capture, pulled over SSH

and then, on the host, runs the SAME `coarse_cfo_ref` float and fixed-point estimators over the
recovered symbols and compares them. The fixed-point path is the RTL's arithmetic, so agreement
here is evidence about the shipped HDL, not about a simulation.

It also reports EVM and, because the transmitted symbols are known, a real symbol error rate --
so "the link works" is a number, not an impression.

Measured 2026-07-17 (915 MHz, -30 dB TX into 30 dB attenuator, RX gain 50 dB):

    |corr| 35-50x   EVM 6.59 %   CFO -208.0 Hz (std 4.2 Hz)
    SER 0 / 14336 symbols (28672 bits)
    float vs fixed(RTL): mean |diff| = 0.09 Hz

FOUR TRAPS THIS LAB ENCODES (each cost real hours; see the .md for the full story):

1. `iio_readdev` defaults to a 256-sample buffer. Without `-b <N>` the capture is stitched from
   chunks WITH GAPS: correlation never locks, the CFO appears to wander by tens of kHz, and BER
   sticks near random -- while the spectrum and EVM look perfectly fine. Always pass `-b`.
   Verify with the periodicity check below.
2. A DDS-only tone does NOT power the TX synthesizer: with
   `adi,tx-lo-powerdown-managed-enable=1` the driver keeps `out_altvoltage1_TX_LO_powerdown=1`
   until a real TX STREAM exists, so nothing leaves the SMA no matter the hardwaregain. A DMA
   buffer (what this lab uses) is such a stream and brings the LO up by itself.
3. After `angle(mean(sym**4))/4` a QPSK constellation lands on the AXES, not at 45 deg -- the
   EVM reference must be rotated back by +pi/4 or you measure a constant ~54 % that no gain,
   timing or LO change will ever move.
4. `ifft(fft(a)*conj(fft(b)))` peaks at `off` meaning `a[n] ~ b[n-off]`, so the aligned
   reference is `np.roll(tx, +off)`. The wrong sign yields exactly the 0.75 SER of a random
   guess.

The `--self-test` flag runs the whole analysis chain on the generated waveform with no radio in
the path. It must report SER = 0. Run it first, always: three of the four traps above were
found only because the instrument was finally checked against a known signal.

RF-SAFETY: this is a CONDUCTED lab -- board A's TX1 goes into board B's RX1 through a cable and
a 30 dB attenuator, nothing radiates. Default TX gain is -30 dB, safe behind the attenuator. If
you run it over the air instead, drop to -50 dB and read the RF-safety note in the .md first.
Board B's stock rc.user re-arms a 71 MHz transmitter at -10 dB on EVERY boot; this lab kills it
and forces -89.75 dB before doing anything else, and quiets both boards on exit.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

from bench_config import (
    DEFAULT_HOST,
    DEFAULT_HOST_B,
    DEFAULT_PASSWORD,
    DEFAULT_PASSWORD_B,
    DEFAULT_PORT,
    DEFAULT_USER,
    DEFAULT_USER_B,
)
from lab_11_7_axi_lite_bpsk_bringup import ParamikoCommandRunner
from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat

_BLOCK05 = Path(__file__).resolve().parents[2] / "block_05_fpga_hdl_flow"
sys.path.insert(0, str(_BLOCK05 / "python"))
import coarse_cfo_ref as ref  # noqa: E402  (path set above)

RRC_TAPS_MEM = _BLOCK05 / "rtl" / "bpsk_rrc_tx_fir_taps.mem"

SPS = 8
SYMBOL_RATE = 480_000.0
SAMPLE_RATE = SPS * SYMBOL_RATE  # 3.84 MHz, the shipped modem configuration
PHY = "/sys/bus/iio/devices/iio:device0"
DDS = "/sys/bus/iio/devices/iio:device2"
QUIET_DB = "-89.750000"
# cf_axi_dds CHAN_CNTRL_7 for channel 0: DAC source select (0 = DDS, 2 = DMA, 3 = zero).
# Read-only here -- the driver owns it; we only use it to prove the DAC really carries the
# DMA buffer, because a running iio_writedev alone does not prove that.
DAC_CHAN_CNTRL_7_CH0 = "0x79024418"
# Symbols the float and fixed estimators are compared over. 256 keeps the fixed model's
# accumulator in the range its sq_shift=11 assumes, matching the RTL's own window scale.
ESTIMATOR_COMPARE_SYMBOLS = 256


# --------------------------------------------------------------------------- #
# waveform
# --------------------------------------------------------------------------- #
def load_rrc_taps() -> np.ndarray:
    """The very Q15 taps the PL transmitter uses, so the wave matches the course modem."""
    taps: list[int] = []
    for token in RRC_TAPS_MEM.read_text().split():
        token = token.strip()
        if token:
            value = int(token, 16)
            taps.append(value - 0x10000 if value >= 0x8000 else value)
    return np.asarray(taps, dtype=float) / 32768.0


def make_cyclic_qpsk(n_symbols: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Return (int16 interleaved IQ, complex symbols).

    The RRC is applied CIRCULARLY: the DMA replays this buffer end-to-start forever, and a
    linear convolution would leave a discontinuity at the seam that splatters the spectrum.
    """
    taps = load_rrc_taps()
    rng = np.random.default_rng(seed)
    bits = rng.integers(0, 2, size=(n_symbols, 2))
    symbols = ((bits[:, 0] * 2 - 1) + 1j * (bits[:, 1] * 2 - 1)) / np.sqrt(2.0)

    upsampled = np.zeros(n_symbols * SPS, dtype=complex)
    upsampled[::SPS] = symbols
    kernel = np.zeros(len(upsampled), dtype=complex)
    kernel[: len(taps)] = taps
    wave = np.fft.ifft(np.fft.fft(upsampled) * np.fft.fft(kernel))

    # Leave ~3 dB of headroom against the DAC full scale; the channel format is le:S16/16>>0,
    # i.e. plain signed 16-bit, no shifting needed.
    wave = wave * (0.70 * 32767 / np.max(np.abs(wave)))
    iq = np.zeros(len(wave) * 2, dtype=np.int16)
    iq[0::2] = np.round(wave.real).astype(np.int16)
    iq[1::2] = np.round(wave.imag).astype(np.int16)
    return iq, symbols


# --------------------------------------------------------------------------- #
# receiver / metrics
# --------------------------------------------------------------------------- #
def evm_percent(symbols: np.ndarray) -> float:
    """EVM against the nearest QPSK point, with the +pi/4 that trap 3 is about."""
    phase = np.angle(np.mean(symbols**4)) / 4.0
    rotated = symbols * np.exp(-1j * phase) * np.exp(1j * np.pi / 4)
    rotated = rotated / np.sqrt(np.mean(np.abs(rotated) ** 2))
    ideal = (np.sign(rotated.real) + 1j * np.sign(rotated.imag)) / np.sqrt(2)
    return float(
        np.sqrt(np.mean(np.abs(rotated - ideal) ** 2))
        / np.sqrt(np.mean(np.abs(ideal) ** 2))
        * 100
    )


def qpsk_bits(symbols: np.ndarray) -> np.ndarray:
    return ((np.sign(symbols.real) + 1) // 2).astype(int) * 2 + (
        (np.sign(symbols.imag) + 1) // 2
    ).astype(int)


def align(segment: np.ndarray, reference_fft: np.ndarray, n_ref: int) -> tuple[int, float, float]:
    """Circular cross-correlation against the known cyclic sequence.

    Magnitude is phase-invariant (finds the offset at any rotation) and the correlation's own
    phase hands back the rotation -- no 4-way search needed.
    """
    padded = np.zeros(n_ref, dtype=complex)
    take = min(len(segment), n_ref)
    padded[:take] = segment[:take]
    corr = np.fft.ifft(np.fft.fft(padded) * np.conj(reference_fft))
    magnitude = np.abs(corr)
    offset = int(np.argmax(magnitude))
    return offset, float(magnitude[offset] / np.mean(magnitude)), float(np.angle(corr[offset]))


def fractional_symbols(matched: np.ndarray, start: int, count: int, mu: float) -> np.ndarray:
    """Linear-interpolate symbol instants; board B samples on its own clock phase."""
    index = start + np.arange(count) * SPS + mu
    base = np.floor(index).astype(int)
    frac = index - base
    keep = (base > 1) & (base < len(matched) - 2)
    base, frac = base[keep], frac[keep]
    return (1 - frac) * matched[base] + frac * matched[base + 1]


def analyse(rx: np.ndarray, tx_symbols: np.ndarray, window: int) -> dict:
    """Matched filter -> fractional timing -> CFO (float+fixed) -> EVM -> SER."""
    taps = load_rrc_taps()
    matched = np.convolve(rx - rx.mean(), taps, mode="same")
    ref_fft = np.fft.fft(tx_symbols)
    n_ref = len(tx_symbols)

    best = None
    for mu in np.arange(0, SPS, 0.125):
        seg = fractional_symbols(matched, 200, min(window, 2048), mu)
        if len(seg) < min(window, 2048):
            continue
        seg = seg / np.sqrt(np.mean(np.abs(seg) ** 2))
        omega = ref.cfo_4th_float(seg)
        derotated = seg * np.exp(-1j * omega * np.arange(len(seg)))
        _, ratio, _ = align(derotated, ref_fft, n_ref)
        if best is None or ratio > best[1]:
            best = (float(mu), ratio)
    mu = best[0]

    windows = []
    total_symbols = 0
    total_errors = 0
    for k in range(64):
        seg = fractional_symbols(matched, 200 + k * window * SPS, window, mu)
        if len(seg) < window:
            break
        seg = seg / np.sqrt(np.mean(np.abs(seg) ** 2))
        omega = ref.cfo_4th_float(seg)
        derotated = seg * np.exp(-1j * omega * np.arange(len(seg)))
        offset, ratio, rotation = align(derotated, ref_fft, n_ref)

        # The point of the comparison is float-vs-fixed ARITHMETIC, so both must see exactly the
        # same input over exactly the same symbols. Feeding the fixed model a derotated slice
        # would have it estimate the residual instead, and any difference would just be the two
        # estimators' own variance over different sample counts.
        n_cmp = min(ESTIMATOR_COMPARE_SYMBOLS, len(seg))
        hz_float = ref.cfo_4th_float(seg[:n_cmp]) / (2 * np.pi) * SYMBOL_RATE
        omega_fixed, _, _ = ref.cfo_4th_fixed(seg[:n_cmp], win=n_cmp, sq_shift=11, amp=2000.0)
        hz_fixed = ref.phase_units_to_hz(omega_fixed)

        aligned = derotated * np.exp(-1j * rotation)
        errors = int(np.sum(qpsk_bits(aligned) != qpsk_bits(np.roll(tx_symbols, offset)[: len(aligned)])))
        total_symbols += len(aligned)
        total_errors += errors
        windows.append(
            {
                "corr_ratio": ratio,
                "evm_percent": evm_percent(derotated),
                "cfo_hz_float": hz_float,
                "cfo_hz_fixed": hz_fixed,
                "estimator_diff_hz": abs(hz_fixed - hz_float),
                "symbol_errors": errors,
            }
        )

    if not windows:
        raise RuntimeError("capture too short to analyse")
    pick = lambda key: np.array([w[key] for w in windows])  # noqa: E731
    return {
        "timing_mu_samples": mu,
        "windows": len(windows),
        "window_symbols": window,
        "corr_ratio_median": float(np.median(pick("corr_ratio"))),
        "evm_percent_median": float(np.median(pick("evm_percent"))),
        "cfo_hz_mean": float(np.mean(pick("cfo_hz_float"))),
        "cfo_hz_std": float(np.std(pick("cfo_hz_float"))),
        "cfo_ppm_at_carrier": None,  # filled by caller (needs the carrier)
        "estimator_diff_hz_mean": float(np.mean(pick("estimator_diff_hz"))),
        "estimator_diff_hz_max": float(np.max(pick("estimator_diff_hz"))),
        "symbols": total_symbols,
        "symbol_errors": total_errors,
        "ser": total_errors / total_symbols,
    }


def periodicity(rx: np.ndarray, period: int, span: int = 40000) -> float:
    """|autocorr| at the cyclic buffer's period. CFO only adds a constant phase, so a
    contiguous capture of a cyclic waveform must score ~1. A chunked one scores ~0 (trap 1)."""
    a = rx[:span]
    b = rx[period : period + span]
    n = min(len(a), len(b))
    if n < 1000:
        return float("nan")
    a, b = a[:n], b[:n]
    return float(abs(np.vdot(b, a)) / np.sqrt(np.vdot(a, a).real * np.vdot(b, b).real))


# --------------------------------------------------------------------------- #
# boards
# --------------------------------------------------------------------------- #
def runner_for(host: str, user: str, password: str, port: int, timeout_s: float) -> ParamikoCommandRunner:
    return ParamikoCommandRunner(
        host=host, user=user, password=password, port=port, key_path=None, timeout_s=timeout_s
    )


def sh(run: ParamikoCommandRunner, command: str) -> str:
    _, out, _ = run(command)
    return out.strip()


def quiet_board(run: ParamikoCommandRunner) -> None:
    run("pkill -9 -f iio_writedev 2>/dev/null; kill $(ps | grep '[m]odem_main' | awk '{print $1}') 2>/dev/null")
    run(f"echo {QUIET_DB} > {PHY}/out_voltage0_hardwaregain")


def check_capture_sane(samples: np.ndarray) -> None:
    """Reject a wedged receiver from the measurement capture itself.

    The receiver's DMA wedges easily (see "Known fragility" in the .md) and then returns a
    zero-length read or a buffer of all zeros -- which downstream turns into confident-looking
    nonsense: |autocorr| lands at exactly 1.0000 and EVM at exactly 0.00 %, the signature of a
    degenerate capture rather than of a good link.

    This deliberately inspects the measurement capture instead of taking a separate probe read:
    the receiver survives only ONE capture per boot, so a probe would consume it and leave the
    real capture wedged. (It also must not use a different `-b` -- see the note in main().)
    """
    if samples.size == 0 or np.count_nonzero(samples) < samples.size // 10:
        raise RuntimeError(
            f"receiver DMA is wedged ({samples.size} samples, "
            f"{int(np.count_nonzero(samples))} non-zero): a live receiver never returns an "
            "all-zero buffer. Reboot the receiver and re-run -- its Linux ignores plain "
            "`reboot`, use `echo 1 > /proc/sys/kernel/sysrq && echo b > /proc/sysrq-trigger` "
            "or `reboot -f`."
        )


def start_detached(run: ParamikoCommandRunner, command: str) -> None:
    """Launch a long-lived background process on the board.

    Must bypass ParamikoCommandRunner.__call__: it wraps everything in `sh -lc '...; rc=$?; ...'`
    and reads the channel to EOF, which tears the backgrounded job down with it -- `nohup ... &`
    started that way is gone within seconds, silently and with an empty log. Measured: launching
    the transmitter through the wrapper leaves the DAC source at 0x0 (DDS) with no process; the
    same command on a raw session gives 0x2 (DMA) and a live writer.
    """
    transport = run.client.get_transport()
    if transport is None:
        raise RuntimeError("SSH transport is not available.")
    channel = transport.open_session()
    channel.exec_command(command)
    channel.close()


def pull_binary(run: ParamikoCommandRunner, remote_path: str) -> bytes:
    transport = run.client.get_transport()
    if transport is None:
        raise RuntimeError("SSH transport is not available.")
    channel = transport.open_session()
    channel.exec_command(f"cat {remote_path}")
    chunks = []
    while True:
        if channel.recv_ready():
            chunks.append(channel.recv(65536))
            continue
        if channel.exit_status_ready() and not channel.recv_ready():
            break
        time.sleep(0.01)
    channel.close()
    return b"".join(chunks)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host-a", default=DEFAULT_HOST, help="transmitter board")
    ap.add_argument("--host-b", default=DEFAULT_HOST_B, help="receiver board (independent reference)")
    ap.add_argument("--carrier", type=float, default=915e6)
    ap.add_argument("--tx-gain", type=float, default=-30.0, help="dB; conducted default, use -50 for OTA")
    ap.add_argument("--rx-gain", type=float, default=50.0)
    ap.add_argument("--symbols", type=int, default=4096, help="cyclic waveform length in symbols")
    ap.add_argument("--capture", type=int, default=131072, help="samples; also the RX buffer size (trap 1)")
    ap.add_argument("--window", type=int, default=1024, help="symbols per estimator window")
    ap.add_argument("--seed", type=int, default=20260715)
    ap.add_argument("--self-test", action="store_true", help="analyse the generated waveform, no radio; expects SER=0")
    ap.add_argument("--out", type=Path, default=Path(__file__).with_name("two_board_cfo_validation.json"))
    args = ap.parse_args()

    iq, tx_symbols = make_cyclic_qpsk(args.symbols, args.seed)
    n_samples = len(iq) // 2
    print(f"waveform: {args.symbols} QPSK symbols -> {n_samples} samples "
          f"({n_samples / SAMPLE_RATE * 1e3:.2f} ms cyclic) at {SAMPLE_RATE/1e6:.2f} MHz")

    if args.self_test:
        clean = iq[0::2].astype(float) + 1j * iq[1::2].astype(float)
        result = analyse(np.tile(clean, 4), tx_symbols, args.window)
        print(f"SELF-TEST: EVM {result['evm_percent_median']:.2f} %  "
              f"|corr| {result['corr_ratio_median']:.1f}x  SER {result['ser']:.6f}")
        ok = result["ser"] == 0.0
        print("SELF-TEST", "PASS - the analysis chain is trustworthy" if ok else "FAIL - fix the host chain before trusting any measurement")
        return 0 if ok else 1

    run_a = runner_for(args.host_a, DEFAULT_USER, DEFAULT_PASSWORD, DEFAULT_PORT, 15.0)
    run_b = runner_for(args.host_b, DEFAULT_USER_B, DEFAULT_PASSWORD_B, DEFAULT_PORT, 15.0)
    try:
        # Board B first: its stock rc.user re-arms a hot 71 MHz TX on every boot.
        quiet_board(run_b)
        print(f"board B quiet: TX={sh(run_b, f'cat {PHY}/out_voltage0_hardwaregain')}")
        run_b(f"echo {int(args.carrier)} > {PHY}/out_altvoltage0_RX_LO_frequency")
        run_b(f"echo {int(SAMPLE_RATE)} > {PHY}/in_voltage_sampling_frequency 2>/dev/null")
        run_b(f"echo manual > {PHY}/in_voltage0_gain_control_mode 2>/dev/null")
        run_b(f"echo {args.rx_gain:.0f} > {PHY}/in_voltage0_hardwaregain 2>/dev/null")
        quiet_board(run_a)
        upload_bytes_via_ssh_cat(run_a, payload=iq.tobytes(), remote_path="/tmp/lab_11_30_wave.bin")
        run_a(f"echo {int(SAMPLE_RATE)} > {PHY}/out_voltage_sampling_frequency 2>/dev/null")
        run_a(f"echo {int(args.carrier)} > {PHY}/out_altvoltage1_TX_LO_frequency")
        run_a(f"echo {args.tx_gain:.2f} > {PHY}/out_voltage0_hardwaregain")
        # Trap 2: a DMA stream is what brings the TX synthesizer up. Assert it anyway; harmless
        # if the driver already did, and it makes the intent explicit.
        run_a(f"echo 0 > {PHY}/out_altvoltage1_TX_LO_powerdown 2>/dev/null")
        start_detached(
            run_a,
            f"nohup iio_writedev -c -b {n_samples} -s {n_samples} cf-ad9361-dds-core-lpc "
            "voltage0 voltage1 < /tmp/lab_11_30_wave.bin > /tmp/lab_11_30_wd.log 2>&1 &",
        )
        time.sleep(3.0)
        log = sh(run_a, "head -1 /tmp/lab_11_30_wd.log 2>/dev/null")
        if log:
            raise RuntimeError(f"iio_writedev failed: {log!r} (a stale cyclic buffer holds the DMA; reboot board A)")
        # A running iio_writedev is not proof of transmission: the DAC only carries the buffer
        # once the driver has switched the channel source DDS(0) -> DMA(2). Read it back rather
        # than trust the process, or a silent DDS-with-zero-scale looks exactly like a dead link.
        dac_src = sh(run_a, f"devmem {DAC_CHAN_CNTRL_7_CH0}")
        if dac_src.strip() not in ("0x00000002", "0x2"):
            raise RuntimeError(
                f"transmitter is not streaming: DAC source select reads {dac_src} "
                "(expected 0x2 = DMA). 0x0 means the channel is still on the DDS, 0x3 means a "
                "forced-zero output. Do not devmem this register by hand -- let the driver own "
                "it, and reboot board A if a stale buffer is stuck."
            )
        print(f"board A transmitting: TX={sh(run_a, f'cat {PHY}/out_voltage0_hardwaregain')} dB "
              f"at {args.carrier/1e6:.3f} MHz, DAC source={dac_src} (DMA), "
              f"LO_powerdown={sh(run_a, f'cat {PHY}/out_altvoltage1_TX_LO_powerdown')}")

        # Trap 1: -b MUST cover the whole capture or the record is chunked with gaps. Do this
        # exactly ONCE -- the receiver survives one capture per boot, and a second read with a
        # different -b makes the driver stitch stale chunks, reintroducing the very same trap.
        time.sleep(1.0)
        run_b(
            f"iio_readdev -b {args.capture} -s {args.capture} cf-ad9361-lpc voltage0 voltage1 "
            "> /tmp/lab_11_30_cap.bin 2>/dev/null"
        )
        raw = pull_binary(run_b, "/tmp/lab_11_30_cap.bin")
        print(f"captured {len(raw)} bytes")
    finally:
        try:
            quiet_board(run_a)
            quiet_board(run_b)
            print("both boards quiet (-89.75 dB)")
        except Exception as exc:  # pragma: no cover - best-effort safety
            print(f"WARNING: could not quiet a board: {exc}")

    samples = np.frombuffer(raw, dtype=np.int16)
    check_capture_sane(samples)
    rx = samples[0::2].astype(float) + 1j * samples[1::2].astype(float)
    if len(rx) < 4 * n_samples:
        raise RuntimeError(f"capture too short: {len(rx)} samples")
    print(f"receiver alive: capture rms = {np.sqrt(np.mean(np.abs(rx) ** 2)):.1f} counts")

    ac = periodicity(rx - rx.mean(), n_samples)
    print(f"contiguity check: |autocorr| at the {n_samples}-sample cyclic period = {ac:.4f}")
    if ac < 0.3:
        print("  ^ FAIL (trap 1): the capture is chunked, not contiguous. Every metric below is meaningless.")

    result = analyse(rx, tx_symbols, args.window)
    result["cfo_ppm_at_carrier"] = result["cfo_hz_mean"] / args.carrier * 1e6
    result["periodicity_autocorr"] = ac
    result["carrier_hz"] = args.carrier
    result["tx_gain_db"] = args.tx_gain
    result["rx_gain_db"] = args.rx_gain

    print(f"\ntiming mu = {result['timing_mu_samples']:.3f} samples, |corr| = {result['corr_ratio_median']:.1f}x")
    print(f"EVM       = {result['evm_percent_median']:.2f} %")
    print(f"CFO       = {result['cfo_hz_mean']:+.1f} Hz (std {result['cfo_hz_std']:.1f} Hz) "
          f"-> {result['cfo_ppm_at_carrier']:+.3f} ppm at {args.carrier/1e6:.0f} MHz")
    print(f"estimator float vs fixed(RTL): mean |diff| = {result['estimator_diff_hz_mean']:.2f} Hz, "
          f"max {result['estimator_diff_hz_max']:.2f} Hz")
    print(f"SER       = {result['symbol_errors']} / {result['symbols']} = {result['ser']:.6f}")

    args.out.write_text(json.dumps(result, indent=2))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
