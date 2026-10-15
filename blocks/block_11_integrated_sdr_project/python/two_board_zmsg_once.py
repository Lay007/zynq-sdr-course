#!/usr/bin/env python3
"""Single-shot messages between the board consoles (Lab 11.48): each message is sent once, board B listens.

    board A TX1 -> attenuators -> splitter -> board B RX1   (conducted)

Board B runs `zmsg receive --listen` (gp_ctrl[18], image of issue #68) in the background for the
whole run. Board A sends --messages messages with `zmsg send --once`, each with its own sequence
number and text, --interval seconds apart. At the end the receiver log is compared with what was
sent: delivered (distinct sequence numbers with the right text), lost, duplicates, and messages
that passed the CRC but were never sent in this run (wrong_accepted).

--receiver zmbox makes board B receive into the PS/PL mailbox instead (zmbox listen, Lab 11.49:
the fabric de-whitens, checks the CRC and fills the mailbox RX registers; needs the mailbox image).

Both boards need /root/zmsg built from blocks/block_11_integrated_sdr_project/sw/zmsg.c (and board B
/root/zmbox for --receiver zmbox; board B runs from a RAM disk, so copy them again after a reboot). The
script runs `zmsg stop` on board A first: a transmitter killed with kill -9 by an earlier tool
leaves its cyclic buffer playing, and a listening receiver would hear it.

    python two_board_zmsg_once.py --messages 500 --json-out zmsg_once.json
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import lab_11_30_two_board_cfo_validation as L
from lab_11_47_single_board_selfota import zynq_temp

RX_LINE = re.compile(r'RX sequence=(\d+) bytes=(\d+) (?:crc=OK|meta=CRC_OK) payload="(.*)"')
SUMMARY = re.compile(r"receptions (\d+), locked (\d+), delivered (\d+), crc failures (\d+), timeouts (\d+)")
ZMBOX_SUMMARY = re.compile(r"listened ([\d.]+) s, delivered (\d+), overflows seen (\d+)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--messages", type=int, default=100)
    ap.add_argument("--interval", type=float, default=0.5, help="seconds between messages")
    ap.add_argument("--lead", type=int, default=64, help="training symbols before the reference symbol (64: Lab 11.49)")
    ap.add_argument("--tx-gain", type=float, default=-30.0)
    ap.add_argument("--rx-gain", type=int, default=71)
    ap.add_argument("--no-listen", action="store_true", help="receiver without listen mode, for comparison")
    ap.add_argument("--receiver", choices=["zmsg", "zmbox"], default="zmsg",
                    help="board B receives with zmsg (PS reads the decoded bits) or zmbox (the PS/PL mailbox)")
    ap.add_argument("--max-temp", type=float, default=78.0, help="refuse to start if board B is hotter (no fan)")
    ap.add_argument("--json-out", type=Path, required=True)
    args = ap.parse_args()

    ra = L.runner_for("192.168.40.1", "root", "analog", 22, 60.0)
    rb = L.runner_for("192.168.20.1", "root", "analog", 22, 60.0)
    t_before = zynq_temp(rb)
    if t_before >= args.max_temp:
        raise SystemExit(f"board B Zynq at {t_before:.1f} C, not starting")
    sent = []
    log = ""
    try:
        L.sh(ra, "cd /root && ./zmsg stop")
        listen = "" if args.no_listen else "--listen "
        budget = args.messages * (args.interval + 1.5) + 30
        # --count is large so that duplicates could not end the receiver early; it is stopped below.
        if args.receiver == "zmbox":
            L.start_detached(rb, f"cd /root && nohup ./zmbox listen --timeout {budget:.0f} --rx-gain {args.rx_gain} "
                                 "> /tmp/zrx.log 2>&1 &")
        else:
            L.start_detached(rb, f"cd /root && nohup ./zmsg receive {listen}--count {10 * args.messages} --attempts 1000000 "
                                 f"--timeout {budget:.0f} --rx-gain {args.rx_gain} --quiet > /tmp/zrx.log 2>&1 &")
        time.sleep(3)
        for k in range(args.messages):
            seq = 1000 + k
            text = f"single shot {k:04d}"
            out = L.sh(ra, f"cd /root && ./zmsg send '{text}' --seq {seq} --once --lead {args.lead} "
                           f"--tx-gain {args.tx_gain}").strip()
            sent.append({"seq": seq, "text": text, "tx": out})
            time.sleep(args.interval)
        time.sleep(3)
        L.sh(rb, "for p in $(ps | grep -E '[z]msg receive|[z]mbox listen' | awk '{print $1}'); do kill $p; done; sleep 1")
        log = L.sh(rb, "cat /tmp/zrx.log")
    finally:
        L.sh(ra, "cd /root && ./zmsg stop")
        L.quiet_board(rb)
        t_after = zynq_temp(rb)
        ra.client.close()
        rb.client.close()

    by_seq = {s["seq"]: s["text"] for s in sent}
    got: dict[int, int] = {}
    wrong = 0
    for line in log.splitlines():
        m = RX_LINE.match(line)
        if not m:
            continue
        if by_seq.get(int(m[1])) == m[3]:
            got[int(m[1])] = got.get(int(m[1]), 0) + 1
        else:
            wrong += 1
    st = SUMMARY.search(log)
    zst = ZMBOX_SUMMARY.search(log)
    summary = {"sent": len(sent), "delivered": len(got), "lost": [s for s in by_seq if s not in got],
               "duplicates": sum(v - 1 for v in got.values()), "wrong_accepted": wrong,
               "receiver": dict(zip(("receptions", "locked", "delivered_lines", "crc_failures", "timeouts"),
                                    map(int, st.groups()))) if st else (
                   {"listened_s": float(zst[1]), "delivered_lines": int(zst[2]), "overflows": int(zst[3])} if zst else None),
               "receiver_tool": args.receiver,
               "listen": not args.no_listen, "lead": args.lead, "tx_gain_db": args.tx_gain, "rx_gain_db": args.rx_gain,
               "interval_s": args.interval, "board_b_zynq_c": [round(t_before, 1), round(t_after, 1)]}
    print(json.dumps({k: v for k, v in summary.items() if k != "lost"}), "lost:", summary["lost"][:20])
    args.json_out.write_text(json.dumps({"summary": summary, "sent": sent, "rx_log": log}, indent=1) + "\n",
                             encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
