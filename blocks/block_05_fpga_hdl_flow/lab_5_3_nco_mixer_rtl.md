# Lab 5.3 — Fixed-Point NCO Mixer RTL

## Goal

Implement a compact fixed-point NCO-based IQ mixer in RTL and verify it against deterministic Python-generated reference vectors.

This lab connects Block 4 fixed-point digital mixing with an executable Verilog implementation.

## Executable HDL package

| File | Purpose |
|---|---|
| `blocks/block_05_fpga_hdl_flow/rtl/nco_mixer_iq.v` | executable Q1.15 NCO IQ mixer RTL block |
| `blocks/block_05_fpga_hdl_flow/tb/tb_nco_mixer_iq.v` | self-checking Verilog testbench |
| `blocks/block_05_fpga_hdl_flow/python/generate_nco_mixer_iq_vectors.py` | deterministic reference-vector generator |
| `blocks/block_05_fpga_hdl_flow/tb/nco_mixer_iq_input_vectors.txt` | generated input vectors |
| `blocks/block_05_fpga_hdl_flow/tb/nco_mixer_iq_expected_vectors.txt` | generated expected output vectors |

Run from the repository root:

```bash
python blocks/block_05_fpga_hdl_flow/python/generate_nco_mixer_iq_vectors.py

iverilog -g2012 \
  -o blocks/block_05_fpga_hdl_flow/tb/tb_nco_mixer_iq.out \
  blocks/block_05_fpga_hdl_flow/rtl/nco_mixer_iq.v \
  blocks/block_05_fpga_hdl_flow/tb/tb_nco_mixer_iq.v

vvp blocks/block_05_fpga_hdl_flow/tb/tb_nco_mixer_iq.out
```

Expected result:

```text
PASS: nco_mixer_iq test completed without errors
```

The GitHub Actions workflow `.github/workflows/block5_hdl.yml` generates vectors and runs this simulation automatically.

## Engineering question

> How does a fixed-point digital mixer become a clocked RTL block with an NCO, LUT, complex multiplier, rounding and saturation?

## DSP equation

For complex input:

```text
x[n] = I[n] + jQ[n]
w[n] = cos(phi[n]) + j sin(phi[n])
y[n] = x[n] * w[n]
```

The RTL implements:

```text
y_i = I*cos - Q*sin
y_q = I*sin + Q*cos
```

## NCO model

The educational RTL uses a compact phase accumulator:

```text
phase[n+1] = phase[n] + phase_increment
```

For this lab:

```text
PHASE_W = 4
LUT size = 16 samples
PHASE_INC = 1
```

This is intentionally small so students can inspect all LUT values and waveform transitions. A production SDR mixer should use a wider phase accumulator and a higher quality oscillator implementation.

## Fixed-point formats

| Signal | Format | Comment |
|---|---|---|
| Input I/Q | Q1.15 | signed 16-bit samples |
| sin/cos LUT | Q1.15 | signed 16-bit oscillator values |
| Product | Q2.30 | multiplication result |
| Accumulator | 40-bit educational accumulator | safe for sum/difference |
| Output I/Q | Q1.15 | rounded and saturated |

## RTL datapath

```mermaid
flowchart LR
    PHASE[Phase accumulator] --> LUT[sin/cos LUT]
    LUT --> CMUL[Complex multiplier]
    IN[Input IQ] --> CMUL
    CMUL --> ROUND[Round to Q1.15]
    ROUND --> SAT[Saturate]
    SAT --> OUT[Output IQ]
```

## Testbench strategy

The testbench verifies:

1. reset behaviour;
2. `out_valid` alignment;
3. phase advance only on valid input;
4. signed complex multiplication;
5. rounding to Q1.15;
6. saturation bounds;
7. sample-by-sample agreement with Python reference vectors.

## Scaling toward real SDR designs

| Educational lab | Production SDR version |
|---|---|
| 4-bit phase accumulator | 24–48 bit phase accumulator |
| 16-entry LUT | large LUT, interpolated LUT or CORDIC |
| no tready | AXI-Stream valid/ready |
| compact unpipelined multiplier | pipelined DSP-slice complex multiplier |
| vector testbench | constrained/random and file-based regression |

## What to expect

```text
PASS: nco_mixer_iq test completed without errors
```

The NCO uses a 16-entry sine table and `PHASE_INC = 1`, so the mixer rotates the input by +22.5 degrees per valid sample (a shift of +fs/16). The Python reference uses the same table, rounding and saturation, so the comparison is bit-exact.

The course runner generates the vectors, compiles, simulates and turns any `FAIL` line or non-zero simulator exit into an error:

```bash
python tools/run_block5_hdl_smoke.py --test tb_nco_mixer_iq
```

On the course FPGA (Vivado 2021.1 out-of-context synthesis, `xc7z020clg400-2`, 100 MHz; `python tools/generate_block5_vivado_reports.py`) this mixer takes 110 LUT, 37 FF and 4 DSP48E1, and misses 100 MHz: WNS -0.807 ns, 16 of 36 endpoints failing, 15 logic levels, an estimate of about 92.6 MHz. The LUT lookup, the complex multiply, the rounding and the saturation all happen in one clock, the same pattern as the FIR of Lab 5.2 (see its exercise 4 for what pipelining that pattern does).

## Exercises

Each exercise below is a deliberate one-line RTL mutation. Make it, run the bench, read the messages, then restore the file (`git checkout -- <file>`). The quoted outputs were observed with Icarus Verilog 12.0.

1. Conjugate the mixer (rotate the other way): `acc_i = I*cos + Q*sin`, `acc_q = -I*sin + Q*cos`. The bench reports 8 errors with the Q sign flipped, for example `out=(11087,-4592) expected=(11087,4592)`. This is the same wrong-sign error as in Lab 3.3: the signal lands at -fs/16 instead of +fs/16.
2. Replace rounding with truncation: `round_q15 = value >>> SHIFT;`. The bench reports 8 errors, for example `out=(11999,0) expected=(12000,0)`. Note that the first one happens at phase 0, where cos = 32767, not 32768: 12000 * 32767 / 32768 = 11999.63, which rounds to 12000 but truncates to 11999. Q1.15 cannot represent +1.0 exactly.
3. Estimate the spurious-free dynamic range of a 16-entry, 16-bit table and compare with the "about 6 dB per phase-address bit" rule measured in Lab 3.3. What would you change first to improve it: table length or table word width?

## Report checklist

- [ ] State input, LUT, product, accumulator and output formats.
- [ ] Explain phase accumulator behaviour.
- [ ] Explain why the LUT is intentionally small.
- [ ] Run the testbench and record PASS output.
- [ ] Inspect the VCD waveform.
- [ ] State measured latency.
- [ ] Explain how to scale the design to a real SDR NCO.

## Engineering conclusion template

```text
The NCO mixer uses Q1.15 input samples and Q1.15 oscillator values.
The educational phase accumulator is ____ bits and advances only when in_valid is asserted.
The output is rounded and saturated back to Q1.15. The simulation passes against
Python-generated reference vectors, so the next step is widening the phase accumulator
and replacing the compact LUT with a production oscillator architecture.
```
