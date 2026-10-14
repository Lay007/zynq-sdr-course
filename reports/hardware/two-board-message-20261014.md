# A text message from board A to board B over the conducted RF path (#55, Lab 11.46), 2026-10-14

First two-board message on the course bench. Script:
`blocks/block_11_integrated_sdr_project/python/two_board_message.py`. Raw campaign:
[`two-board-message-campaign-20261014.json`](two-board-message-campaign-20261014.json).

## Path

```text
host -> board A: packet-v1 frame -> cyclic iio_writedev -> A TX1 -> 30 dB -> splitter -> B RX1
board B: fabric QPSK modem (Lab 11.45 mode) -> 288-bit decoded-bit register -> host: CRC-16, text
```

- **Board A (transmitter):** vendor image, TX -10 dB, 915 MHz, 3.84 MS/s.
- **Packet:** the host builds a Lab 11.46 packet-v1 frame (32 bytes: length, sequence, payload,
  CRC-16) and puts it as the 256-bit payload of a Lab 11.45 frame: the 48-bit course preamble plus
  the packet, differentially encoded, RRC-shaped. A replays it cyclically.
- **Board B (receiver):** image `3d492301`, RX 50 dB manual, mode `0x2D630` (Lab 11.45, DC blocker
  on). The fabric receiver locks on the preamble and decodes. Its BER counter still compares the
  payload with the ROM frame and therefore reports errors; what is used is the bridge's decoded-bit
  register (`gp_ctrl[16]`).
- **Register mapping:** a calibration with the ROM frame placed payload bit i (48..303) at register
  bit `2*(151 - i//2) + i%2`, with no rotation. All 256 payload bits matched in 6 of 6 bursts.
- **Decoding on the host:** the host reads the register over SSH, packs the 256 bits into the
  packet and checks the CRC. This is not the PS/PL mailbox path of the lab (that path is not on
  the board yet), and the text is printed by the host from board B's receiver output.

## First message

```text
TX sequence=17 bytes=18 payload="Hello from board A"
RX sequence=17 bytes=18 crc=OK payload="Hello from board A"
```

## Two problems found on the way

1. **Differential encoding across frame boundaries.** The waveform builder of the earlier labs
   encodes one frame and tiles it. That is seamless only if the frame's total phase increment is
   0 mod 4 quarter turns. It holds for the ROM frame and, by chance, for the plain
   "Hello from board A" packet, but a whitened packet advances by 2 quarters. Every frame boundary
   then carried a 180-degree jump, the first preamble dibit decoded wrong, and the 24-bit frame sync
   (one error allowed) never locked: 0 of 24.

   Fix: encode the whole cyclic buffer continuously, with the number of frames a multiple of 4.
   Checked offline: all 28 frames of the buffer, including the wrap, decode exactly.
2. **Long zero runs in the packet.** The 18-byte text is padded with zeros to 32 bytes, a run of 73
   zero bits. Differentially encoded it is a long run of one repeated symbol: a DC component and no
   symbol transitions. Errors clustered there and in the CRC right after it.

   Fix: PN9 whitening (x^9 + x^5 + 1) of the 256 packet bits, applied by the host on both ends.
   The longest zero run drops to 6.

24 receptions of "Hello from board A", delivered intact:

| | DC blocker on | DC blocker off |
|---|---:|---:|
| plain packet | 17 | 19 |
| whitened packet | **24** | **24** |

## Campaign

Ten messages (`"msg NN from A, seq 1NN"`, 22 bytes, sequences 100-109), whitened, DC blocker on, 20
receptions each:

| receptions | locked | delivered intact | CRC failed | CRC passed on a wrong message | PER |
|---:|---:|---:|---:|---:|---:|
| 200 | 196 | **189** | 7 | **0** | **5.5 %** (3.6 % of locked frames) |

Every failure was either a missed lock (4) or caught by the CRC (7); no corrupted message was
accepted.

## From the board consoles: `zmsg`

`blocks/block_11_integrated_sdr_project/sw/zmsg.c` does both ends on the boards themselves, which
have no Python. It is built with the Vitis `arm-linux-gnueabihf-gcc -static`.

- **`zmsg send` (board A)** builds the same frame as `two_board_message.py`: packet-v1, PN9,
  continuous differential encoding, RRC from the FPGA's own taps. Its output file is identical,
  sample for sample, to the Python waveform, and it takes 40 ms on the board. It then starts the
  cyclic `iio_writedev`.
- **`zmsg receive` (board B)** runs the fabric bursts through `/dev/mem`, reads the decoded-bit
  register, de-whitens and checks the CRC.

`tools/gen_zmsg_tables.py` writes the preamble and RRC tables into the C source from the FPGA's
`.mem` files, and `tests/test_zmsg_tables.py` checks that they stay equal.

One timing detail mattered. The receiver reports done at the end of the frame, but its sampler
still emits the 256-symbol margin (about 0.5 ms), and those symbols shift through the decoded-bit
register. Read immediately, the register gave 3 good packets out of 17. After waiting 5 ms it
gave 39 of 40. The Python tool never hit this, because each `devmem` call takes milliseconds.

```text
board-a$ ./zmsg send "Hello from board A" --seq 17
TX sequence=17 bytes=18 payload="Hello from board A"
board-b$ ./zmsg receive
RX sequence=17 bytes=18 crc=OK payload="Hello from board A"
```

Campaign from the consoles: ten messages (`"board console msg NN"`, 20 bytes, sequences 200-209),
`zmsg receive --count 20 --attempts 20` each. Raw data:
[`two-board-message-zmsg-campaign-20261014.json`](two-board-message-zmsg-campaign-20261014.json).

| receptions | locked | delivered intact | CRC failed | wrong message accepted | PER |
|---:|---:|---:|---:|---:|---:|
| 200 | 200 | **200** | 0 | 0 | **0** (95 % upper bound about 1.5 %) |

This is better than the host-driven campaign above (5.5 %), with the same RF settings and the same
frame format. The difference was not investigated.

## Limits

- One board pair, one RF setting (915 MHz, conducted, TX -10 / RX 50 dB), one session.
- The PS/PL mailbox of Lab 11.46 is not in this path. It passes its own echo test on board A
  (`tools/run_mailbox_board.py`) but does not feed the modem yet.
- The whitening is a host-side extension of packet-v1, not part of the RTL codec.
