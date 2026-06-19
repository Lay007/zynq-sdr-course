# Lab 5.11 - AXI-Lite control wrapper for the BPSK BER top-level

## Goal

Expose the deterministic BPSK BER top-level to a Zynq Processing System style control plane:

```text
PS / software -> AXI-Lite registers -> framed BPSK BER core -> TX/RX sample seam
```

This is the control-path companion to Lab 5.10. The DSP datapath stays the same, but the start command, timing parameters and BER results now pass through a compact memory-mapped register interface.

## Executable HDL package

| File | Purpose |
|---|---|
| `blocks/block_05_fpga_hdl_flow/rtl/bpsk_zynq_ber_axi_lite.v` | AXI-Lite wrapper around `bpsk_zynq_ber_top.v` |
| `blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_zynq_ber_axi_lite.v` | self-checking AXI-Lite testbench |

Run from the repository root:

```bash
python blocks/block_05_fpga_hdl_flow/python/generate_bpsk_framed_loopback_vectors.py
python blocks/block_05_fpga_hdl_flow/python/generate_bpsk_rrc_tx_fir_vectors.py

iverilog -g2012 \
  -o blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_zynq_ber_axi_lite.out \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_symbol_mapper.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_upsampler_8x.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_rrc_tx_fir.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_rrc_rx_fir.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_symbol_timing_sampler.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_hard_decision.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_framed_tx_chain.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_rx_bit_recovery_chain.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bit_source.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_ber_counter.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_zynq_ber_top.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_zynq_ber_axi_lite.v \
  blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_zynq_ber_axi_lite.v

vvp blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_zynq_ber_axi_lite.out
```

Expected result:

```text
PASS: bpsk_zynq_ber_axi_lite completed without errors
```

## Register map

| Address | Name | Access | Meaning |
|---|---|---|---|
| `0x00` | `CONTROL_STATUS` | `W/RO` | bit `0`: write `1` to launch one frame; bit `1`: `busy`; bit `2`: `done` sticky, clear by writing `1` to bit `2` |
| `0x04` | `FRAME_BIT_COUNT` | `RW` | number of bits to transmit and compare |
| `0x08` | `PREAMBLE_COUNT` | `RW` | number of preamble bits excluded from payload BER |
| `0x0C` | `START_OFFSET` | `RW` | deterministic matched-filter sample index for symbol decisions |
| `0x10` | `RECEIVED_BITS` | `RO` | number of recovered bits in the last completed run |
| `0x14` | `TOTAL_ERRORS` | `RO` | total bit errors in the last completed run |
| `0x18` | `PAYLOAD_ERRORS` | `RO` | payload-only bit errors in the last completed run |
| `0x1C` | `ID` | `RO` | fixed identification word `0x4250534B` |

## Interface intent

This wrapper is designed for low-rate control, not bulk sample transport:

- AXI-Lite configures the frame launch and reads back BER counters;
- the sample stream remains on the explicit TX/RX seam from Lab 5.10;
- a future design can connect that seam to AD9363, DMA or a stream bridge.

## Why this stage matters

The earlier labs proved that the modem logic works. This lab proves that the control plane is also integration-ready:

1. software can program the deterministic frame configuration;
2. software can trigger exactly one burst;
3. software can poll `busy` and `done`;
4. software can read BER counters after the burst finishes.

That is the minimum register contract needed before handing the design to a real Zynq PS or no-OS software layer.

## Testbench strategy

The self-checking testbench:

1. reads the shared deterministic metadata;
2. writes frame configuration registers over AXI-Lite;
3. starts one burst through the control register;
4. loops TX samples back into RX samples;
5. polls the status register until the sticky `done` bit is set;
6. verifies zero BER and then clears the sticky `done` flag.

## Hardware-facing interpretation

The first hardware use is straightforward:

```text
PS writes AXI-Lite registers -> one short deterministic burst launches -> AD9363 TX/RX path or external monitor observes the result
```

This is the correct point to connect no-OS software, Linux userspace register pokes, or a small driver.

## First AD9363 handoff order

Use the existing repository tools as the bring-up path:

1. Probe the remote IIO context with `python blocks/block_06_rf_frontend_and_ad9363/python/lab_6_3_probe_iio_context.py --uri ip:192.168.40.1`.
2. Apply the conservative Block 6.3 RF policy: minimum TX power, low manual RX gain, AGC disabled, and a short burst only.
3. Read the AXI-Lite `ID` register first, then program `FRAME_BIT_COUNT`, `PREAMBLE_COUNT`, and `START_OFFSET`.
4. Write `1` to `CONTROL_STATUS[0]`, poll `busy`, then wait for sticky `done`.
5. Use the controlled Zynq RX path for BER counters and keep RTL-SDR as a spectrum-only observer during the first OTA check.

This keeps the discovery run small and deterministic before moving to longer bursts or quantitative BER measurement.

## Report checklist

- [ ] Include the register map.
- [ ] State which registers must be programmed before `start`.
- [ ] Show how `done` is cleared.
- [ ] Show the `ID` readback as a bring-up sanity check.
- [ ] State that AXI-Lite controls only the configuration path, not the sample stream.

## Engineering conclusion template

```text
The deterministic BPSK BER core is now exposed through an AXI-Lite control wrapper.
Software can program the frame size, preamble size and sampling offset, launch one burst and read back BER counters.
This is the minimal PS-facing contract needed before connecting the modem path to AD9363 or DMA-based hardware integration.
```
