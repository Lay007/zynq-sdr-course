# Lab 5.10 — Zynq-ready BPSK BER top-level

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
| `lock_inverted` | `1` when the counter locked on the inverted preamble (180 degrees) and flipped the payload back; held after `done` until the next `start` |

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
top-level TX sample outputs -> 24-sample delay, I sign inverted -> top-level RX sample inputs
```

The sign inversion is deliberate: it makes every run go through the inverted-lock path of the BER counter.

Then it verifies:

- `start` launches exactly one frame;
- `busy` becomes active during the run and clears at the end;
- `done` asserts only after the full burst finishes;
- the BER counters report zero total and payload errors;
- `lock_inverted = 1`: the counter locked on the inverted preamble that the inverted loopback produces.

## First hardware-facing interpretation

This top-level is still synthetic, but it is now structurally aligned with the future board path:

```text
frame source / control -> TX samples -> AD9363 TX -> RF path -> AD9363 RX -> RX samples -> BER counters
```

That is the correct place to attach AXI-Lite registers, DMA, BRAM control or board-specific clock/reset logic in the next step.

## What to expect

```text
PASS: bpsk_zynq_ber_top completed without errors (281 bits, payload errors 0)
```

Unlike Labs 5.8 and 5.9, the top-level contains `bpsk_ber_counter`, which finds the frame by correlating the received bits with the known preamble instead of trusting a fixed offset.

The course runner generates the vectors, compiles, simulates and turns any `FAIL` line or non-zero simulator exit into an error:

```bash
python tools/run_block5_hdl_smoke.py --test tb_bpsk_zynq_ber_top
```

In Vivado 2021.1 this top places and routes on `xc7z020clg400-2` at 100 MHz with +1.935 ns of
slack, using 653 LUTs, 3075 flip-flops and **192 of the 220 DSP48E1 slices (87 %)**
([report](https://github.com/Lay007/zynq-sdr-course/blob/main/reports/fpga/block5-bpsk-vivado-evidence.md)): the TX pulse-shaping filter and the RX matched filter take 96 each
(Lab 5.6). Anything else that needs multipliers on the same device, such as a carrier loop or a
second channel, would not fit. The worst path is a fan-out, not arithmetic: the per-frame RX
restart (`rst || frame_start`) driving 2560 reset pins of the matched filter, 3 logic levels and
87 % routing.

## Exercises

Each exercise below is a deliberate one-line RTL mutation. Make it, run the bench, read the messages, then restore the file (`git checkout -- <file>`). The quoted outputs were observed with Icarus Verilog 12.0.

1. Apply the same polarity flip as in Labs 5.8 and 5.9 (`out_bit <= (in_i >= 0);` in `bpsk_hard_decision.v`). Those two benches fail with 281 / 256 errors. This one fails differently: `ERROR: lock_inverted=0 on the sign-inverted loopback, expected 1`. Find the reason in `bpsk_ber_counter.v`: it counts preamble matches against both the true pattern (`m_noninv`) and the inverted one (`m_inv`), and on an inverted lock it flips the payload. This is 180-degree ambiguity resolution, and a real receiver needs it because a BPSK carrier loop can lock at 0 or 180 degrees. What would the error counters alone have shown?
2. The bench inverts the loopback on purpose. Why, and what should the PS do with `CONTROL_STATUS[3]` (Lab 5.11) on hardware?
3. What is the probability that 8 random bits match an 8-bit preamble exactly? Relate it to `LOCK_PREAMBLE_BITS` and `LOCK_ERR_TOL`.

<details markdown="1">
<summary>Answers (checked against the RTL and the bench)</summary>

1. The flip cancels the inversion of the loopback, so the counter now locks on the true preamble, counts zero total and payload errors, and drops `lock_inverted` to 0. The error counters alone would show a clean run: they cannot see a polarity bug, because the counter normalises the payload either way. Only the flag shows it. Before [issue #64](https://github.com/Lay007/zynq-sdr-course/issues/64) the polarity stayed in the internal `invert_bits` register and this mutation passed silently.
2. A straight loopback only ever exercises the non-inverted lock, so the inverted branch (`m_inv`, `invert_bits`, the payload flip) would never run in the regression. The inverted loopback runs it every time, and the `lock_inverted = 1` check makes the expected polarity part of the contract. On hardware, read `CONTROL_STATUS[3]` with every BER result and log it (the Block 11 gpreg bridge has the same information in `gp_status[6:5]`). On a link with a fixed phase, such as a digital or in-fabric loopback, it must not change, and a change points to a sign error in the chain. Behind a carrier loop either value is legitimate, and the logged values show how often the loop lands on each lock point. The QPSK top has the same output as a 2-bit `rotation_index` (k·90 degrees).
3. An exact 8-bit match by random bits has probability `1/256 ≈ 0.4 %`, doubled to about 0.8 % because either polarity is accepted. With `LOCK_ERR_TOL = t` the window accepts up to `t` mismatches: `P = 2 · Σ_{k≤t} C(8,k) / 256`, already 7 % for `t = 1`. Longer lock windows and a small tolerance keep false locks rare; the course default is 8 bits with `LOCK_ERR_TOL = 0`.

</details>

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
