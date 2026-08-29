# PS↔PL mailbox in Vivado: first hardware build

This page continues Lab 5.12 with the **smallest useful** Zynq hardware experiment. There is no AD936x datapath, QPSK, DMA, or interrupt yet. The only target is:

```text
Linux in PS
  ↓
M_AXI_GP0
  ↓
AXI SmartConnect / Interconnect
  ↓
zynq_message_mailbox_vivado_wrapper
  ↓
PL hardware echo
  ↓
the same AXI registers
  ↓
Linux in PS
```

Do not connect the radio modem until this boundary is understood and observable.

## Repository pieces

RTL:

```text
blocks/block_05_fpga_hdl_flow/rtl/
  zynq_message_mailbox_axi_lite.v
  zynq_message_mailbox_vivado_wrapper.v
```

The first file contains the mailbox and hardware echo. The wrapper fixes the Vivado-facing interface to:

- AXI4-Lite;
- 32-bit data;
- 32-bit address;
- one `s_axi_aclk`;
- synchronous active-low `s_axi_aresetn` inside the mailbox.

The wrapper includes `X_INTERFACE_INFO` / `X_INTERFACE_PARAMETER` metadata so Vivado can infer one `S_AXI` interface when the module is used as a Module Reference.

Software:

```text
tools/zynq_message_console.py
```

The same helper uses a mock backend on a normal computer and `/dev/mem` later on Zynq Linux.

## 1. Start from a known-good PS configuration

For the real board, **do not guess PS7 DDR/MIO settings**. Reuse the known-good board project or hardware handoff already used by the course.

Board materials live under:

```text
hardware/7020_ad936x_sdr/
```

The AD936x datapath itself is not needed for this first PS↔PL lab, but DDR, MIO, clocks and boot settings must still match the actual board.

## 2. Add RTL sources

Add:

```text
zynq_message_mailbox_axi_lite.v
zynq_message_mailbox_vivado_wrapper.v
```

Add `zynq_message_mailbox_vivado_wrapper` to the Block Design as a **Module Reference**.

Vivado should group the ports into one slave bus named `S_AXI`. If only individual AXI signals appear, fix interface inference first rather than treating dozens of manual wires as the normal learning path.

## 3. PS7 settings

Enable:

- `M_AXI_GP0`;
- `FCLK_CLK0`;
- `FCLK_RESET0_N` into the PL reset path.

A convenient first baseline is `FCLK_CLK0 = 100 MHz`. That frequency is not an algorithmic requirement. If the known-good board design uses another frequency, record it and keep the interface metadata consistent.

## 4. Clock and reset

Use one domain:

```text
PS7/FCLK_CLK0 ──────────────┬──────── SmartConnect/aclk
                            └──────── mailbox/s_axi_aclk

PS7/FCLK_RESET0_N
        ↓
Processor System Reset
        ↓ peripheral_aresetn
mailbox/s_axi_aresetn
```

There is deliberately **no CDC** in the first exercise. CDC should be introduced only when the design actually crosses clock domains.

## 5. AXI connection

Connect:

```text
PS7/M_AXI_GP0
      ↓
AXI SmartConnect (or AXI Interconnect)
      ↓
mailbox/S_AXI
```

Run `Validate Design`.

## 6. Address Editor

Assign a memory-mapped range to the mailbox and record:

```text
MAILBOX_BASE = 0x........
range        = ..........
```

Do **not** copy an address from course text. The actual Vivado Address Editor is the source of truth for the build.

The helper then accesses offsets `0x00…0xAC` relative to that base.

## 7. Build evidence

Record at least:

- Block Design screenshot;
- Address Editor screenshot;
- bitstream/build identity;
- AXI clock frequency;
- physical base address;
- bitstream loading method;
- successful Linux boot.

Until the design is exercised on a board, Icarus/CI only prove RTL semantics.

## 8. Linux probe

Copy `tools/zynq_message_console.py` to the board and start with identity only:

```bash
sudo python3 tools/zynq_message_console.py \
  --base <MAILBOX_BASE> probe
```

Expected:

```text
id=0x4d424f58 version=0x00010000
```

If the ID is wrong, stop and check the loaded bitstream, physical address, GP0 enable, clock/reset, and hardware/Linux handoff before trying a message.

## 9. First real PS→PL→PS message

After a successful probe:

```bash
sudo python3 tools/zynq_message_console.py \
  --base <MAILBOX_BASE> demo "Hello PL" --sequence 1
```

Expected idea:

```text
TX sequence=1 bytes=8 payload="Hello PL"
RX sequence=1 bytes=8 crc=OK payload="Hello PL"
```

At this stage `crc=OK` means only that the **hardware echo contract** produced an integrity-good RX snapshot. It is not yet a radio-packet CRC result and not RF evidence.

## 10. Questions after PASS

A student should be able to explain:

1. Why does Python run in PS while the mailbox state machine runs in PL?
2. Why is `MAILBOX_BASE` a physical address while `0x70` is an IP-relative RX offset?
3. Why is SmartConnect/Interconnect present?
4. What does `M_AXI_GP0` mean in terms of master/slave direction?
5. Why is there no CDC in this baseline?
6. Why is hardware echo useful before QPSK integration?

## Next course step

Only after the hardware echo works, replace:

```text
TX mailbox → echo → RX mailbox
```

with:

```text
TX mailbox
→ 32-byte packet bridge
→ existing QPSK modem
→ packet recovery
→ RX mailbox
```

The PS helper and user interaction should remain almost unchanged. That is the practical value of a clean PS/PL partition.
