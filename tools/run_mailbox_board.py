#!/usr/bin/env python3
"""Issue #55 stage 2 / Lab 5.12 on a board: PS -> AXI-Lite -> PL mailbox echo -> PS on Zynq Linux.

Loads the mailbox block design (tools/build_block5_mailbox_bd.py, mailbox at 0x40000000) into the
FPGA of board A through fpga_manager, the same way tools/run_ofdm_dma_board.py does: stop the IIO
users, unbind the drivers of the board's own PL cores, load, test with `devmem`, then warm-reboot
the board back to its own image. The board has no Python, so every message is one batched shell
command. Register contract: blocks/block_05_fpga_hdl_flow/rtl/zynq_message_mailbox_axi_lite.v.

Tests: ID/VERSION; the Lab 11.46 "Hello from board A" sequence 17 echo; random messages of 0-64
bytes; an over-long length (frame error); overflow (a second message before RX_ACK keeps the first
and sets RX_OVERFLOW); RX_ACK clearing RX_VALID and RX_OVERFLOW.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import socket
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "blocks" / "block_11_integrated_sdr_project" / "python"))
import lab_11_30_two_board_cfo_validation as L  # noqa: E402
from bit_to_fpga_manager_bin import convert  # noqa: E402
from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat  # noqa: E402

BASE = 0x40000000
REG = {"id": 0x00, "version": 0x04, "control": 0x08, "status": 0x0C, "tx_seq": 0x10, "tx_len": 0x14,
       "tx_data": 0x20, "rx_seq": 0x60, "rx_len": 0x64, "rx_meta": 0x68, "rx_data": 0x70}
PL_DEVICES = ["79024000.cf-ad9361-dds-core-lpc", "79020000.cf-ad9361-lpc", "7c420000.dma", "7c400000.dma"]


def a(name: str, word: int = 0) -> str:
    return f"0x{BASE + REG[name] + 4 * word:X}"


def words(payload: bytes) -> list[int]:
    padded = payload.ljust(64, b"\0")[:64]
    return [struct.unpack_from("<I", padded, 4 * i)[0] for i in range(16)]


def send_and_read(r, seq: int, length: int, payload: bytes, ack: bool = True) -> dict:
    cmd = [f"devmem {a('tx_seq')} 32 {seq}", f"devmem {a('tx_len')} 32 {length}"]
    cmd += [f"devmem {a('tx_data', i)} 32 {w}" for i, w in enumerate(words(payload))]
    cmd += [f"devmem {a('control')} 32 1",
            f"i=0; while [ $i -lt 100 ]; do s=$(devmem {a('status')}); [ $((s & 4)) -ne 0 ] && break; i=$((i+1)); done",
            f"echo STATUS $(devmem {a('status')})", f"echo SEQ $(devmem {a('rx_seq')})",
            f"echo LEN $(devmem {a('rx_len')})", f"echo META $(devmem {a('rx_meta')})"]
    cmd += [f"echo D{i} $(devmem {a('rx_data', i)})" for i in range(16)]
    if ack:
        cmd += [f"devmem {a('control')} 32 2", f"echo AFTER $(devmem {a('status')})"]
    out = dict(line.split()[:2] for line in L.sh(r, "; ".join(cmd)).splitlines() if line[:1].isupper() and " 0x" in line)
    data = b"".join(struct.pack("<I", int(out[f"D{i}"], 16)) for i in range(16))
    res = {"status": int(out["STATUS"], 16), "seq": int(out["SEQ"], 16), "len": int(out["LEN"], 16),
           "meta": int(out["META"], 16), "data": data}
    if ack:
        res["after_ack"] = int(out["AFTER"], 16)
    return res


def wait_ssh(host: str, timeout: float) -> bool:
    t0, seen_down = time.time(), False
    while time.time() - t0 < timeout:
        s = socket.socket()
        s.settimeout(2)
        try:
            s.connect((host, 22))
            up = True
        except OSError:
            up = False
        finally:
            s.close()
        seen_down |= not up
        if seen_down and up:
            return True
        time.sleep(3)
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default="192.168.40.1")
    ap.add_argument("--bit", type=Path, default=Path(r"C:\tmp\mb\proj\mailbox_echo.runs\impl_1\mailbox_echo_bd_wrapper.bit"))
    ap.add_argument("--messages", type=int, default=200)
    ap.add_argument("--seed", type=int, default=55)
    ap.add_argument("--no-reboot", action="store_true")
    ap.add_argument("--json-out", type=Path, required=True)
    args = ap.parse_args()

    bit = args.bit.read_bytes()
    fw = convert(bit)
    res: dict = {"issue": 55, "stage": 2, "host": args.host, "bit_sha256": hashlib.sha256(bit).hexdigest(),
                 "base": hex(BASE), "checks": {}}
    r = L.runner_for(args.host, "root", "analog", 22, 60.0)
    sh = L.sh
    try:
        sh(r, "for p in $(ps | grep -E '[i]io_writedev|[i]io_readdev|[i]iod' | awk '{print $1}'); do kill -9 $p; done")
        L.quiet_board(r)
        for dev in PL_DEVICES:
            drv = sh(r, f"readlink -f /sys/bus/platform/devices/{dev}/driver 2>/dev/null").strip()
            if drv:
                sh(r, f"echo {dev} > {drv}/unbind")
        upload_bytes_via_ssh_cat(r, payload=fw, remote_path="/lib/firmware/mailbox_echo.bin")
        sh(r, "echo 0 > /sys/class/fpga_manager/fpga0/flags; echo mailbox_echo.bin > /sys/class/fpga_manager/fpga0/firmware")
        res["fpga_state"] = sh(r, "cat /sys/class/fpga_manager/fpga0/state").strip()
        ident = sh(r, f"devmem {a('id')}; devmem {a('version')}").split()
        res["checks"]["id_version"] = {"id": ident[0], "version": ident[1],
                                       "pass": ident[0].lower() == "0x4d424f58" and ident[1].lower() == "0x00010000"}
        print("ID/VERSION", ident, flush=True)

        hello = b"Hello from board A"
        h = send_and_read(r, 17, len(hello), hello)
        ok = h["seq"] == 17 and h["len"] == len(hello) and h["data"][:len(hello)] == hello and h["meta"] == 1
        res["checks"]["hello"] = {"rx_sequence": h["seq"], "rx_length": h["len"], "meta": h["meta"],
                                  "payload": h["data"][:h["len"]].decode(errors="replace"), "pass": ok,
                                  "status_before_ack": hex(h["status"]), "status_after_ack": hex(h["after_ack"])}
        print(f"TX sequence=17 bytes={len(hello)} payload=\"{hello.decode()}\"")
        print(f"RX sequence={h['seq']} bytes={h['len']} crc={'OK' if h['meta'] == 1 else 'BAD'} "
              f"payload=\"{h['data'][:h['len']].decode(errors='replace')}\"", flush=True)

        rng = random.Random(args.seed)
        bad = []
        for k in range(args.messages):
            n = rng.randint(0, 64)
            payload = bytes(rng.randrange(256) for _ in range(n))
            seq = rng.randrange(1 << 32)
            m = send_and_read(r, seq, n, payload)
            if not (m["seq"] == seq and m["len"] == n and m["data"][:n] == payload and m["meta"] == 1
                    and (m["after_ack"] & 0xC) == 0):
                bad.append({"k": k, "seq": seq, "len": n, "got": {kk: (vv.hex() if isinstance(vv, bytes) else vv)
                                                                   for kk, vv in m.items()}})
        res["checks"]["random_echo"] = {"messages": args.messages, "failures": len(bad), "first_failures": bad[:3],
                                        "pass": not bad}
        print(f"random echo: {args.messages - len(bad)}/{args.messages} intact", flush=True)

        m = send_and_read(r, 7, 80, b"x" * 64)
        res["checks"]["too_long"] = {"rx_length": m["len"], "meta": m["meta"], "pass": m["len"] == 64 and m["meta"] == 2}
        print("length 80 ->", m["len"], "meta", m["meta"], flush=True)

        first = send_and_read(r, 1001, 5, b"first", ack=False)
        second = send_and_read(r, 1002, 6, b"second", ack=True)
        ov = {"status_after_second": hex(second["status"]), "kept_sequence": second["seq"],
              "kept_payload": second["data"][:second["len"]].decode(errors="replace"),
              "status_after_ack": hex(second["after_ack"])}
        ov["pass"] = (second["status"] & 0x8) != 0 and second["seq"] == 1001 and (second["after_ack"] & 0xC) == 0
        res["checks"]["overflow"] = ov
        res["checks"]["overflow"]["first_status"] = hex(first["status"])
        print("overflow:", ov, flush=True)
    finally:
        if not args.no_reboot:
            L.start_detached(r, "sync; (sleep 1; reboot) > /dev/null 2>&1 &")
            r.client.close()
            res["rebooted"] = wait_ssh(args.host, 300)
            time.sleep(15)
            r2 = L.runner_for(args.host, "root", "analog", 22, 60.0)
            L.quiet_board(r2)
            sh(r2, f"echo 1 > {L.PHY}/out_altvoltage1_TX_LO_powerdown")
            res["after_reboot_iio"] = sh(r2, "cat /sys/bus/iio/devices/iio:device*/name").split()
            r2.client.close()
        else:
            r.client.close()
        res["all_pass"] = all(c.get("pass") for c in res["checks"].values())
        args.json_out.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
        print("all pass:", res["all_pass"], "| board back:", res.get("after_reboot_iio"))
    return 0 if res["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
