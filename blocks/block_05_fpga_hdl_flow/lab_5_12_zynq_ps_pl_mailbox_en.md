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

### Concrete Vivado procedure (built with Vivado 2021.1; not loaded on a board)

The RTL side of this step is committed and CI-tested (`zynq_message_mailbox_axi_lite.v`, `zynq_message_mailbox_vivado_wrapper.v`, `tb_zynq_message_mailbox_axi_lite.sv`, workflow `block5_ps_pl_mailbox.yml`). The Block Design procedure below was executed end to end on 2026-09-24 with Vivado 2021.1, through bitstream and XSA, by one command:

```bash
python tools/build_block5_mailbox_bd.py --build-dir C:/tmp/mb
```

The script reads the course board's own PS7 settings (all 876 `PCW_*` parameters: DDR, MIO, peripherals) from its known-good hardware handoff `hardware/7020_ad936x_sdr/ps/bringup_tests/design_1_wrapper.xsa`, so DDR and MIO are not guessed, then runs `tools/vivado_block5_mailbox_bd.tcl`. Keep the build directory short: Vivado warns above 80 characters, and IP generation fails near the 260-character Windows path limit.

```tcl
# 1. New BD in a project for xc7z020clg400-2.
create_bd_design "mailbox_echo_bd"

# 2. Zynq PS. The course board has no Vivado board file, so do not apply a board
#    preset; apply the board's own PCW_* settings instead (the script does this).
create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 processing_system7_0
apply_bd_automation -rule xilinx.com:bd_rule:processing_system7 \
    -config {make_external "FIXED_IO, DDR" apply_board_preset "0"} \
    [get_bd_cells processing_system7_0]
#    ... set_property CONFIG.<PCW_*> for every board parameter, then enable what
#    this lab needs on top (the board image has M_AXI_GP0 off and FCLK0 at 50 MHz):
set_property -dict [list CONFIG.PCW_USE_M_AXI_GP0 {1} CONFIG.PCW_EN_CLK0_PORT {1} \
    CONFIG.PCW_EN_RST0_PORT {1} CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ {100}] \
    [get_bd_cells processing_system7_0]

# 3. The mailbox as a Verilog module reference (the same wrapper iverilog
#    elaborates in CI).
create_bd_cell -type module -reference zynq_message_mailbox_vivado_wrapper mailbox_0

# 4. M_AXI_GP0 -> interconnect -> mailbox S_AXI; automation adds the
#    interconnect and the processor-system-reset block.
apply_bd_automation -rule xilinx.com:bd_rule:axi4 \
    -config {Master "/processing_system7_0/M_AXI_GP0" Clk "Auto"} \
    [get_bd_intf_pins mailbox_0/S_AXI]

# 5-6. Let Vivado assign the address, restrict it to 4K (0x00-0xAC register map),
#      then validate.
assign_bd_address
set_property range 4K [get_bd_addr_segs {processing_system7_0/Data/SEG_mailbox_0_reg0}]
validate_bd_design

# 7. Read the assigned address back (Tcl has no pipes, so no `| grep`):
set seg [get_bd_addr_segs -of_objects [get_bd_addr_spaces processing_system7_0/Data]]
puts "[get_property OFFSET $seg] [get_property RANGE $seg]"
#    then make_wrapper, launch_runs impl_1 -to_step write_bitstream -jobs 1,
#    write_hw_platform -fixed -include_bit.
```

Result of that build (normalized reports in [`reports/fpga/block5_mailbox_bd_raw`](https://github.com/Lay007/zynq-sdr-course/tree/main/reports/fpga/block5_mailbox_bd_raw)):

| Item | Value |
|---|---|
| Mailbox segment | `SEG_mailbox_0_reg0`, offset `0x40000000`, range `0x1000` (4 KB) |
| FCLK_CLK0 | 100.000 MHz |
| Timing at 100 MHz | WNS +3.508 ns, 0 failing endpoints |
| Utilization | 1060 LUT, 1844 FF, 0 BRAM, 0 DSP (mailbox 636 LUT / 1265 FF, AXI interconnect 407 LUT) |
| DRC | 0 violations |
| Outputs | bitstream and XSA (not committed, not loaded on a board) |

What executing the recipe found:

- **Without step 6 the mailbox gets the whole 1 GB `M_AXI_GP0` window** (range `0x40000000`). The 4K restriction is not cosmetic.
- `apply_board_preset "1"` needs a Vivado board file, which this board does not have; the board's settings must come from its own hardware handoff.
- The board's reference image has `M_AXI_GP0` disabled and `FCLK_CLK0` at 50 MHz, so they must be enabled on top of the board settings.
- 10 of the 876 board parameters are read-only derived values (the `*_FREQMHZ` bus clocks and `PCW_NUM_F2P_INTR_INPUTS`); Vivado rejects them with a CRITICAL WARNING, which is expected.
- With four parallel jobs on a 16 GB machine the IP syntheses ran out of memory; one job at a time completes.

`0x40000000` is simply the start of the `M_AXI_GP0` window, which is why Vivado picked it. It is still a build-time fact: record the address your own build reports, not this one.

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
