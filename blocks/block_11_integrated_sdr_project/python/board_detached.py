#!/usr/bin/env python3
"""Run long board commands detached from the SSH session that started them.

A command that runs for many minutes over one SSH session dies with the session, and on the course
bench sessions between the PC and the boards were reset now and then (paramiko ConnectionResetError),
once only two seconds in, with the board's Ethernet link up. run_detached() writes the command into
a script on the board and starts it with nohup on a raw SSH channel; its output goes to a file on
the board. wait_detached() polls that file over short, fresh connections, retrying a reset one, and
returns the output when the command has finished.

The raw channel matters: ParamikoCommandRunner wraps commands in `sh -lc '...'` and reads the
channel to its end, which takes a backgrounded job down with it (see start_detached in
lab_11_30_two_board_cfo_validation).

    from board_detached import run_detached, wait_detached
    run_detached("192.168.20.1", "./zmbox listen --timeout 900", "rx")
    print(wait_detached("192.168.20.1", "rx", timeout_s=1000))
"""
from __future__ import annotations

import time

import lab_11_30_two_board_cfo_validation as L
from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat

DONE = "__DETACHED_DONE__"
USER, PASSWORD, PORT = "root", "analog", 22


def board_sh(host: str, command: str, timeout_s: float = 60.0, tries: int = 5) -> str:
    """Run a short command on a fresh connection; retry when the connection is reset."""
    for attempt in range(tries):
        try:
            r = L.runner_for(host, USER, PASSWORD, PORT, timeout_s)
            try:
                return L.sh(r, command)
            finally:
                r.client.close()
        except Exception as exc:  # noqa: BLE001 -- a reset connection: try again with a new one
            if attempt == tries - 1:
                raise
            print(f"[board_detached] {host}: {type(exc).__name__}, retry {attempt + 1}", flush=True)
            time.sleep(3)
    raise RuntimeError("unreachable")


def run_detached(host: str, command: str, tag: str, cwd: str = "/root") -> None:
    """Start `command` in `cwd` on the board, detached; its output goes to /tmp/det_<tag>.log."""
    script = f"cd {cwd} && ( {command} ) > /tmp/det_{tag}.log 2>&1; echo {DONE} >> /tmp/det_{tag}.log\n"
    board_sh(host, f"rm -f /tmp/det_{tag}.log /tmp/det_{tag}.sh")
    r = L.runner_for(host, USER, PASSWORD, PORT, 60.0)
    try:
        upload_bytes_via_ssh_cat(r, payload=script.encode(), remote_path=f"/tmp/det_{tag}.sh")
        L.start_detached(r, f"nohup sh /tmp/det_{tag}.sh > /dev/null 2>&1 &")
    finally:
        r.client.close()
    time.sleep(1.0)


def wait_detached(host: str, tag: str, timeout_s: float, poll_s: float = 10.0) -> str:
    """Wait until the detached command has finished; return its output."""
    t_end = time.time() + timeout_s
    while time.time() < t_end:
        out = board_sh(host, f"cat /tmp/det_{tag}.log 2>/dev/null")
        if DONE in out:
            return out.replace(DONE, "").rstrip()
        time.sleep(poll_s)
    raise TimeoutError(f"{host}: '{tag}' not finished after {timeout_s:.0f} s")
