#!/usr/bin/env python3
"""Two-board chat through the PS/PL mailboxes (Lab 11.50): both boards run `zmbox chat`, lines are typed on a schedule.

    board A TX1 -> attenuators -> splitter -> board B RX1
    board B TX1 -> attenuators -> board A RX1             (conducted, two separate paths)

Both boards need the mailbox image with the #69 fix (issue69-listen-silent) and /root/zmbox built from
blocks/block_11_integrated_sdr_project/sw/zmbox.c (both boards lose /root on a reboot: copy it again).
Each round board A types "a<k>", and --period seconds later board B types "b<k>". Afterwards both
consoles are compared with what was typed: delivered lines in each direction, lines that arrived
with a text nobody typed (wrong), and lines that arrived twice.

    python two_board_chat.py --rounds 100 --tx-gain-b -50 --json-out chat.json
"""
from __future__ import annotations

import argparse
import json
import re
import threading
from pathlib import Path

import lab_11_30_two_board_cfo_validation as L
from lab_11_47_single_board_selfota import zynq_temp

RX_LINE = re.compile(r"^<< (.*)$", re.M)


def typing_script(who: str, rounds: int, period: float, start: float) -> str:
    """Shell commands that print who<k> every 2*period seconds, starting after `start` seconds."""
    parts = [f"sleep {start:g}"]
    for k in range(rounds):
        parts += [f"echo {who}{k}", f"sleep {2 * period:g}"]
    parts.append("sleep 3")
    return "(" + "; ".join(parts) + ")"


def count(console: str, name: str, who: str, rounds: int) -> dict:
    """Lines from the other board as printed by `zmbox chat` on this one."""
    got = RX_LINE.findall(console)
    expected = {f"{name}: {who}{k}" for k in range(rounds)}
    ok = [g for g in got if g in expected]
    return {"delivered": len(set(ok)), "duplicates": len(ok) - len(set(ok)),
            "wrong": len([g for g in got if g not in expected]),
            "missing": sorted(k for k in range(rounds) if f"{name}: {who}{k}" not in set(ok))}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rounds", type=int, default=30)
    ap.add_argument("--period", type=float, default=2.0, help="seconds between A's line and B's reply")
    ap.add_argument("--tx-gain-a", type=float, default=-30.0)
    ap.add_argument("--tx-gain-b", type=float, default=-50.0,
                    help="the B -> A path of the course bench has no splitter; louder than -40 dB overdrives board A at 71 dB")
    ap.add_argument("--rx-gain", type=int, default=71)
    ap.add_argument("--max-temp", type=float, default=78.0, help="refuse to start if board B is hotter (no fan)")
    ap.add_argument("--json-out", type=Path, required=True)
    args = ap.parse_args()

    timeout = 60.0 + args.rounds * 2 * args.period + 30
    ra = L.runner_for("192.168.40.1", "root", "analog", 22, timeout)
    rb = L.runner_for("192.168.20.1", "root", "analog", 22, timeout)
    t_before = zynq_temp(rb)
    if t_before >= args.max_temp:
        raise SystemExit(f"board B Zynq at {t_before:.1f} C, not starting")
    consoles: dict[str, str] = {}

    def run(key, runner, who, name, gain, start):
        cmd = (f"cd /root && {typing_script(who, args.rounds, args.period, start)} | "
               f"ZMBOX_DEBUG=1 ./zmbox chat --name {name} --tx-gain {gain:g} --rx-gain {args.rx_gain} 2>&1")
        consoles[key] = L.sh(runner, cmd)

    threads = [threading.Thread(target=run, args=("a", ra, "a", "A", args.tx_gain_a, 3)),
               threading.Thread(target=run, args=("b", rb, "b", "B", args.tx_gain_b, 3 + args.period))]
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        for r in (ra, rb):
            L.sh(r, "cd /root && ./zmbox stop")
    summary = {"rounds": args.rounds, "period_s": args.period, "tx_gain_a_db": args.tx_gain_a,
               "tx_gain_b_db": args.tx_gain_b, "rx_gain_db": args.rx_gain,
               "a_to_b": count(consoles["b"], "A", "a", args.rounds),
               "b_to_a": count(consoles["a"], "B", "b", args.rounds),
               "crc_dropped": {"at_a": consoles["a"].count("packet dropped"), "at_b": consoles["b"].count("packet dropped")},
               "not_sent": consoles["a"].count("not sent") + consoles["b"].count("not sent"),
               "board_b_zynq_c": [t_before, zynq_temp(rb)]}
    print(json.dumps({k: v for k, v in summary.items() if k not in ("a_to_b", "b_to_a")}))
    for d in ("a_to_b", "b_to_a"):
        s = summary[d]
        print(f"{d}: delivered {s['delivered']} of {args.rounds}, wrong {s['wrong']}, duplicates {s['duplicates']}, missing {s['missing']}")
    args.json_out.write_text(json.dumps({"summary": summary, "console_a": consoles["a"], "console_b": consoles["b"]}, indent=1) + "\n",
                             encoding="utf-8")
    ra.client.close()
    rb.client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
