# CSS accelerator AXI integration

[Русская версия](https://lay007.github.io/zynq-sdr-course/ru/blocks/css_axi_integration_ru/)

The course CSS detector now has a shared-clock PS/PL integration boundary:

```text
AXI4-Stream 32-bit Q:I samples
  -> css_sf7_axis_detector
  -> css_sf7_sequential_detector
  -> one AXI4-Stream 256-bit decision packet
                         |
                         +-> AXI4-Lite status/result snapshot + IRQ
```

`css_sf7_axi_accelerator.v` is the integration top level. All AXI interfaces
use `aclk` and active-low synchronous `aresetn`; clock-domain crossing belongs
outside this module.

The [Vivado AXI implementation report](https://github.com/Lay007/zynq-sdr-course/blob/main/reports/fpga/block8-css-axi-evidence.md)
records fully routed 100 MHz OOC evidence for this top level.

## Stream contract

The input transfer condition is `s_axis_tvalid && s_axis_tready`.
`s_axis_tdata[15:0]` is signed Q1.15 I and `[31:16]` is signed Q1.15 Q. Exactly
128 accepted beats form one symbol. `s_axis_tlast` must be asserted only on beat
127. A mismatch sets the result's frame-error bit but does not change the fixed
128-beat grouping or resynchronize the stream.

The accelerator emits one result beat per symbol and holds `m_axis_tvalid`,
`m_axis_tdata`, and `m_axis_tlast` until `m_axis_tready` accepts it. No next
symbol is accepted while an unconsumed result is pending.

| Result bits | Meaning |
|---|---|
| `[6:0]` | peak bin |
| `[7]` | reserved, zero |
| `[14:8]` | second bin |
| `[15]` | input TLAST/frame error |
| `[31:16]` | dechirp saturation count |
| `[95:32]` | peak magnitude squared |
| `[159:96]` | second magnitude squared |
| `[255:160]` | reserved, zero |

The one-beat result packet always asserts `m_axis_tlast`.

## AXI-Lite register map

All registers are 32 bits. Undefined addresses read as zero and writes to them
have no effect.

| Offset | Name | Access | Meaning |
|---:|---|---|---|
| `0x00` | `ID` | RO | `0x43535337` (`CSS7`) |
| `0x04` | `VERSION` | RO | `0x00010000` |
| `0x08` | `CONTROL` | RW/W1P | bit 0 IRQ enable; bits 8/9 clear done/frame-error sticky flags; bit 10 clears counters |
| `0x0C` | `STATUS` | RO | bits 0–4: busy, input ready, result pending, done sticky, frame-error sticky |
| `0x10`–`0x2C` | `RESULT0`–`RESULT7` | RO | last 256-bit result, least-significant word first |
| `0x30` | `COMPLETED_COUNT` | RO | completed result count |
| `0x34` | `FRAME_ERROR_COUNT` | RO | results with TLAST mismatch |

`irq` is asserted while both IRQ enable and done sticky are set. A new result
wins over a simultaneous software clear, so an event is not lost.

## Verification

Run Icarus inside WSL:

```bash
python3 tools/run_block8_css_rtl.py --test tb_css_sf7_axis_detector
python3 tools/run_block8_css_rtl.py --test tb_css_sf7_axi_accelerator
```

The stream test covers result backpressure, stable payload holding, packing,
and TLAST mismatch detection. The integration test covers ID/version, status,
the complete result snapshot, counters, sticky flags, IRQ, W1P clears, and an
undefined register address.

## Remaining board work

The wrapper is RTL-verified and closes OOC routed timing at 100 MHz, but has not
been integrated into a PS7 block design.
The next step is to connect the input and result streams through DMA or suitable
stream infrastructure, map AXI-Lite in the PS address space, rerun complete
implementation timing, and execute a hardware smoke test. A 256-bit result
stream may require an AXI data-width converter for a narrower DMA/interconnect.
