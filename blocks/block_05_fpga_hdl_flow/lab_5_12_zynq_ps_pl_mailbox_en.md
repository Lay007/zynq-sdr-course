# Lab 5.12 — PS↔PL message mailbox: the first meaningful Zynq bridge

## Goal

Understand the Zynq architecture through a small observable transaction instead of a large Vivado block design:

```text
Linux/Python in PS
      ↓ memory-mapped AXI-Lite
64-byte TX/RX mailbox in PL
      ↓
simple PL operation / future modem datapath
```

After this lab a student should be able to explain:

1. which code runs on the ARM processor;
2. which logic is implemented in FPGA fabric;
3. how PS sees PL registers in the memory map;
4. why the control plane and the sample datapath use different interfaces.

Read [Zynq: where PS ends and PL begins](/zynq-sdr-course/zynq-ps-pl-architecture/) first.

## Why there is no DMA yet

DMA comes later. The first message is limited to **64 bytes** and lives directly in AXI-Lite registers. This is not a high-performance architecture, but every step stays visible:

```text
byte → 32-bit register → AXI write → PL state → AXI read → byte
```

Once this path is understood, BRAM, AXI4-Stream, DMA and interrupts have a clear purpose.

## Educational mailbox contract

### Identification and control

| Offset | Register | Access | Meaning |
|---:|---|---|---|
| `0x00` | `ID` | RO | `0x4D424F58` = `MBOX` |
| `0x04` | `VERSION` | RO | `0x00010000` |
| `0x08` | `CONTROL` | WO/W1P | bit0 `TX_START`, bit1 `RX_ACK` |
| `0x0C` | `STATUS` | RO | bit0 `TX_BUSY`, bit1 `TX_DONE`, bit2 `RX_VALID`, bit3 `RX_OVERFLOW` |

### TX mailbox

| Offset | Register | Access | Meaning |
|---:|---|---|---|
| `0x10` | `TX_SEQUENCE` | RW | packet sequence number |
| `0x14` | `TX_LENGTH` | RW | payload length, `0…64` bytes |
| `0x20…0x5C` | `TX_DATA[0…15]` | RW | 64 payload bytes, little-endian packed into 16 words |

### RX mailbox

| Offset | Register | Access | Meaning |
|---:|---|---|---|
| `0x60` | `RX_SEQUENCE` | RO | received sequence number |
| `0x64` | `RX_LENGTH` | RO | received payload length |
| `0x68` | `RX_META` | RO | bit0 `CRC_OK`, bit1 `FRAME_ERROR` |
| `0x70…0xAC` | `RX_DATA[0…15]` | RO | received payload |

### Critical RX contract

While `RX_VALID=1`, PL must keep `RX_SEQUENCE`, `RX_LENGTH`, `RX_META`, and `RX_DATA` stable until PS issues `RX_ACK`.

That makes a multiword software read coherent without a complicated snapshot protocol.

If a new packet arrives while the mailbox is occupied, the first implementation keeps the old packet and sets `RX_OVERFLOW`.

## Byte packing

The string `ABCD` is four ASCII bytes:

```text
41 42 43 44
```

and appears in `TX_DATA[0]` as the little-endian word:

```text
0x44434241
```

This gives the course a concrete place to discuss endianness on a real PS/PL interface.

## Part A — run without hardware

Use:

```bash
python tools/zynq_message_console.py --mock demo "Hello Zynq" --sequence 17
```

The mock backend models the register protocol, not RF. The intended output is:

```text
TX sequence=17 bytes=10 payload="Hello Zynq"
RX sequence=17 bytes=10 crc=OK payload="Hello Zynq"
```

The goal is to understand the software-visible contract before opening Vivado.

## Part B — first hardware implementation

Minimal Vivado design:

```text
Zynq7 Processing System
        |
   M_AXI_GP0
        |
AXI Interconnect / SmartConnect
        |
PS/PL mailbox AXI-Lite IP
```

Requirements:

- one AXI clock domain for the first experiment;
- reset through the standard processor-system-reset structure;
- mailbox address assigned in Vivado Address Editor;
- the physical address is recorded from the actual build, not copied blindly from course text.

For the first board test, PL can implement a hardware echo: `TX_START` copies the TX mailbox to RX and raises `RX_VALID`.

That proves:

```text
PS → AXI → PL → AXI → PS
```

without RF or DSP.

### Concrete Vivado procedure (prepared, not executed in this repository)

The RTL side of this step is already committed and CI-tested (`zynq_message_mailbox_axi_lite.v`, `zynq_message_mailbox_vivado_wrapper.v`, `tb_zynq_message_mailbox_axi_lite.sv`, workflow `block5_ps_pl_mailbox.yml`). Building this into a Zynq Block Design still requires Vivado itself, which is not available in every development environment (it was not available when this section was written). The steps below are the exact, reviewable procedure to run when it is -- a recipe, not a report of results already obtained.

```tcl
# 1. Create a new BD in an existing Zynq-7020 project (or the course project).
create_bd_design "mailbox_echo_bd"

# 2. Add the Zynq7 Processing System and run block automation
#    (enables one AXI clock, applies the standard processor-system-reset IP).
create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 processing_system7_0
apply_bd_automation -rule xilinx.com:bd_rule:processing_system7 \
    -config {make_external "FIXED_IO, DDR" apply_board_preset "1"} \
    [get_bd_cells processing_system7_0]

# 3. Add the mailbox as a Verilog module reference (not a packaged IP -- this
#    is the same zynq_message_mailbox_vivado_wrapper.v that iverilog already
#    elaborates in CI, so there is no separate hardware-only RTL to trust).
create_bd_cell -type module -reference zynq_message_mailbox_vivado_wrapper mailbox_0

# 4. Connect M_AXI_GP0 to the mailbox's S_AXI through automation, which also
#    inserts the AXI Interconnect/SmartConnect and wires clock/reset.
apply_bd_automation -rule xilinx.com:bd_rule:axi4 \
    -config {Master "/processing_system7_0/M_AXI_GP0" Clk "Auto"} \
    [get_bd_intf_pins mailbox_0/S_AXI]

# 5. Validate the design before assigning addresses.
validate_bd_design

# 6. Let Vivado assign the base address (do not hand-pick one); a 4K range
#    covers the 0x00-0xAC register map with headroom for the RX_DATA words.
assign_bd_address [get_bd_addr_segs mailbox_0/S_AXI/reg0]
set_property range 4K [get_bd_addr_segs {processing_system7_0/Data/SEG_mailbox_0_reg0}]

# 7. Generate the wrapper, run synthesis/implementation, export the bitstream
#    and XSA, then read the *actual* assigned address back out for the report:
report_property [get_bd_addr_segs] -class {} | grep -i offset
```

Record whatever address step 7 actually reports -- do not reuse the address from a previous board, a previous synthesis run, or this text. The register map, byte widths and RX-hold-until-ACK contract above are the part that is fixed; the base address is a build-time fact.

Do not fabricate a "physical base address" without running this. A `TBD` in the lab report is an honest and acceptable state until the build above has actually produced one.

## Part C — move to the radio link

After the hardware echo, the software API stays unchanged. Only the PL path between TX and RX changes:

```text
TX mailbox
   ↓
packet serializer / framing
   ↓
existing QPSK TX datapath
   ↓ RF
existing QPSK RX datapath
   ↓
packet recovery
   ↓
RX mailbox
```

The educational point is that **the PS console application stays the same while the PL datapath becomes a real modem**.

## Checks

- [ ] explain PS and PL in your own words;
- [ ] read `ID=MBOX`;
- [ ] show the physical base address from Vivado;
- [ ] transfer 1-, 4-, and 64-byte messages;
- [ ] show little-endian packing for at least one word;
- [ ] show that `RX_VALID` keeps data stable until `RX_ACK`;
- [ ] explain why 65 bytes are rejected;
- [ ] state explicitly that this AXI-Lite mailbox is not an IQ sample stream.

## Report questions

1. Why should mapper/RRC stay in PL while `printf()` stays in PS?
2. Why is AXI-Lite unsuitable for continuous IQ data?
3. What fails if PL rewrites RX data while PS is reading it?
4. Why is `RX_ACK` needed?
5. When does DMA become justified?

## Completion criterion

Minimum educational PASS:

```text
PS software → AXI-Lite mailbox → PL echo → AXI-Lite mailbox → PS console
```

The next course stage replaces `PL echo` with the two-board QPSK path while preserving the same user story: **type a message on one board and see it on the other**.
