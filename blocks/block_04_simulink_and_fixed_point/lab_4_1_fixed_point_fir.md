# Lab 4.1 — Fixed-Point FIR Filtering

## Goal

Convert the floating-point FIR filter from Block 3 into a fixed-point implementation and evaluate the implementation error before moving toward HDL.

The lab answers the practical question:

> What word lengths are sufficient for an FIR filter to keep useful signal quality while staying economical for FPGA implementation?

## Executable files

| Environment | File | Output |
|---|---|---|
| Python | `blocks/block_04_simulink_and_fixed_point/python/lab_4_1_fixed_point_fir.py` | metrics + PNG figures in `docs/assets` |
| MATLAB | `blocks/block_04_simulink_and_fixed_point/matlab/lab_4_1_fixed_point_fir.m` | metrics + PNG figures in `docs/assets` |

Run from the repository root:

```bash
python blocks/block_04_simulink_and_fixed_point/python/lab_4_1_fixed_point_fir.py
```

MATLAB:

```bash
matlab -batch "run('blocks/block_04_simulink_and_fixed_point/matlab/lab_4_1_fixed_point_fir.m')"
```

Generated Python figures:

```text
docs/assets/lab41_fixed_point_fir_response.png
docs/assets/lab41_fixed_point_fir_spectrum.png
docs/assets/lab41_fixed_point_fir_error.png
```

Generated MATLAB figures:

```text
docs/assets/lab41_fixed_point_fir_response_matlab.png
docs/assets/lab41_fixed_point_fir_spectrum_matlab.png
docs/assets/lab41_fixed_point_fir_error_matlab.png
```

## Engineering context

A floating-point FIR is convenient for algorithm design, but FPGA implementation requires explicit decisions about:

- input IQ format;
- coefficient format;
- product width;
- accumulator width;
- rounding mode;
- saturation mode;
- output scaling;
- allowed error versus the reference model.

## Processing chain

```mermaid
flowchart LR
    X[Input IQ Q-format] --> COEF[Quantized FIR coefficients]
    COEF --> MAC[Fixed-point MAC chain]
    X --> MAC
    MAC --> ROUND[Rounding / scaling]
    ROUND --> SAT[Saturation]
    SAT --> Y[Output IQ]
    Y --> ERR[Float vs fixed error]
```

## Recommended starting formats

| Signal | Start format | Notes |
|---|---|---|
| Input IQ | Q1.15 | normalized complex samples |
| FIR coefficients | Q1.15 | Blackman/windowed-sinc coefficients |
| Product | Q2.30 | multiplication of Q1.15 by Q1.15 |
| Accumulator | Q6.30 or wider | depends on number of taps |
| Output IQ | Q1.15 | after rounding and saturation |

For an FIR with `N` taps, use at least:

```text
guard_bits = ceil(log2(N))
```

extra accumulator bits.

## Reference implementations

The executable Python and MATLAB scripts implement the same experiment:

1. generate a complex IQ signal with a wanted tone, interferer and noise;
2. design a Blackman-windowed low-pass FIR;
3. quantize input samples and coefficients to Q1.15;
4. run an educational integer fixed-point FIR model;
5. compare floating-point and fixed-point outputs;
6. compute RMS error, max error, SQNR, guard bits and saturation count;
7. save comparison figures.

## Required plots

Produce at least:

1. floating-point FIR magnitude response;
2. quantized-coefficient FIR magnitude response;
3. spectrum before filtering;
4. spectrum after float FIR;
5. spectrum after fixed FIR;
6. error spectrum or time-domain error.

## Metrics

| Metric | How to compute | Engineering meaning |
|---|---|---|
| RMS error | `rms(y_float - y_fixed)` | average implementation error |
| SQNR | signal RMS / error RMS | quantization quality |
| Max abs error | `max(abs(error))` | worst-case excursion |
| Stopband delta | float stopband vs quantized stopband | coefficient quantization impact |
| Saturation count | number of clipped output samples | scaling quality |

## HDL mapping

The fixed-point FIR maps to a streaming block:

```text
input  wire              clk
input  wire              rst
input  wire              in_valid
input  wire signed [15:0] in_i
input  wire signed [15:0] in_q
output wire              out_valid
output wire signed [15:0] out_i
output wire signed [15:0] out_q
```

Implementation options:

| Architecture | Pros | Cons |
|---|---|---|
| Fully parallel FIR | maximum throughput | many multipliers |
| Time-multiplexed MAC | fewer resources | lower throughput / more control logic |
| Symmetric FIR | fewer multipliers | only for symmetric coefficients |

## What to expect

```text
FIR taps: 129
Cutoff: 250.0 kHz
Input/coefficient format: Q1.15
Recommended FIR guard bits: 8
RMS error: 3.975029e-05
Max abs error: 7.540183e-05
SQNR: 83.51 dB
Saturation count: 0
```

- **SQNR 83.5 dB** is the whole fixed-point path (input, coefficient and output rounding) against the floating-point filter. The max error of 7.5e-5 is about 2.5 LSB of Q1.15 (1 LSB = 3.05e-5).
- **Zero saturations**: the input is normalised to a peak of 0.85 and the taps are normalised to a DC gain of 1, so the output cannot exceed full scale.
- **8 guard bits** = ceil(log2(129)). With these taps the sum of |h| is 1.81, so the true worst-case growth is under 1 bit; the rule is a safe upper bound and costs nothing in a DSP48 with a 48-bit accumulator.
- The coefficient quantization sets the stopband: the Q1.15 response peaks at **-71.0 dB** from 400 kHz up, against -89.7 dB for the float taps (the same filter as Lab 3.2).

## Exercises

1. Change `q_fractional_bits` and rerun. With `sample_count = 8192` (to keep the pure-Python loop fast) the SQNR was 83.5, 80.7, 75.9, 66.4 and 63.9 dB for 15, 14, 13, 12 and 11 bits, and 49.3 dB at 9. Quantizing only the taps (float data) gives almost the same numbers (84.1 dB at 15 bits), so the coefficients dominate. That is also why the steps are irregular instead of 6.02 dB per bit: a coefficient error is one fixed, deterministic change of the filter, not white noise added to every sample.
2. Quantize only the taps and plot the stopband. Observed peaks from 400 kHz up: -71.0 dB (15 fractional bits), -59.6 dB (13), -47.9 dB (11), -35.3 dB (9), again about 6 dB per bit. Count the taps that round to zero (115, 107, 93, 73 non-zero of 129). Which is the cheaper fix for a -80 dB requirement: more coefficient bits or a shorter filter with larger taps?
3. Scale the input up until the saturation counter becomes non-zero. What happens to the SQNR, and why is a few saturations much worse than a few LSB of rounding error?

## Report checklist

- [ ] State input, coefficient, product, accumulator and output formats.
- [ ] Explain coefficient quantization.
- [ ] Plot float and quantized FIR responses.
- [ ] Compare output spectra.
- [ ] Compute RMS error and SQNR.
- [ ] Count saturation events.
- [ ] Estimate accumulator guard bits.
- [ ] State whether the FIR is ready for HDL.

## Engineering conclusion template

```text
The selected FIR format ______ provides SQNR = ____ dB and saturation count = ____.
The coefficient quantization changes stopband rejection by approximately ____ dB.
The accumulator requires at least ____ guard bits for ____ taps.
This configuration is / is not ready for an HDL implementation because ______.
```
