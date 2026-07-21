#!/usr/bin/env python3
"""Lab 11.32 - Coarse-CFO acquiring a real inter-board offset IN THE FABRIC (not on the host).

Labs 11.30/11.31 proved the coarse-CFO estimator against a real two-board link, but the *decision*
was made on the HOST: board B captured raw IQ and Python ran `coarse_cfo_ref`. This lab closes the
last gap -- the estimator runs IN THE PL on board B, and the on-chip BER counter reports the result.
The coarse block is in the shipped bitstream (`COARSE_ENABLE=1`), runtime-gated by `gp_ctrl[13]`.

    board A  --  vendor Pluto, iio_writedev streams a BIT-EXACT course frame, continuously
       |          (915 MHz + injected delta)
       |  contained SMA cable + 30 dB attenuator
       v
    board B  --  COURSE bitstream, fabric RX + Costas + coarse-CFO; on-chip BER counter

Sweeping the injected CFO with the fabric coarse ON vs OFF is the whole point: the Costas loop alone
cannot acquire a tens-of-kHz offset, the coarse estimator ahead of it can, and now that is a number
the PL reports, not a host post-process.

WHY THE ROLE SPLIT (board A vendor, board B course). The COURSE boot config has NO continuous-TX
path: its device tree exposes no `cf-ad9361-dds-core` (no DMA DAC device), and the fabric modem's
own TX is BURSTY -- `course_dac_fifo_source_mux` writes the DAC FIFO only on `bpsk_valid` unless a
vendor cyclic DMA supplies a rigid cadence, so a burst never becomes clean RF (board B RSSI stays at
the ~108 dB noise floor). So the transmitter role lives on the VENDOR image (which has the DDS/DMA
that `iio_writedev` drives into a continuous stream, the proven Lab 11.30 TX path) and the
receiver+coarse role lives on the COURSE image. The frame is rebuilt bit-exact from the modem's own
ROM so board B's preamble correlator and BER counter see exactly the frame the PL transmitter would.

THE FRAME IS BIT-EXACT. Bits come from `bpsk_frame_bits.mem` (the same ROM `qpsk_frame_dibit_source`
reads); the QPSK map is `qpsk_symbol_mapper.v` verbatim -- bit[2k] -> I, bit[2k+1] -> Q, 0 -> +A,
1 -> -A (A = 23170), then upsample x8 and the course RRC (`bpsk_rrc_tx_fir_taps.mem`) circularly, so
the cyclic DMA replay has no seam. `--self-test` decodes the generated frame in software and expects
0 bit errors -- run it first; a frame-gen bug would silently make every hardware number meaningless.

RF-SAFETY: conducted lab -- board A TX1 -> 30 dB attenuator -> board B RX1, nothing radiates. TX gain
-30 dB, safe behind the pad. Both boards are forced to -89.75 dB before and after. Do NOT raise TX to
"see signal"; if the link is weak, raise RX gain (the pad keeps the conducted level fixed).

Measured 2026-07-20 (915 MHz, -30 dB TX into 30 dB attenuator, RX 50 dB): fabric coarse ON acquired
at BER 0 at all 12 points across 0..55 kHz (75/288 clean attempts); Costas-only produced 0/216
clean attempts at 15..55 kHz. This proves acquisition range, not a continuous BER=0 link.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
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
import lab_11_30_two_board_cfo_validation as L
from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat
from lab_11_27_runtime_qpsk_digital_loopback import qpsk_ber_once

ROOT = Path(__file__).resolve().parents[3]
FRAME_MEM = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "rtl" / "bpsk_frame_bits.mem"
ASSET_DIR = ROOT / "docs" / "assets"
COURSE_BITSTREAM = (
    ROOT / "hardware" / "7020_ad936x_sdr" / "hdl" / "course_bpsk_fmcomms2_zc702" / "system.bit.bin"
)

BASE_ADDR = 0x79040000
SYMBOLS = 140          # QPSK symbols per frame (the RX frame the on-chip BER counter scores)
PREAMBLE_BITS = 24     # frame-sync correlation window
BITS_PER_FRAME = 2 * SYMBOLS
A_LEVEL = 23170        # qpsk_symbol_mapper POS_LEVEL; sign only matters here
QUIET_DB = "-89.750000"
PHY = L.PHY

# gp_ctrl mode bits (see the bridge): QPSK | raw-RX | DC-block | Costas | phase-pick [| coarse]
RF_MODE = 0x10 | 0x20 | 0x200 | 0x400 | 0x1000
COARSE_BIT = 0x2000
TIMING_RECOVERY_BIT = 0x4000


# --------------------------------------------------------------------------- #
# bit-exact course frame
# --------------------------------------------------------------------------- #
def frame_bits() -> np.ndarray:
    toks = [t for t in FRAME_MEM.read_text().split() if t.strip() in ("0", "1")]
    bits = np.array([int(t) for t in toks], dtype=int)
    if len(bits) < BITS_PER_FRAME:
        raise RuntimeError(f"{FRAME_MEM} has {len(bits)} bits, need {BITS_PER_FRAME}")
    return bits[:BITS_PER_FRAME]


def frame_symbols() -> np.ndarray:
    """140 QPSK symbols mapped exactly like qpsk_symbol_mapper.v (0 -> +A, 1 -> -A)."""
    fb = frame_bits()
    i = 1.0 - 2.0 * fb[0::2]   # bit[2k]   -> I
    q = 1.0 - 2.0 * fb[1::2]   # bit[2k+1] -> Q
    return (i + 1j * q) / np.sqrt(2.0)


def make_cyclic_frame(n_frames: int) -> np.ndarray:
    """int16 interleaved IQ of the frame tiled n_frames times, RRC-shaped circularly (seamless
    cyclic replay), scaled to ~3 dB below full scale -- the Lab 11.30 transmit shaping, frame data."""
    sym = np.tile(frame_symbols(), n_frames)
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


def self_test() -> int:
    """Decode the generated frame in software (matched filter -> symbol sampling -> dibit map) and
    expect 0 bit errors, proving the frame is bit-exact before trusting any hardware number."""
    iq = make_cyclic_frame(4)
    wave = iq[0::2].astype(float) + 1j * iq[1::2].astype(float)
    taps = L.load_rrc_taps()
    mf = np.convolve(wave, taps, mode="full")
    # RRC->RRC is a raised cosine with peak at lag len(taps)-1; symbols sit every SPS from there.
    start = len(taps) - 1
    centers = start + np.arange(len(frame_symbols())) * L.SPS
    s = mf[centers]
    # qpsk_symbol_mapper: I>0 <=> bit 0, I<0 <=> bit 1 (0 -> +A). Same for Q.
    rec = np.zeros(BITS_PER_FRAME, dtype=int)
    rec[0::2] = (s.real < 0).astype(int)
    rec[1::2] = (s.imag < 0).astype(int)
    errs = int(np.sum(rec != frame_bits()))
    print(f"SELF-TEST: recovered {BITS_PER_FRAME} bits, {errs} errors")
    print("SELF-TEST", "PASS - frame is bit-exact" if errs == 0 else "FAIL - frame-gen bug, fix before hardware")
    return 0 if errs == 0 else 1


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


# --------------------------------------------------------------------------- #
# statistics
# --------------------------------------------------------------------------- #
def wilson(count: int, total: int, z: float = 1.959963984540054):
    if total <= 0:
        return None
    p = count / total
    d = 1.0 + z * z / total
    c = (p + z * z / (2 * total)) / d
    h = z / d * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))
    return [max(0.0, c - h), min(1.0, c + h)]


def _signed(value: int, width: int) -> int:
    sign = 1 << (width - 1)
    return value - (1 << width) if value & sign else value


def summarize_attempts(
    rows: list[dict], *, symbol_count: int = SYMBOLS, timing_recovery: bool = False
) -> dict:
    """Summarize one equal-budget acquisition experiment without hiding failed attempts.

    ``best_ber`` answers whether the receiver acquired at least once.  ``aggregate_ber`` is
    conditional on a full frame being reported, while ``clean_attempt_rate`` keeps no-lock
    attempts in the denominator.  Keeping those meanings separate prevents a lucky clean frame
    from being presented as a stable BER result.
    """
    attempts = len(rows)
    full_rows = [row for row in rows if int(row.get("received_symbols") or 0) == symbol_count]
    clean_rows = [row for row in full_rows if int(row.get("total_bit_errors") or 0) == 0]
    errors = [int(row.get("total_bit_errors") or 0) for row in full_rows]
    best_err = min(errors) if errors else None
    total_errors = sum(errors)
    total_bits = len(full_rows) * symbol_count * 2
    compact_rows = []
    for row in rows:
        compact = {
            "start_offset": row.get("start_offset"),
            "received_symbols": int(row.get("received_symbols") or 0),
            "total_bit_errors": int(row.get("total_bit_errors") or 0),
            "timed_out": bool(row.get("timed_out", False)),
            "ok": bool(row.get("ok", False)),
        }
        for name in ("payload_errors", "status", "polls", "error"):
            if name in row:
                compact[name] = row[name]
        debug = row.get("debug")
        if isinstance(debug, dict):
            compact["debug"] = debug
            if timing_recovery:
                adc_word = int(str(debug.get("adc_input", "0")), 0)
                ted_word = int(str(debug.get("capture", "0")), 0)
                compact["timing_debug"] = {
                    "mu_q16": adc_word & 0xFFFF,
                    "omega_q16": _signed((adc_word >> 16) & 0xFFFF, 16),
                    "ted_error": _signed(ted_word & 0x7, 3),
                }
        compact_rows.append(compact)
    return {
        "locked": bool(full_rows),
        "reached_zero": bool(clean_rows),
        "best_errors": best_err,
        "best_ber": (best_err / (symbol_count * 2)) if best_err is not None else None,
        "full_frames": len(full_rows),
        "clean_frames": len(clean_rows),
        "attempts": attempts,
        "total_bits_in_full_frames": total_bits,
        "total_errors_in_full_frames": total_errors,
        "aggregate_ber": (total_errors / total_bits) if total_bits else None,
        "lock_rate": (len(full_rows) / attempts) if attempts else 0.0,
        "lock_rate_wilson95": wilson(len(full_rows), attempts),
        "clean_attempt_rate": (len(clean_rows) / attempts) if attempts else 0.0,
        "clean_attempt_rate_wilson95": wilson(len(clean_rows), attempts),
        "clean_given_lock_rate": (len(clean_rows) / len(full_rows)) if full_rows else 0.0,
        "attempt_results": compact_rows,
    }


def measure_point(
    runner_b, offsets, retries, coarse: bool, *, timing_recovery: bool = False
) -> dict:
    """Sweep offsets x retries with an EQUAL budget for coarse on/off and report acquisition, not a
    single-offset average. The two AD9361s run on independent clocks, so on top of the carrier CFO
    there is a residual sample-clock offset the fixed-phase RX sampler does not track: the frame's
    landing phase walks burst-to-burst, and a fixed start_offset catches good and bad phases alike.
    The honest, use-matching metric for a host-retry burst modem is therefore the BEST decode over
    the budget (did it ACQUIRE the CFO at all) plus the clean-frame fraction (how reliably), not the
    mean BER at one offset. `reached_zero` answers "can the loop acquire this offset"; `clean_rate`
    answers "how often"."""
    mode = RF_MODE | (COARSE_BIT if coarse else 0)
    if timing_recovery:
        mode |= TIMING_RECOVERY_BIT
    rows: list[dict] = []
    for off in offsets:
        for _ in range(retries):
            row = qpsk_ber_once(runner_b, BASE_ADDR, SYMBOLS, off, mode_bits=mode, preamble_bits=PREAMBLE_BITS)
            rows.append(row)
    return summarize_attempts(rows, timing_recovery=timing_recovery)


def summarize_experiment(results: list[dict], *, min_discriminating_cfo_hz: float) -> dict:
    on_acquired = [row for row in results if row["coarse_on"]["reached_zero"]]
    discriminating = [row for row in results if abs(row["cfo_hz"]) >= min_discriminating_cfo_hz]
    off_acquired = [row for row in discriminating if row["coarse_off"]["reached_zero"]]
    on_clean = sum(row["coarse_on"]["clean_frames"] for row in results)
    on_attempts = sum(row["coarse_on"]["attempts"] for row in results)
    off_clean = sum(row["coarse_off"]["clean_frames"] for row in discriminating)
    off_attempts = sum(row["coarse_off"]["attempts"] for row in discriminating)
    passed = bool(results) and len(on_acquired) == len(results) and not off_acquired
    conclusion = (
        f"in-fabric coarse ON acquired at BER=0 at {len(on_acquired)}/{len(results)} CFO points "
        f"({on_clean}/{on_attempts} clean attempts); Costas-only acquired at BER=0 at "
        f"{len(off_acquired)}/{len(discriminating)} points with |CFO| >= "
        f"{min_discriminating_cfo_hz / 1e3:g} kHz ({off_clean}/{off_attempts} clean attempts)"
    )
    return {
        "passed": passed,
        "coarse_on_acquired_points": len(on_acquired),
        "total_cfo_points": len(results),
        "coarse_on_clean_attempts": on_clean,
        "coarse_on_attempts": on_attempts,
        "costas_only_acquired_discriminating_points": len(off_acquired),
        "discriminating_cfo_points": len(discriminating),
        "costas_only_clean_attempts": off_clean,
        "costas_only_attempts": off_attempts,
        "min_discriminating_cfo_hz": min_discriminating_cfo_hz,
        "conclusion": conclusion,
    }


# --------------------------------------------------------------------------- #
# plot
# --------------------------------------------------------------------------- #
def plot(results: list[dict], carrier_hz: float, out_png: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Two categorical series, a CVD-safe blue/orange pair + distinct marker & dash (secondary
    # encoding), text in ink not series colour.
    C_ON, C_OFF = "#1f6feb", "#e8590c"
    INK, MUTED, GRID = "#1b1f24", "#6b7580", "#e3e7ec"
    khz = [r["cfo_hz"] / 1e3 for r in results]

    def floor_of(r):  # BER=0 -> rule-of-three bound for one acquired frame on a log axis
        if r["best_ber"] is None:
            return None
        return r["best_ber"] if r["best_ber"] > 0 else (3.0 / BITS_PER_FRAME)

    on_y = [floor_of(r["coarse_on"]) for r in results]
    off_y = [floor_of(r["coarse_off"]) for r in results]
    off_nolock = [r["cfo_hz"] / 1e3 for r in results if not r["coarse_off"]["locked"]]

    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    ax.set_yscale("log")
    xo = [k for k, y in zip(khz, on_y) if y is not None]
    yo = [y for y in on_y if y is not None]
    xf = [k for k, y in zip(khz, off_y) if y is not None]
    yf = [y for y in off_y if y is not None]
    ax.plot(xf, yf, "--s", color=C_OFF, lw=2, ms=7, mfc=C_OFF, mec="white", mew=1.2,
            label="coarse OFF (Costas only)", zorder=3)
    ax.plot(xo, yo, "-o", color=C_ON, lw=2, ms=8, mfc=C_ON, mec="white", mew=1.2,
            label="coarse ON (in-fabric)", zorder=4)
    # zero-error markers on the ON line get a hollow ring + a single direct label
    for k, y, r in zip(khz, on_y, results):
        if y is not None and r["coarse_on"]["best_ber"] == 0:
            ax.plot([k], [y], "o", ms=13, mfc="none", mec=C_ON, mew=1.4, zorder=5)
    if xo:
        ax.annotate("BER = 0  (95% upper bound shown)", xy=(xo[len(xo) // 2], yo[len(yo) // 2]),
                    xytext=(6, 14), textcoords="offset points", color=C_ON, fontsize=9, fontweight="bold")
    for k in off_nolock:  # coarse OFF lost the frame entirely
        ax.annotate("no lock", xy=(k, ax.get_ylim()[1]), ha="center", va="top",
                    color=C_OFF, fontsize=8.5, xytext=(0, -4), textcoords="offset points")

    ax.set_xlabel("injected inter-board CFO (kHz)", color=INK, fontsize=11)
    ax.set_ylabel("best acquired-frame BER", color=INK, fontsize=11)
    ax.set_title(f"In-fabric coarse-CFO vs Costas alone -- two boards, {carrier_hz/1e6:.0f} MHz over a 30 dB cable",
                 color=INK, fontsize=11.5, fontweight="bold")
    ax.grid(True, which="both", color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(MUTED)
    ax.tick_params(colors=MUTED)
    leg = ax.legend(loc="center left", frameon=False, fontsize=10)
    for t in leg.get_texts():
        t.set_color(INK)
    fig.tight_layout()
    fig.savefig(out_png, dpi=140, facecolor="white")
    plt.close(fig)
    print(f"wrote {out_png}")


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host-a", default=DEFAULT_HOST, help="transmitter (VENDOR Pluto image)")
    ap.add_argument("--host-b", default=DEFAULT_HOST_B, help="receiver (COURSE bitstream)")
    ap.add_argument("--carrier", type=float, default=915e6)
    ap.add_argument("--tx-gain", type=float, default=-30.0, help="dB; conducted, behind the 30 dB pad")
    ap.add_argument("--rx-gain", type=float, default=50.0)
    ap.add_argument("--frames", type=int, default=29, help="frames tiled into the cyclic TX buffer")
    ap.add_argument("--cfo-start", type=float, default=0.0)
    ap.add_argument("--cfo-stop", type=float, default=55000.0)
    ap.add_argument("--cfo-step", type=float, default=5000.0)
    ap.add_argument("--offsets", default="0,1,2,3,4,5,6,7")
    ap.add_argument("--retries-per-offset", "--bursts", dest="retries_per_offset", type=int, default=3,
                    help="attempts for each start offset and coarse setting (default: 3)")
    ap.add_argument("--min-discriminating-cfo", type=float, default=15000.0,
                    help="minimum |CFO| used for the Costas-only rejection gate")
    ap.add_argument("--timing-recovery", action="store_true",
                    help="set gp_ctrl[14] and run the continuous Gardner timing path")
    ap.add_argument(
        "--course-bitstream",
        type=Path,
        default=COURSE_BITSTREAM,
        help="local bitstream payload currently loaded on board B; recorded and hashed as evidence",
    )
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--no-plot", action="store_true")
    ap.add_argument("--json-out", type=Path,
                    default=ASSET_DIR / "lab1132_two_board_fabric_coarse_cfo.json")
    ap.add_argument("--png-out", type=Path,
                    default=ASSET_DIR / "lab1132_two_board_fabric_coarse_cfo.png")
    return ap


def main() -> int:
    args = build_arg_parser().parse_args()
    if args.self_test:
        return self_test()

    offsets = [int(x) for x in args.offsets.split(",")]
    cfos = list(np.arange(args.cfo_start, args.cfo_stop + 1.0, args.cfo_step))
    course_bitstream = args.course_bitstream.resolve()
    if not course_bitstream.is_file():
        raise SystemExit(f"Missing course bitstream evidence file: {course_bitstream}")
    iq = make_cyclic_frame(args.frames)
    n_samples = len(iq) // 2
    print(f"frame: {args.frames} x {SYMBOLS} sym cyclic -> {n_samples} samples "
          f"({n_samples/L.SAMPLE_RATE*1e3:.2f} ms) at {L.SAMPLE_RATE/1e6:.2f} MHz")

    run_a = L.runner_for(args.host_a, DEFAULT_USER, DEFAULT_PASSWORD, DEFAULT_PORT, 20.0)
    run_b = L.runner_for(args.host_b, DEFAULT_USER_B, DEFAULT_PASSWORD_B, DEFAULT_PORT, 20.0)

    def sh(r, c):
        return L.sh(r, c)

    results: list[dict] = []
    payload = {"timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "carrier_hz": args.carrier, "tx_gain_db": args.tx_gain, "rx_gain_db": args.rx_gain,
               "symbols": SYMBOLS, "bits_per_frame": BITS_PER_FRAME,
               "start_offsets": offsets, "retries_per_offset": args.retries_per_offset,
               "timing_recovery": args.timing_recovery,
               "topology": "board A (vendor Pluto, iio_writedev bit-exact course frame) TX1 -> 30 dB "
                           "pad -> board B (course fabric RX + coarse) RX1",
               "points": results}
    try:
        # board B receiver config (course fabric RX)
        L.quiet_board(run_b)
        sh(run_b, f"echo {int(args.carrier)} > {PHY}/out_altvoltage0_RX_LO_frequency")
        sh(run_b, f"echo {int(L.SAMPLE_RATE)} > {PHY}/in_voltage_sampling_frequency 2>/dev/null")
        sh(run_b, f"echo manual > {PHY}/in_voltage0_gain_control_mode 2>/dev/null")
        sh(run_b, f"echo {args.rx_gain:.0f} > {PHY}/in_voltage0_hardwaregain 2>/dev/null")
        sig = sh(run_b, f"devmem 0x{BASE_ADDR+0x004:X} 2>/dev/null").strip()
        if not sig.lower().endswith("4250534b"):
            raise RuntimeError(f"board B is not the course bitstream (gpreg core_id={sig}); boot the course config")

        # board A transmitter: continuous bit-exact frame via the vendor DMA path
        L.quiet_board(run_a)
        if "dds" not in sh(run_a, "for d in /sys/bus/iio/devices/iio:device*; do cat $d/name 2>/dev/null; done"):
            raise RuntimeError("board A has no cf-ad9361-dds-core (needs the VENDOR image to stream a continuous TX)")
        payload["repository_commit"] = repository_commit()
        payload["expected_course_bitstream"] = {
            "path": str(course_bitstream),
            "sha256": sha256_file(course_bitstream),
            "runtime_core_id": sig,
        }
        payload["boards"] = {
            "tx": {
                "host": args.host_a,
                "role": "vendor-image cyclic-DMA transmitter",
                "kernel": sh(run_a, "uname -srvm").strip(),
            },
            "rx": {
                "host": args.host_b,
                "role": "course-bitstream fabric receiver",
                "kernel": sh(run_b, "uname -srvm").strip(),
                "runtime_core_id": sig,
            },
        }
        L.reset_tx_dma(run_a)
        upload_bytes_via_ssh_cat(run_a, payload=iq.tobytes(), remote_path="/tmp/lab_11_32_frame.bin")
        sh(run_a, f"echo {int(L.SAMPLE_RATE)} > {PHY}/out_voltage_sampling_frequency 2>/dev/null")
        sh(run_a, f"echo {int(args.carrier)} > {PHY}/out_altvoltage1_TX_LO_frequency")
        sh(run_a, f"echo {args.tx_gain:.2f} > {PHY}/out_voltage0_hardwaregain")
        sh(run_a, f"echo 0 > {PHY}/out_altvoltage1_TX_LO_powerdown 2>/dev/null")
        L.start_detached(run_a, f"nohup iio_writedev -c -b {n_samples} -s {n_samples} cf-ad9361-dds-core-lpc "
                                "voltage0 voltage1 < /tmp/lab_11_32_frame.bin > /tmp/lab_11_32_wd.log 2>&1 &")
        time.sleep(3.0)
        werr = sh(run_a, "head -1 /tmp/lab_11_32_wd.log 2>/dev/null").strip()
        if werr:
            raise RuntimeError(f"iio_writedev failed: {werr!r} (stale cyclic buffer -> reboot board A)")
        dac = sh(run_a, f"devmem {L.DAC_CHAN_CNTRL_7_CH0}").strip()
        if dac not in ("0x00000002", "0x2"):
            raise RuntimeError(f"transmitter not streaming: DAC source={dac} (want 0x2=DMA)")
        print(f"board A transmitting the course frame: DAC={dac} (DMA), TX={args.tx_gain} dB @ {args.carrier/1e6:.3f} MHz")

        for cfo in cfos:
            sh(run_a, f"echo {int(args.carrier + cfo)} > {PHY}/out_altvoltage1_TX_LO_frequency")
            time.sleep(0.4)
            on = measure_point(
                run_b, offsets, args.retries_per_offset, coarse=True,
                timing_recovery=args.timing_recovery,
            )
            off = measure_point(
                run_b, offsets, args.retries_per_offset, coarse=False,
                timing_recovery=args.timing_recovery,
            )
            rssi = sh(run_b, f"cat {PHY}/in_voltage0_rssi 2>/dev/null").strip()
            results.append({"cfo_hz": float(cfo), "rssi_db": rssi, "coarse_on": on, "coarse_off": off})
            print(f"CFO {cfo/1e3:+6.1f} kHz | coarse ON best={on['best_ber']} "
                  f"clean={on['clean_frames']}/{on['attempts']} lock={on['lock_rate']:.2f} | "
                  f"OFF best={off['best_ber']} clean={off['clean_frames']}/{off['attempts']} "
                  f"lock={off['lock_rate']:.2f}")
    finally:
        try:
            sh(run_a, "pkill -9 -f iio_writedev 2>/dev/null")
            L.quiet_board(run_a)
            L.quiet_board(run_b)
            print("both boards quiet (-89.75 dB)")
        except Exception as exc:  # pragma: no cover - best-effort safety
            print(f"WARNING quiet: {exc}")
        run_a.client.close()
        run_b.client.close()

    payload["acceptance"] = summarize_experiment(
        results, min_discriminating_cfo_hz=args.min_discriminating_cfo
    )
    payload["conclusion"] = payload["acceptance"]["conclusion"]
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2))
    print(f"wrote {args.json_out}")
    print("Conclusion:", payload["conclusion"])
    if not args.no_plot and results:
        try:
            plot(results, args.carrier, args.png_out)
        except Exception as exc:  # pragma: no cover - plotting is optional
            print(f"plot skipped: {exc}")
    return 0 if payload["acceptance"]["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
