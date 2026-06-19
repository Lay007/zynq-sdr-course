# Lab 5.10 - Zynq-ready BPSK BER top-level

## Goal

Wrap the deterministic framed BPSK chain in a control-oriented top-level that looks much closer to the future Zynq integration path:

```text
start -> frame bit source -> framed TX chain -> external TX sample boundary
                                            -> external RX sample boundary -> RX recovery -> BER counter -> done
```

This lab keeps the BPSK frame source and BER checker inside the FPGA-facing logic while exposing the sample-domain TX/RX boundary for later AD9363, FIFO or DMA wiring.

## Executable HDL package

| File | Purpose |
|---|---|
| `blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bit_source.v` | deterministic ROM-backed frame source with `start/busy/done` semantics |
| `blocks/block_05_fpga_hdl_flow/rtl/bpsk_ber_counter.v` | compares recovered bits against the same frame ROM and counts total/payload BER |
| `blocks/block_05_fpga_hdl_flow/rtl/bpsk_zynq_ber_top.v` | top-level wrapper around source, TX chain, RX chain and BER checker |
| `blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_zynq_ber_top.v` | self-checking top-level loopback testbench |

Run from the repository root:

```bash
python blocks/block_05_fpga_hdl_flow/python/generate_bpsk_framed_loopback_vectors.py
python blocks/block_05_fpga_hdl_flow/python/generate_bpsk_rrc_tx_fir_vectors.py

iverilog -g2012 \
  -o blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_zynq_ber_top.out \
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
  blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_zynq_ber_top.v

vvp blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_zynq_ber_top.out
```

Expected result:

```text
PASS: bpsk_zynq_ber_top completed without errors
```

## Top-level contract

The new top-level is intentionally small but hardware-oriented:

| Signal group | Role |
|---|---|
| `start`, `busy`, `done` | one-shot frame launch and completion status |
| `frame_bit_count`, `preamble_count`, `start_offset` | deterministic control inputs derived from the shared Block 11 package |
| `tx_valid`, `tx_i`, `tx_q` | TX sample stream to a future DAC, FIFO or AD9363 TX path |
| `rx_valid`, `rx_i`, `rx_q` | RX sample stream from a future ADC, FIFO or AD9363 RX path |
| `received_bits`, `total_errors`, `payload_errors` | compact BER result interface |

## Why this stage matters

The earlier loopback testbench proved that the DSP chain works. This lab adds the system-level structure needed before a board design can use it:

1. a deterministic frame source rather than a direct testbench stimulus loop;
2. a BER counter that can later be memory-mapped or exported to software;
3. a clean sample-domain seam where AD9363 or AXI/DMA can attach;
4. explicit top-level completion semantics for automated hardware testing.

## Shared frame contract

The top-level reuses:

| Shared artifact | Role |
|---|---|
| `blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem` | deterministic frame bits for both the source and BER checker |
| `blocks/block_05_fpga_hdl_flow/tb/bpsk_framed_loopback_meta.txt` | start offset, bit count, preamble count and flush assumptions |

This keeps the source bits, BER reference and timing metadata synchronized across the standalone loopback and the Zynq-ready top-level.

## Testbench strategy

The self-checking testbench connects:

```text
top-level TX sample outputs -> top-level RX sample inputs
```

Then it verifies:

- `start` launches exactly one frame;
- `busy` becomes active during the run and clears at the end;
- `done` asserts only after the full burst finishes;
- the BER counters report zero total and payload errors.

## First hardware-facing interpretation

This top-level is still synthetic, but it is now structurally aligned with the future board path:

```text
frame source / control -> TX samples -> AD9363 TX -> RF path -> AD9363 RX -> RX samples -> BER counters
```

That is the correct place to attach AXI-Lite registers, DMA, BRAM control or board-specific clock/reset logic in the next step.

## Report checklist

- [ ] State the meaning of `start`, `busy` and `done`.
- [ ] Show how `frame_bit_count`, `preamble_count` and `start_offset` are supplied.
- [ ] Show the exposed TX and RX sample boundaries.
- [ ] Include the final BER counter values.
- [ ] State the next integration step: AXI-Lite registers, DMA hookup or AD9363 connection.

## Engineering conclusion template

```text
The deterministic BPSK modem chain now has a Zynq-ready top-level with a one-shot start interface, explicit completion status and BER counters.
The frame source and BER checker reuse the same ROM-backed bit sequence, so the test remains deterministic.
This is the correct integration anchor before connecting the design to AXI control, DMA or the AD9363 sample path.
```
