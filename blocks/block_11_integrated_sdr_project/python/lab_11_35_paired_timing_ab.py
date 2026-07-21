#!/usr/bin/env python3
"""Lab 11.35 - interleaved, paired fixed-vs-Gardner hardware A/B.

Lab 11.34 found a large Gardner lock-rate gain but a one-attempt clean-rate deficit in an
unpaired sweep.  This runner removes slow bench drift as a systematic bias: every observation
is a fixed/Gardner pair at the same CFO and start offset, and AB/BA order alternates.

The primary gate is declared before acquisition:

* clean-attempt Gardner-minus-fixed 95% CI lower bound >= -2 percentage points;
* full-frame-lock Gardner-minus-fixed 95% CI lower bound >= +10 percentage points.

This is a conducted-only lab.  Board A must be the vendor cyclic-DMA TX connected as
``A TX1 -> 30 dB attenuator -> B RX1``; board B must run the course receiver.  Both boards
are forced to -89.75 dB before and after the run.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from pathlib import Path

import lab_11_32_two_board_fabric_coarse_cfo as B
from bench_config import (
    DEFAULT_HOST,
    DEFAULT_HOST_B,
    DEFAULT_PASSWORD,
    DEFAULT_PASSWORD_B,
    DEFAULT_PORT,
    DEFAULT_USER,
    DEFAULT_USER_B,
)


ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "docs" / "assets"
DEFAULT_JSON = ASSETS / "lab1135_paired_timing_ab_live.json"
DEFAULT_PNG = ASSETS / "lab1135_paired_timing_ab_live.png"
FIXED_MODE = B.RF_MODE | B.COARSE_BIT
GARDNER_MODE = FIXED_MODE | B.TIMING_RECOVERY_BIT


def is_lock(row: dict) -> bool:
    return int(row.get("received_symbols") or 0) >= B.SYMBOLS


def is_clean(row: dict) -> bool:
    return is_lock(row) and int(row.get("total_bit_errors") or 0) == 0


def paired_difference(pairs: list[dict], outcome) -> dict:
    """Normal CI for the mean of paired {-1,0,+1} Gardner-minus-fixed outcomes."""
    values = [int(outcome(pair["gardner"])) - int(outcome(pair["fixed"])) for pair in pairs]
    n = len(values)
    if not n:
        return {
            "pairs": 0,
            "fixed_successes": 0,
            "gardner_successes": 0,
            "gardner_only": 0,
            "fixed_only": 0,
            "delta": None,
            "delta_ci95": None,
        }
    mean = sum(values) / n
    variance = sum((value - mean) ** 2 for value in values) / (n - 1) if n > 1 else 0.0
    half = 1.959963984540054 * math.sqrt(variance / n)
    return {
        "pairs": n,
        "fixed_successes": sum(bool(outcome(pair["fixed"])) for pair in pairs),
        "gardner_successes": sum(bool(outcome(pair["gardner"])) for pair in pairs),
        "gardner_only": values.count(1),
        "fixed_only": values.count(-1),
        "delta": mean,
        "delta_ci95": [max(-1.0, mean - half), min(1.0, mean + half)],
    }


def numeric_summary(values: list[int]) -> dict:
    if not values:
        return {"count": 0, "min": None, "max": None, "mean": None, "median": None}
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
    }


def timing_telemetry(pairs: list[dict]) -> dict:
    groups: dict[str, list[int]] = {"clean": [], "dirty_full": [], "no_lock": []}
    ted: dict[str, dict[str, int]] = {
        name: {"-1": 0, "0": 0, "1": 0} for name in groups
    }
    for pair in pairs:
        row = pair["gardner"]
        timing = row.get("timing_debug") or {}
        if is_clean(row):
            group = "clean"
        elif is_lock(row):
            group = "dirty_full"
        else:
            group = "no_lock"
        if timing.get("omega_q16") is not None:
            groups[group].append(int(timing["omega_q16"]))
        if timing.get("ted_error") is not None:
            key = str(int(timing["ted_error"]))
            ted[group][key] = ted[group].get(key, 0) + 1
    return {
        name: {"omega_q16": numeric_summary(groups[name]), "ted_error_counts": ted[name]}
        for name in groups
    }


def error_localization(rows: list[dict]) -> dict:
    """Split full-frame errors between the preamble and payload regions."""
    full_rows = [row for row in rows if is_lock(row)]
    telemetry_rows = [row for row in full_rows if row.get("payload_errors") is not None]
    total_errors = [int(row.get("total_bit_errors") or 0) for row in telemetry_rows]
    payload_errors = [int(row.get("payload_errors") or 0) for row in telemetry_rows]
    preamble_errors = [
        max(total - payload, 0) for total, payload in zip(total_errors, payload_errors)
    ]
    payload_bits_per_frame = B.SYMBOLS * 2 - B.PREAMBLE_BITS
    dirty = [index for index, total in enumerate(total_errors) if total > 0]
    single = [index for index, total in enumerate(total_errors) if total == 1]
    return {
        "telemetry_available": bool(full_rows) and len(telemetry_rows) == len(full_rows),
        "full_frames": len(full_rows),
        "telemetry_frames": len(telemetry_rows),
        "total_bit_errors": sum(total_errors),
        "preamble_bit_errors": sum(preamble_errors),
        "payload_bit_errors": sum(payload_errors),
        "payload_bits": len(telemetry_rows) * payload_bits_per_frame,
        "aggregate_payload_ber": (
            sum(payload_errors) / (len(telemetry_rows) * payload_bits_per_frame)
            if telemetry_rows
            else None
        ),
        "dirty_full_frames": len(dirty),
        "preamble_only_dirty_frames": sum(
            payload_errors[index] == 0 for index in dirty
        ),
        "payload_only_dirty_frames": sum(
            payload_errors[index] > 0 and preamble_errors[index] == 0 for index in dirty
        ),
        "mixed_dirty_frames": sum(
            payload_errors[index] > 0 and preamble_errors[index] > 0 for index in dirty
        ),
        "single_bit_dirty_frames": len(single),
        "single_bit_preamble_frames": sum(
            preamble_errors[index] == 1 for index in single
        ),
        "single_bit_payload_frames": sum(
            payload_errors[index] == 1 for index in single
        ),
    }


def summarize(pairs: list[dict], *, clean_margin: float, lock_margin: float) -> dict:
    fixed_rows = [pair["fixed"] for pair in pairs]
    gardner_rows = [pair["gardner"] for pair in pairs]
    clean = paired_difference(pairs, is_clean)
    lock = paired_difference(pairs, is_lock)
    clean_lower = clean["delta_ci95"][0] if clean["delta_ci95"] else -1.0
    lock_lower = lock["delta_ci95"][0] if lock["delta_ci95"] else -1.0
    clean_noninferior = clean_lower >= -clean_margin
    lock_superior = lock_lower >= lock_margin
    by_cfo = []
    for cfo in sorted({float(pair["cfo_hz"]) for pair in pairs}):
        selected = [pair for pair in pairs if float(pair["cfo_hz"]) == cfo]
        by_cfo.append(
            {
                "cfo_hz": cfo,
                "pairs": len(selected),
                "clean": paired_difference(selected, is_clean),
                "lock": paired_difference(selected, is_lock),
            }
        )
    passed = bool(pairs) and clean_noninferior and lock_superior
    return {
        "pairs": len(pairs),
        "fixed": B.summarize_attempts(fixed_rows),
        "gardner": B.summarize_attempts(gardner_rows, timing_recovery=True),
        "paired_clean": clean,
        "paired_lock": lock,
        "clean_noninferiority_margin": clean_margin,
        "lock_superiority_margin": lock_margin,
        "clean_noninferior": clean_noninferior,
        "lock_superior": lock_superior,
        "passed": passed,
        "decision": "promote_gardner" if passed else "retain_fixed_baseline",
        "by_cfo": by_cfo,
        "gardner_timing_telemetry": timing_telemetry(pairs),
        "error_localization": {
            "fixed": error_localization(fixed_rows),
            "gardner": error_localization(gardner_rows),
        },
        "conclusion": (
            "Gardner is clean-rate non-inferior and improves full-frame lock by the declared margin."
            if passed
            else "The paired campaign does not satisfy both predeclared confidence-bound gates."
        ),
    }


def compact_row(row: dict, *, timing: bool) -> dict:
    return B.summarize_attempts([row], timing_recovery=timing)["attempt_results"][0]


def synthetic_row(*, lock: bool, clean: bool, omega: int = 16384) -> dict:
    errors = 0 if clean else 7
    return {
        "received_symbols": B.SYMBOLS if lock else 0,
        "total_bit_errors": errors if lock else 0,
        "timed_out": not lock,
        "ok": True,
        "timing_debug": {"mu_q16": 32768, "omega_q16": omega, "ted_error": 0},
    }


def self_test() -> int:
    pairs = []
    # 400 pairs: equal clean count, +20 percentage points of Gardner lock.
    for index in range(400):
        fixed_lock = index < 240
        gardner_lock = index < 320
        fixed_clean = index < 100
        gardner_clean = index < 100
        pairs.append(
            {
                "cfo_hz": 30_000.0,
                "fixed": synthetic_row(lock=fixed_lock, clean=fixed_clean),
                "gardner": synthetic_row(lock=gardner_lock, clean=gardner_clean),
            }
        )
    result = summarize(pairs, clean_margin=0.02, lock_margin=0.10)
    assert result["paired_clean"]["delta"] == 0.0
    assert result["paired_lock"]["delta"] == 0.2
    assert result["passed"]

    rejected = summarize(pairs[:40], clean_margin=0.02, lock_margin=0.10)
    assert not rejected["passed"]
    print("SELF-TEST PASS")
    return 0


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def plot(summary: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    metrics = [summary["paired_clean"], summary["paired_lock"]]
    labels = ["BER=0 attempt", "full-frame lock"]
    delta = [100.0 * row["delta"] for row in metrics]
    low = [100.0 * row["delta_ci95"][0] for row in metrics]
    high = [100.0 * row["delta_ci95"][1] for row in metrics]
    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    ax.errorbar(
        delta,
        range(2),
        xerr=[[d - lo for d, lo in zip(delta, low)], [hi - d for d, hi in zip(delta, high)]],
        fmt="o",
        color="#1f6feb",
        capsize=5,
        markersize=8,
    )
    ax.axvline(0.0, color="#6b7580", linewidth=1)
    ax.axvline(-100.0 * summary["clean_noninferiority_margin"], color="#e8590c", linestyle="--")
    ax.axvline(100.0 * summary["lock_superiority_margin"], color="#2b8a3e", linestyle="--")
    ax.set_yticks(range(2), labels)
    ax.set_xlabel("Gardner − fixed (percentage points), paired 95% CI")
    ax.set_title("Lab 11.35 — interleaved timing-recovery A/B")
    ax.grid(axis="x", color="#e3e7ec")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host-a", default=DEFAULT_HOST, help="vendor cyclic-DMA TX")
    ap.add_argument("--host-b", default=DEFAULT_HOST_B, help="course fabric RX")
    ap.add_argument("--carrier", type=float, default=915e6)
    ap.add_argument("--tx-gain", type=float, default=-30.0)
    ap.add_argument("--rx-gain", type=float, default=50.0)
    ap.add_argument("--frames", type=int, default=29)
    ap.add_argument("--cfo-values", default="0,30000,55000")
    ap.add_argument("--offsets", default="0,1,2,3,4,5,6,7")
    ap.add_argument("--pairs-per-offset", type=int, default=100)
    ap.add_argument("--clean-noninferiority-margin", type=float, default=0.02)
    ap.add_argument("--lock-superiority-margin", type=float, default=0.10)
    ap.add_argument("--checkpoint-every", type=int, default=20)
    ap.add_argument("--course-bitstream", type=Path, default=B.COURSE_BITSTREAM)
    ap.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    ap.add_argument("--png-out", type=Path, default=DEFAULT_PNG)
    ap.add_argument("--no-plot", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    return ap


def main() -> int:
    args = parser().parse_args()
    if args.self_test:
        return self_test()
    if args.pairs_per_offset <= 0:
        raise SystemExit("--pairs-per-offset must be positive")
    if not 0.0 <= args.clean_noninferiority_margin < 1.0:
        raise SystemExit("--clean-noninferiority-margin must be in [0, 1)")
    if not 0.0 <= args.lock_superiority_margin < 1.0:
        raise SystemExit("--lock-superiority-margin must be in [0, 1)")

    cfos = [float(value) for value in args.cfo_values.split(",")]
    offsets = [int(value) for value in args.offsets.split(",")]
    bitstream = args.course_bitstream.resolve()
    if not bitstream.is_file():
        raise SystemExit(f"Missing course bitstream evidence file: {bitstream}")

    iq = B.make_cyclic_frame(args.frames)
    n_samples = len(iq) // 2
    run_a = B.L.runner_for(args.host_a, DEFAULT_USER, DEFAULT_PASSWORD, DEFAULT_PORT, 20.0)
    run_b = B.L.runner_for(args.host_b, DEFAULT_USER_B, DEFAULT_PASSWORD_B, DEFAULT_PORT, 20.0)
    pairs: list[dict] = []
    payload = {
        "lab": "11.35",
        "status": "running",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "repository_commit": B.repository_commit(),
        "carrier_hz": args.carrier,
        "tx_gain_db": args.tx_gain,
        "rx_gain_db": args.rx_gain,
        "cfo_hz": cfos,
        "start_offsets": offsets,
        "pairs_per_offset": args.pairs_per_offset,
        "clean_noninferiority_margin": args.clean_noninferiority_margin,
        "lock_superiority_margin": args.lock_superiority_margin,
        "topology": "board A vendor TX1 -> 30 dB attenuator -> board B course RX1",
        "pairing": "fixed/Gardner at identical CFO and offset; order alternates AB/BA",
        "expected_course_bitstream": {
            "path": str(bitstream),
            "sha256": B.sha256_file(bitstream),
        },
        "pairs": pairs,
    }

    def sh(runner, command):
        return B.L.sh(runner, command)

    try:
        B.L.quiet_board(run_a)
        B.L.quiet_board(run_b)

        sh(run_b, f"echo {int(args.carrier)} > {B.PHY}/out_altvoltage0_RX_LO_frequency")
        sh(run_b, f"echo {int(B.L.SAMPLE_RATE)} > {B.PHY}/in_voltage_sampling_frequency 2>/dev/null")
        sh(run_b, f"echo manual > {B.PHY}/in_voltage0_gain_control_mode 2>/dev/null")
        sh(run_b, f"echo {args.rx_gain:.0f} > {B.PHY}/in_voltage0_hardwaregain 2>/dev/null")
        core_id = sh(run_b, f"devmem 0x{B.BASE_ADDR + 0x004:X} 2>/dev/null").strip()
        if not core_id.lower().endswith("4250534b"):
            raise RuntimeError(f"board B is not the course receiver (core_id={core_id})")
        payload["expected_course_bitstream"]["runtime_core_id"] = core_id

        devices = sh(
            run_a, "for d in /sys/bus/iio/devices/iio:device*; do cat $d/name 2>/dev/null; done"
        )
        if "dds" not in devices:
            raise RuntimeError("board A has no vendor cyclic-DMA TX device")
        payload["boards"] = {
            "tx": {"host": args.host_a, "kernel": sh(run_a, "uname -srvm").strip()},
            "rx": {"host": args.host_b, "kernel": sh(run_b, "uname -srvm").strip()},
        }

        B.L.reset_tx_dma(run_a)
        B.upload_bytes_via_ssh_cat(run_a, payload=iq.tobytes(), remote_path="/tmp/lab_11_35_frame.bin")
        sh(run_a, f"echo {int(B.L.SAMPLE_RATE)} > {B.PHY}/out_voltage_sampling_frequency 2>/dev/null")
        sh(run_a, f"echo {int(args.carrier)} > {B.PHY}/out_altvoltage1_TX_LO_frequency")
        sh(run_a, f"echo {args.tx_gain:.2f} > {B.PHY}/out_voltage0_hardwaregain")
        sh(run_a, f"echo 0 > {B.PHY}/out_altvoltage1_TX_LO_powerdown 2>/dev/null")
        B.L.start_detached(
            run_a,
            f"nohup iio_writedev -c -b {n_samples} -s {n_samples} cf-ad9361-dds-core-lpc "
            "voltage0 voltage1 < /tmp/lab_11_35_frame.bin > /tmp/lab_11_35_wd.log 2>&1 &",
        )
        time.sleep(3.0)
        writer_error = sh(run_a, "head -1 /tmp/lab_11_35_wd.log 2>/dev/null").strip()
        if writer_error:
            raise RuntimeError(f"iio_writedev failed: {writer_error!r}")
        dac = sh(run_a, f"devmem {B.L.DAC_CHAN_CNTRL_7_CH0}").strip()
        if dac not in ("0x00000002", "0x2"):
            raise RuntimeError(f"transmitter is not on DMA source: {dac}")

        total_pairs = len(cfos) * len(offsets) * args.pairs_per_offset
        sequence = 0
        for cfo in cfos:
            sh(run_a, f"echo {int(args.carrier + cfo)} > {B.PHY}/out_altvoltage1_TX_LO_frequency")
            time.sleep(0.4)
            for offset in offsets:
                for repetition in range(args.pairs_per_offset):
                    order = ("fixed", "gardner") if sequence % 2 == 0 else ("gardner", "fixed")
                    rows = {}
                    for mode_name in order:
                        mode = FIXED_MODE if mode_name == "fixed" else GARDNER_MODE
                        raw = B.qpsk_ber_once(
                            run_b,
                            B.BASE_ADDR,
                            B.SYMBOLS,
                            offset,
                            mode_bits=mode,
                            preamble_bits=B.PREAMBLE_BITS,
                        )
                        rows[mode_name] = compact_row(raw, timing=mode_name == "gardner")
                    pairs.append(
                        {
                            "sequence": sequence,
                            "cfo_hz": cfo,
                            "start_offset": offset,
                            "repetition": repetition,
                            "order": list(order),
                            "fixed": rows["fixed"],
                            "gardner": rows["gardner"],
                        }
                    )
                    sequence += 1
                    if sequence % args.checkpoint_every == 0 or sequence == total_pairs:
                        partial = summarize(
                            pairs,
                            clean_margin=args.clean_noninferiority_margin,
                            lock_margin=args.lock_superiority_margin,
                        )
                        payload["progress"] = {"completed_pairs": sequence, "total_pairs": total_pairs}
                        payload["summary"] = partial
                        write_json(args.json_out, payload)
                        print(
                            f"pairs {sequence}/{total_pairs} | clean delta="
                            f"{partial['paired_clean']['delta']:+.4f} lock delta="
                            f"{partial['paired_lock']['delta']:+.4f}"
                        )
    finally:
        try:
            sh(run_a, "pkill -9 -f iio_writedev 2>/dev/null || true")
            B.L.quiet_board(run_a)
            B.L.quiet_board(run_b)
            print("both boards quiet (-89.75 dB)")
        except Exception as exc:  # pragma: no cover - best-effort RF safety
            print(f"WARNING quiet: {exc}")
        run_a.client.close()
        run_b.client.close()

    payload["status"] = "complete"
    payload["completed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    payload["summary"] = summarize(
        pairs,
        clean_margin=args.clean_noninferiority_margin,
        lock_margin=args.lock_superiority_margin,
    )
    write_json(args.json_out, payload)
    if not args.no_plot:
        plot(payload["summary"], args.png_out)
    print(payload["summary"]["conclusion"])
    return 0 if payload["summary"]["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
