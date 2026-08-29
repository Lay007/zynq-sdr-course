# Lab 11.46 — A message from one Zynq console to another

## Idea

This is not another BER lab. It is the user-visible capstone of the main educational path:

```text
board A console
    ↓
PS A
    ↓ AXI-Lite mailbox
PL A: packet source → existing QPSK TX
    ↓
AD936x A
    ↓ RF / cable
AD936x B
    ↓
PL B: existing QPSK RX → packet recovery
    ↓ AXI-Lite mailbox
PS B
    ↓
board B console
```

The learner types text on the first board and sees **the same text** on the second.

## Why this matters more than another DSP primitive

By this point the course already contains mapper/RRC work, synchronization, CFO/timing, BER and two-board measurements. Without user data, however, those results can still feel like separate experiments.

Lab 11.46 turns them into one system:

- PS owns the user interface and packet-level software;
- PL owns the deterministic bit/symbol/sample datapath;
- AXI is the concrete boundary between them;
- AD936x transports a meaningful message instead of only a test pattern.

## Prerequisites

Before this lab, understand:

1. [Zynq: where PS ends and PL begins](../../zynq-ps-pl-architecture.md);
2. [Lab 5.12 — PS↔PL message mailbox](lab-5-12-zynq-ps-pl-mailbox.md);
3. the existing two-board QPSK path and the Lab 11.45 result.

## What is reused

Do not build a new PHY. Reuse the proven Block 11 path:

```text
QPSK mapper
→ RRC TX
→ AD936x
→ RX matched filter / timing / carrier recovery
→ frame synchronization
→ recovered bits
```

The new work belongs **before the mapper and after recovered bits**:

```text
PS message bytes → packet serializer → [existing modem] → packet decoder → PS message bytes
```

## Baseline size limit

The existing working frame provides **256 payload bits = 32 bytes**. Therefore the first radio version accepts one fixed 32-byte packet payload.

The 64-byte PS/PL mailbox remains useful, but v1 of the radio bridge intentionally uses a single existing QPSK payload. Longer messages can be fragmented later.

## Packet payload v1

Use the existing 32 payload bytes as:

```text
byte 0      : application length N, 0…27
bytes 1..2  : sequence, uint16 little-endian
bytes 3..29 : UTF-8/application bytes, zero padded
bytes 30..31: CRC-16/CCITT over bytes 0..29
```

The maximum user message in v1 is therefore **27 bytes**.

For the first implementation, packet assembly and CRC belong in **PS**. PL receives a fixed 32-byte payload and transports it deterministically as bits/symbols/samples. On RX, PS verifies CRC and prints the message.

That choice is deliberately educational: it demonstrates a real PS/PL partition instead of moving the entire application into FPGA fabric.

## Stage 1 — software contract without RF

Run:

```bash
python tools/zynq_message_console.py --mock demo "Hello Zynq" --sequence 17
```

This is not RF simulation. It validates only the software-visible mailbox contract.

## Stage 2 — one-board PS↔PL hardware echo

Implement the AXI-Lite mailbox and prove:

```text
Linux PS → AXI-Lite → PL echo → AXI-Lite → Linux PS
```

The physical address must come from the actual Vivado Address Editor map.

## Stage 3 — digital modem loopback

Replace the PL echo with the packet serializer plus the existing QPSK digital loopback:

```text
PS → mailbox → packet bytes → QPSK TX → digital loopback → QPSK RX → mailbox → PS
```

RF is still absent, but the real modem datapath now carries application bytes.

## Stage 4 — two boards

Start with a safe conducted connection and the required attenuation; move to OTA only when appropriate.

Board A:

```text
board-a$ sudo python3 tools/zynq_message_console.py --base <addr> send \
  "Hello from board A" --sequence 17
TX sequence=17 bytes=18 payload="Hello from board A"
```

Board B:

```text
board-b$ sudo python3 tools/zynq_message_console.py --base <addr> receive --wait 10
RX sequence=17 bytes=18 crc=OK payload="Hello from board A"
```

That is the primary acceptance criterion.

## Record in the report

- bitstream/build identity on both boards;
- mailbox physical base address;
- RF frequency, sample rate, attenuation and gains;
- transmitted string and UTF-8 byte length;
- sequence number;
- RX CRC result;
- number of repetitions;
- packet success rate;
- on failure, the raw 32-byte packet or a hex dump.

## Minimum campaign

After the first successful message, run at least 100 short transmissions and record:

```text
packets sent
packets received
CRC OK
CRC failed / timeout
PER
```

BER from the modem evidence remains useful, but **PER / successful message delivery** becomes the user-facing metric.

## Do not add before the first PASS

Do not simultaneously add DMA, interrupts, fragmentation, encryption, OFDM, LoRa, or an Ethernet bridge.

First prove the simplest visible chain:

```text
text → PS → PL → RF → PL → PS → text
```

## Completion criterion

The lab is complete only with **two-board hardware evidence**:

1. transmit command on Board A;
2. received string on Board B;
3. matching sequence;
4. `CRC=OK`;
5. documented RF settings;
6. a short repeated campaign with measured PER.

Mock, RTL and digital-loopback results remain intermediate evidence until the two-board message has actually crossed the radio path.
