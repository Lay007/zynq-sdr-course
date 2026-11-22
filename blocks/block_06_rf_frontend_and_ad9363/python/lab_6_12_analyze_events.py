#!/usr/bin/env python3
"""Lab 6.12: analyze RX-local CTRL_OUT event log, or run a synthetic self-test.

CSV header: tick,source. A 'step' marker must share the same RX clock as the
detector events to make latency values meaningful; a TX host timestamp does not.
This tool does not claim to capture AD9361 GPIOs or align two SDR clocks.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter
from pathlib import Path

EVENTS = ("step", "lmt", "large_adc", "small_adc", "low_power", "gain_change")


def analyze(rows: list[tuple[int, str]], clock_hz: float) -> dict:
    if clock_hz <= 0:
        raise ValueError("clock_hz must be positive")
    if any(tick < 0 or source not in EVENTS for tick, source in rows):
        raise ValueError("nonnegative ticks and known event names required")
    if any(rows[i][0] < rows[i - 1][0] for i in range(1, len(rows))):
        raise ValueError("events must be sorted by nondecreasing RX-local tick")
    marks = [i for i, (_, kind) in enumerate(rows) if kind == "step"]
    intervals = []
    for j, start in enumerate(marks):
        stop = marks[j + 1] if j + 1 < len(marks) else len(rows)
        t0 = rows[start][0]
        observed = {}
        for tick, kind in rows[start + 1:stop]:
            if kind != "step" and kind not in observed:
                observed[kind] = round((tick - t0) * 1e6 / clock_hz, 3)
        intervals.append({"step_tick": t0, "first_event_latency_us": observed})
    return {
        "evidence": "event-log-analysis; source provenance requires verification",
        "clock_hz": clock_hz,
        "events": len(rows),
        "event_counts": dict(Counter(kind for _, kind in rows)),
        "step_windows": intervals,
        "lmt_first_latency_mean_us": (
            round(statistics.mean(w["first_event_latency_us"]["lmt"]
                                  for w in intervals if "lmt" in w["first_event_latency_us"]), 3)
            if any("lmt" in w["first_event_latency_us"] for w in intervals) else None
        ),
    }


def read_csv(path: Path) -> list[tuple[int, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["tick", "source"]:
            raise ValueError("CSV header must be exactly tick,source")
        return [(int(row["tick"]), row["source"].strip()) for row in reader]


def self_test() -> None:
    # 100 MHz: first LMT edge 120 ns after the local step; second 50 ns.
    rows = [(1000, "step"), (1007, "small_adc"), (1012, "lmt"),
            (1023, "large_adc"), (1034, "gain_change"),
            (5000, "step"), (5005, "lmt"), (5011, "gain_change")]
    result = analyze(rows, 100_000_000)
    assert result["event_counts"]["lmt"] == 2
    assert result["step_windows"][0]["first_event_latency_us"]["lmt"] == 0.12
    assert result["step_windows"][1]["first_event_latency_us"]["lmt"] == 0.05
    assert result["lmt_first_latency_mean_us"] == 0.085
    try:
        analyze([(100, "lmt"), (50, "step")], 100_000_000)
    except ValueError:
        pass
    else:
        raise AssertionError("unsorted input accepted")
    print("PASS: synthetic event-log analysis (not RF measurement)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--events", type=Path, help="receiver-local tick,source CSV")
    parser.add_argument("--clock-hz", type=float, help="measured PL counter frequency, Hz")
    parser.add_argument("--json-out", type=Path, help="write JSON summary")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.events is None or args.clock_hz is None:
        parser.error("--events and --clock-hz are required without --self-test")
    result = analyze(read_csv(args.events), args.clock_hz)
    formatted = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    print(formatted, end="")
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(formatted, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
