# Lab 5.7 - BPSK 8x symbol upsampler

## Goal

Insert the explicit multi-rate bridge between the BPSK symbol mapper and the sample-rate RRC TX FIR.

The new block accepts one symbol-rate Q1.15 sample and emits the `8x` zero-stuffed sample stream required by the pulse-shaping filter:

```text
BPSK mapper -> 8x upsampler / zero-stuffer -> RRC TX FIR -> future DAC / RF chain
```

## Executable HDL package

| File | Purpose |
|---|---|
| `blocks/block_05_fpga_hdl_flow/rtl/bpsk_upsampler_8x.v` | symbol-rate to sample-rate bridge with `SPS = 8` |
| `blocks/block_05_fpga_hdl_flow/python/generate_bpsk_upsampler_8x_vectors.py` | generates deterministic input and expected-output vectors from the shared Block 11 package |
| `blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_upsampler_8x.v` | self-checking Verilog testbench |
| `blocks/block_05_fpga_hdl_flow/tb/bpsk_upsampler_8x_input_vectors.txt` | generated Q1.15 symbol stream |
| `blocks/block_05_fpga_hdl_flow/tb/bpsk_upsampler_8x_expected_vectors.txt` | generated zero-stuffed sample stream |

Run from the repository root:

```bash
python blocks/block_05_fpga_hdl_flow/python/generate_bpsk_upsampler_8x_vectors.py

iverilog -g2012 \
  -o blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_upsampler_8x.out \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_upsampler_8x.v \
  blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_upsampler_8x.v

vvp blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_upsampler_8x.out
```

Expected result:

```text
PASS: bpsk_upsampler_8x test completed without errors
```

## Why this block matters

The symbol mapper and the TX FIR do not naturally run at the same effective rate:

- mapper output: one complex symbol per symbol period;
- TX FIR input: one complex sample every FPGA clock in the sample-rate domain.

Without an explicit zero-stuffer, the mapper cannot be connected to the pulse-shaping filter in a deterministic RTL chain.

## Interface contract

| Signal | Meaning |
|---|---|
| `in_valid` | upstream presents one Q1.15 complex symbol |
| `in_ready` | upsampler can accept the next symbol |
| `out_valid` | one sample-rate output sample is available |
| `out_i`, `out_q` | first sample is the symbol, next `SPS-1` samples are zero |

The block keeps `out_valid` high for the full `8`-sample expansion of every accepted symbol.

## Shared inputs

The Python generator reuses:

| Shared file | Role |
|---|---|
| `tx_symbols_q15.txt` | exact symbol sequence from the shared BPSK package |
| `config.json` | provides `samples_per_symbol = 8` |

## What to expect

```text
PASS: bpsk_upsampler_8x test completed without errors (281 symbols, 2248 samples)
```

2248 = 281 x 8. The block zero-stuffs: the symbol appears on phase 0 and the next 7 output samples are zero, with `in_ready` low for those 7 cycles. The RRC filter of Lab 5.6 turns the zero-stuffed impulses into the shaped waveform.

The course runner generates the vectors, compiles, simulates and turns any `FAIL` line or non-zero simulator exit into an error:

```bash
python tools/run_block5_hdl_smoke.py --test tb_bpsk_upsampler_8x
```

## Exercises

Each exercise below is a deliberate one-line RTL mutation. Make it, run the bench, read the messages, then restore the file (`git checkout -- <file>`). The quoted outputs were observed with Icarus Verilog 12.0.

1. Make the counter one short: `if (phase == SPS - 2)`. The bench reports 786 errors. The first is `out=(32767,0) expected=(0,0) idx=7` (the next symbol arrives one sample early), and the last is `out_valid=0 expected=1 idx=2247` (the stream ends early). An off-by-one in a counter shows up as a periodic misalignment, not as a random error.
2. Why zero-stuffing and not sample-and-hold (repeating the symbol 8 times)? Describe what holding does to the spectrum before the RRC filter.
3. With zero-stuffing, the average power per output sample drops by a factor of 8. The 65 TX taps in `rtl/bpsk_rrc_tx_fir_taps.mem` sum to about 2.85 (close to the square root of 8), and the largest tap is 0.387. Explain where that scaling comes from and how much headroom it leaves below Q1.15 full scale.

## Lab 5.7b: the upsampler and the TX filter as one polyphase filter

The zeros this block inserts are not free downstream: `bpsk_rrc_tx_fir` multiplies them. For output
phase p (0..7) only the taps p, p+8, ..., p+64 meet a non-zero input, so

```text
y[8n + p] = sum over m of h[p + 8m] * s[n - m],   m = 0..8
```

`rtl/bpsk_rrc_tx_polyphase.v` computes exactly that: 9 multipliers per channel whose coefficients
change with the phase, a registered adder tree, the same rounding and saturation. It has the ports
of the pair (symbol input with `in_ready`, sample output) and is checked clock for clock against
`bpsk_upsampler_8x` followed by `bpsk_rrc_tx_fir`:

```bash
iverilog -g2012 -o /tmp/tx_pp.vvp \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_upsampler_8x.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_rrc_tx_fir.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_rrc_tx_polyphase.v \
  blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_rrc_tx_polyphase_equivalence.v
vvp /tmp/tx_pp.vvp
```

```text
PASS: bpsk_rrc_tx_polyphase equals bpsk_upsampler_8x + bpsk_rrc_tx_fir clock for clock (600 symbols, 4800 samples, 0 saturated)
```

Vivado 2021.1 on `xc7z020clg400-2` at 100 MHz ([report](https://github.com/Lay007/zynq-sdr-course/blob/main/reports/fpga/block5-bpsk-vivado-evidence.md)):

| Implementation | LUT | FF | DSP48E1 | WNS |
|---|---:|---:|---:|---:|
| `bpsk_upsampler_8x` + `bpsk_rrc_tx_fir` | 169 | 2303 | 96 | +3.038 ns (filter) |
| `bpsk_rrc_tx_polyphase` | 404 | 541 | 14 | +3.233 ns |

Same output, a seventh of the DSP slices and a quarter of the flip-flops; the extra LUTs are the
coefficient multiplexers. The hardware TX path keeps the original pair, so nothing on the board
changes.

4. The design has 18 multiplies (9 per channel) but uses 14 DSP slices. Synthesize it
   (`python tools/generate_block5_bpsk_vivado_reports.py --top bpsk_rrc_tx_polyphase` writes the
   reports) and read the "DSP: Preliminary Mapping Report" in the synthesis log: most slices get
   only a 2-3 bit B input. Where did the rest of each coefficient go, and what does that cost in
   LUTs?
5. Why can the RX matched filter in Lab 5.8 not use the same trick, and which receive-side
   structure would (think of the decimation after the matched filter)?

## Report checklist

- [ ] Explain why the mapper-to-FIR boundary is a multi-rate interface.
- [ ] Show `in_ready` and `out_valid` timing for at least two symbols.
- [ ] State that the expected output is one symbol sample followed by seven zeros.
- [ ] Show how this block feeds `bpsk_rrc_tx_fir.v` in the next integration step.

## Engineering conclusion template

```text
The BPSK 8x upsampler converts one symbol-rate Q1.15 sample into eight sample-rate outputs.
It is the explicit timing bridge between the symbol mapper and the RRC TX FIR.
With this block in place, the TX HDL path now has a deterministic sample-rate input stream for pulse shaping.
```
