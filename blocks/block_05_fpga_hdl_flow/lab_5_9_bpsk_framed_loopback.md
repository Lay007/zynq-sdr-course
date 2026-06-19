# Lab 5.9 - BPSK framed TX/RX loopback top-level

## Goal

Promote the separate TX and RX anchors into one deterministic framed HDL chain:

```text
framed bits -> symbol mapper -> 8x upsampler -> RRC TX FIR -> RRC RX FIR -> fixed-phase timing -> hard decision
```

This is the first Zynq-oriented top-level integration step in Block 5. It adds two things that the earlier labs intentionally avoided:

1. framed source control with `valid/ready/last`;
2. deterministic zero-symbol flushing after the last bit so the FIR tails are fully observable in loopback.

## Executable HDL package

| File | Purpose |
|---|---|
| `blocks/block_05_fpga_hdl_flow/rtl/bpsk_framed_tx_chain.v` | framed BPSK TX chain with automatic flush tail |
| `blocks/block_05_fpga_hdl_flow/rtl/bpsk_rx_bit_recovery_chain.v` | RX matched filter, timing sampler and hard decision wrapper |
| `blocks/block_05_fpga_hdl_flow/python/generate_bpsk_framed_loopback_vectors.py` | generates framed input bits and loopback metadata |
| `blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_framed_loopback.v` | self-checking integrated TX/RX loopback testbench |

Run from the repository root:

```bash
python blocks/block_05_fpga_hdl_flow/python/generate_bpsk_framed_loopback_vectors.py

iverilog -g2012 \
  -o blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_framed_loopback.out \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_symbol_mapper.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_upsampler_8x.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_rrc_tx_fir.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_rrc_rx_fir.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_symbol_timing_sampler.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_hard_decision.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_framed_tx_chain.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_rx_bit_recovery_chain.v \
  blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_framed_loopback.v

vvp blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_framed_loopback.out
```

Expected result:

```text
PASS: bpsk_framed_loopback completed without errors
```

## What changed compared to Labs 5.6-5.8

The earlier labs proved each bridge separately:

- bit-to-symbol mapping;
- symbol-rate to sample-rate expansion;
- TX pulse shaping;
- RX matched filtering and deterministic bit recovery.

This lab proves that those stages can now run as one framed burst rather than as isolated static checks.

## Framing contract

The TX wrapper accepts:

| Signal | Meaning |
|---|---|
| `s_valid` | one source bit is available |
| `s_ready` | the chain can accept the next framed bit |
| `s_last` | marks the last payload bit of the frame |

After `s_last`, the wrapper injects a deterministic zero-symbol flush tail. In the current BPSK setup the loopback metadata resolves this to `16` zero symbols, which is enough to expose the combined TX and RX FIR tails.

## Shared metadata from Block 11

The loopback generator reuses:

| Shared file | Role |
|---|---|
| `tx_bits.txt` | framed bit payload and expected BER reference |
| `rrc_taps_q15.txt` | shared TX/RX pulse-shaping coefficients |
| `config.json` | `samples_per_symbol = 8` and frame context |

The generator searches for the deterministic matched-filter sampling point of the fully integrated HDL-equivalent loopback and stores it in `bpsk_framed_loopback_meta.txt`.

## Why this stage matters

This is the missing bridge between unit-style HDL checks and an actual board-level modem path:

1. there is now a framed entry point instead of loose standalone vectors;
2. the TX chain has explicit burst termination behavior;
3. the RX chain is wired to the same timing and BER contract;
4. the end-to-end HDL route can now be promoted to a Zynq top-level with DMA or RF I/O.

## Report checklist

- [ ] Show that `s_ready` throttles the framed source to the 8x upsampler rate.
- [ ] State the flush-symbol count and why it is needed.
- [ ] Include the deterministic `start_offset` used by the loopback receiver.
- [ ] Show the final pass log with zero total and payload errors.
- [ ] State the next hardware step: routed top-level integration or board-level TX/RX validation.

## Engineering conclusion template

```text
The framed BPSK HDL loopback connected the mapper, 8x upsampler, TX RRC FIR and deterministic RX recovery chain into one self-checking burst path.
The TX side now exposes a framed ready/valid interface and appends a deterministic flush tail after the last bit.
This is the first integrated HDL top-level anchor that can be promoted to a routed Zynq design and later to measured BER experiments.
```
