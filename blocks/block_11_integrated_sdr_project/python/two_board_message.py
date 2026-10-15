#!/usr/bin/env python3
"""Issue #55 / Lab 11.46 stage 4: a text message from board A to board B over the conducted RF path.

    board A TX1 -> attenuators -> board B RX1

Board A transmits one packet-v1 frame (Lab 11.46: length, sequence, payload, CRC-16 in 32 bytes)
in the Lab 11.45 frame: the 48-bit course preamble, then the 256 packet bits, differentially
encoded, RRC-shaped, replayed cyclically by `iio_writedev`. Board B receives it with its fabric
QPSK modem in the Lab 11.45 mode. The receiver's own BER counter still compares the payload with
the ROM frame (so it reports errors); what matters is the recovered bit stream, which the bridge
keeps in its 288-bit decoded-bit register (gp_ctrl[16]). For this 152-symbol differential frame the
calibration run put payload bit i (48..303) at register bit 2*(151 - i//2) + i%2, with no rotation,
and matched the ROM payload in 6 of 6 bursts. The 256 bits are packed into the packet and decoded
(CRC-16) on the host PC.

    python two_board_message.py send "Hello from board A" --sequence 17
    python two_board_message.py campaign --messages 10 --receptions 20
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

import lab_11_30_two_board_cfo_validation as L
import lab_11_32_two_board_fabric_coarse_cfo as B
from decoded_bit_readout import read_decoded
from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat
from lab_11_27_runtime_qpsk_digital_loopback import qpsk_ber_once
from qpsk_packet_v1 import PACKET_SIZE, decode_packet, encode_packet
from two_board_agc_ber import MODE

PHY = L.PHY
BASE = 0x79040000
SYMS = B.LONG_FRAME_SYMBOLS          # 152
PRE = B.LONG_PREAMBLE_BITS           # 48


def pn9(n: int, seed: int = 0x1FF) -> np.ndarray:
    """PN9 whitening sequence (x^9 + x^5 + 1), the same on both ends."""
    s, out = seed, []
    for _ in range(n):
        out.append(s & 1)
        s = ((s << 1) | (((s >> 8) ^ (s >> 4)) & 1)) & 0x1FF
    return np.array(out, dtype=np.uint8)


WHITEN = pn9(PACKET_SIZE * 8)


def frame_iq(packet: bytes, n_frames: int = 28, whiten: bool = False) -> np.ndarray:
    """int16 IQ of n_frames Lab 11.45 frames carrying `packet`, replayed cyclically.

    The differential encoding runs over the whole buffer, not frame by frame. Encoding one frame
    and tiling it (as make_long_preamble_frame does) is seamless only if the frame's total phase
    increment is 0 mod 4 quarter turns. That holds for the ROM frame, but not for an arbitrary
    payload: a PN9-whitened packet advances by 2 quarters, so every frame boundary carried a
    180-degree jump, the first preamble dibit decoded wrong and the 24-bit frame sync (1 error
    allowed) never locked. With continuous encoding and n_frames a multiple of 4, the wrap of the
    buffer itself is seamless too (four equal increments make a full turn).
    """
    if len(packet) != PACKET_SIZE:
        raise ValueError("packet-v1 frames are 32 bytes")
    if n_frames % 4:
        raise ValueError("n_frames must be a multiple of 4 for a seamless cyclic buffer")
    payload = np.unpackbits(np.frombuffer(packet, dtype=np.uint8), bitorder="little")
    if whiten:
        payload = payload ^ WHITEN
    bits = np.concatenate([B.long_frame_bits()[:PRE], payload])
    fb = B.diff_encode_bits(np.tile(bits, n_frames))
    sym = ((1.0 - 2.0 * fb[0::2]) + 1j * (1.0 - 2.0 * fb[1::2])) / np.sqrt(2.0)
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


def once_iq(packet: bytes, whiten: bool = False, lead: int = 64, pad_head: int = 8, pad_tail: int = 256) -> np.ndarray:
    """int16 IQ of one Lab 11.45 frame carrying `packet`, for sending once (zmsg send --once).

    pad_head silent symbols, `lead` training symbols alternating between phase states 0 and 2
    (ending in 2), one reference symbol in state 0 (the differential encoder's starting state), the
    frame, pad_tail silent symbols; linear (not circular) RRC. Why the lead-in and the reference:
    Lab 11.48. zmsg.c builds the same buffer; tests/test_zmsg_once.py compares the two models.
    """
    if len(packet) != PACKET_SIZE:
        raise ValueError("packet-v1 frames are 32 bytes")
    payload = np.unpackbits(np.frombuffer(packet, dtype=np.uint8), bitorder="little")
    if whiten:
        payload = payload ^ WHITEN
    fb = B.diff_encode_bits(np.concatenate([B.long_frame_bits()[:PRE], payload]))
    s0 = (1 + 1j) / np.sqrt(2.0)
    frame = ((1.0 - 2.0 * fb[0::2]) + 1j * (1.0 - 2.0 * fb[1::2])) / np.sqrt(2.0)
    train = np.array([-s0 if (lead - k) % 2 else s0 for k in range(lead)], dtype=complex)
    sym = np.concatenate([np.zeros(pad_head, complex), train, [s0], frame, np.zeros(pad_tail, complex)])
    up = np.zeros(len(sym) * L.SPS, dtype=complex)
    up[:: L.SPS] = sym
    wave = np.convolve(up, L.load_rrc_taps())[: len(up)]
    wave = wave * (0.70 * 32767 / np.max(np.abs(wave)))
    iq = np.zeros(len(wave) * 2, dtype=np.int16)
    iq[0::2] = np.round(wave.real).astype(np.int16)
    iq[1::2] = np.round(wave.imag).astype(np.int16)
    return iq


def a_transmit(ra, packet: bytes, carrier: float, tx_gain: float, whiten: bool = False) -> None:
    iq = frame_iq(packet, whiten=whiten)
    n = len(iq) // 2
    L.sh(ra, "for p in $(ps | grep '[i]io_writedev' | awk '{print $1}'); do kill -9 $p; done")
    L.reset_tx_dma(ra)
    upload_bytes_via_ssh_cat(ra, payload=iq.tobytes(), remote_path="/tmp/msg.bin")
    L.sh(ra, f"echo {int(L.SAMPLE_RATE)} > {PHY}/out_voltage_sampling_frequency; "
             f"echo {int(carrier)} > {PHY}/out_altvoltage1_TX_LO_frequency; "
             f"echo {tx_gain:.2f} > {PHY}/out_voltage0_hardwaregain; echo 0 > {PHY}/out_altvoltage1_TX_LO_powerdown")
    L.start_detached(ra, f"nohup iio_writedev -c -b {n} -s {n} cf-ad9361-dds-core-lpc voltage0 voltage1 "
                         "< /tmp/msg.bin > /tmp/msg.log 2>&1 &")
    time.sleep(2.0)
    if L.sh(ra, f"devmem {L.DAC_CHAN_CNTRL_7_CH0}").strip() not in ("0x00000002", "0x2"):
        raise RuntimeError("board A transmitter not on DMA")


def b_setup(rb, carrier: float, rx_gain: int) -> None:
    L.quiet_board(rb)
    L.sh(rb, f"echo {int(L.SAMPLE_RATE)} > {PHY}/in_voltage_sampling_frequency; "
             f"echo {int(carrier)} > {PHY}/out_altvoltage0_RX_LO_frequency; "
             f"echo manual > {PHY}/in_voltage0_gain_control_mode; echo {rx_gain} > {PHY}/in_voltage0_hardwaregain")


def b_receive(rb, offset: int, mode: int = MODE, whiten: bool = False) -> dict:
    """One reception on board B: fabric burst, then the 256 payload bits from the register."""
    row = qpsk_ber_once(rb, BASE, SYMS, offset, mode_bits=mode, preamble_bits=PRE)
    if row.get("received_symbols") != SYMS:
        return {"locked": False}
    value, _ = read_decoded(rb, mode)
    bits = np.array([(value >> (2 * (SYMS - 1 - (i >> 1)) + (i & 1))) & 1 for i in range(PRE, 2 * SYMS)], dtype=np.uint8)
    if whiten:
        bits = bits ^ WHITEN
    packet = np.packbits(bits, bitorder="little").tobytes()
    d = decode_packet(packet)
    text = None
    if d.crc_ok and not d.frame_error:
        try:
            text = d.payload.decode("utf-8")
        except UnicodeDecodeError:
            text = None
    return {"locked": True, "sequence": d.sequence, "crc_ok": bool(d.crc_ok), "frame_error": bool(d.frame_error),
            "length": packet[0], "payload": text}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("send")
    s.add_argument("message")
    s.add_argument("--sequence", type=int, default=0)
    s.add_argument("--receptions", type=int, default=5)
    c = sub.add_parser("campaign")
    c.add_argument("--messages", type=int, default=10)
    c.add_argument("--receptions", type=int, default=20)
    for p in (s, c):
        p.add_argument("--carrier", type=float, default=915e6)
        p.add_argument("--tx-gain", type=float, default=-10.0)
        p.add_argument("--rx-gain", type=int, default=50)
        p.add_argument("--json-out", type=Path, default=None)
        p.add_argument("--whiten", action="store_true", help="PN9-whiten the packet bits (both ends)")
        p.add_argument("--no-dc-blocker", action="store_true", help="receiver mode without bit 0x200")
    args = ap.parse_args()

    if args.cmd == "send":
        plan = [(args.sequence, args.message)]
    else:
        plan = [(100 + k, f"msg {k:02d} from A, seq {100 + k}") for k in range(args.messages)]
    ra = L.runner_for("192.168.40.1", "root", "analog", 22, 30.0)
    rb = L.runner_for("192.168.20.1", "root", "analog", 22, 40.0)
    mode = MODE & ~0x200 if args.no_dc_blocker else MODE
    res = {"issue": 55, "whiten": args.whiten, "carrier_hz": args.carrier, "tx_gain_db": args.tx_gain, "rx_gain_db": args.rx_gain,
           "mode_bits": hex(mode), "frame_symbols": SYMS, "preamble_bits": PRE, "messages": []}
    try:
        b_setup(rb, args.carrier, args.rx_gain)
        for seq, text in plan:
            packet = encode_packet(text.encode("utf-8"), seq)
            a_transmit(ra, packet, args.carrier, args.tx_gain, args.whiten)
            print(f"TX sequence={seq} bytes={len(text.encode())} payload=\"{text}\"", flush=True)
            rx = [b_receive(rb, k % 8, mode, args.whiten) for k in range(args.receptions)]
            ok = [r for r in rx if r.get("crc_ok") and r.get("sequence") == seq and r.get("payload") == text]
            for r in rx[:1] + [r for r in rx if r.get("locked") and not r.get("crc_ok")][:2]:
                if r.get("locked"):
                    print(f"RX sequence={r['sequence']} bytes={r['length']} crc={'OK' if r['crc_ok'] else 'BAD'} "
                          f"payload=\"{r['payload']}\"", flush=True)
            res["messages"].append({"sequence": seq, "text": text, "receptions": len(rx),
                                    "locked": sum(r.get("locked", False) for r in rx), "crc_ok_and_match": len(ok),
                                    "crc_bad": sum(1 for r in rx if r.get("locked") and not r.get("crc_ok"))})
            print(f"   {len(ok)}/{len(rx)} receptions delivered the message intact "
                  f"({res['messages'][-1]['locked']} locked)", flush=True)
    finally:
        L.sh(ra, "for p in $(ps | grep '[i]io_writedev' | awk '{print $1}'); do kill -9 $p; done")
        L.quiet_board(ra)
        L.sh(ra, f"echo 1 > {PHY}/out_altvoltage1_TX_LO_powerdown")
        L.quiet_board(rb)
        ra.client.close()
        rb.client.close()
    tot = sum(m["receptions"] for m in res["messages"])
    good = sum(m["crc_ok_and_match"] for m in res["messages"])
    locked = sum(m["locked"] for m in res["messages"])
    res["summary"] = {"receptions": tot, "locked": locked, "delivered": good,
                      "per_all": round(1 - good / tot, 4) if tot else None,
                      "per_locked": round(1 - good / locked, 4) if locked else None}
    print(json.dumps(res["summary"]))
    if args.json_out:
        args.json_out.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
