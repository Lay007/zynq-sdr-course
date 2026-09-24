# Lab 4.4 - BPSK Simulink chain and ideal BER vs SNR

## Goal

Add a real Simulink stage to the BPSK route and verify that MATLAB/Simulink produces an ideal BER-vs-SNR curve for the reference AWGN case.

This lab closes the Simulink part of the route:

```text
Block 11 handoff files -> Simulink fixed-point chain -> ideal BER/SNR baseline -> HDL stage
```

## Why this lab matters

Every BER number you measure later on the board needs a yardstick. "BER = 1e-3" is
meaningless until you know what the *best possible* receiver would achieve at the
same signal-to-noise ratio. Coherent BPSK over AWGN has a closed-form answer, and
Simulink lets you check that your fixed-point chain, sample by sample, reaches it.
If your simulated curve sits far to the right of theory, the implementation is
losing decibels somewhere (timing, quantization, filter mismatch); if a hardware
measurement is far to the right of *this* curve, the loss is in the RF chain or the
synchronization, not in the modem maths.

## Executable MATLAB files

| File | Role |
|---|---|
| `blocks/block_04_simulink_and_fixed_point/matlab/lab_4_4_prepare_bpsk_simulink_workspace.m` | loads Block 11 handoff files into the MATLAB/Simulink workspace |
| `blocks/block_04_simulink_and_fixed_point/matlab/lab_4_4_generate_bpsk_simulink_models.m` | generates the `.slx` models programmatically |
| `blocks/block_04_simulink_and_fixed_point/matlab/lab_4_4_run_bpsk_simulink_models.m` | runs both models and saves report-ready figures |

## Generated Simulink models

| Model | Path | Purpose |
|---|---|---|
| Fixed-point chain | `blocks/block_04_simulink_and_fixed_point/simulink/lab_4_4_bpsk_fixed_point_chain.slx` | imports the Block 11 BPSK handoff files and runs the TX/RX RRC filters in Simulink |
| Ideal BER model | `blocks/block_04_simulink_and_fixed_point/simulink/lab_4_4_bpsk_ideal_ber_awgn.slx` | ideal BPSK over AWGN for BER-vs-SNR validation |

## How to run

From the repository root:

```bash
matlab -batch "lab_4_4_run_bpsk_simulink_models"
```

## Generated artifacts

```text
docs/assets/lab44_bpsk_simulink_tx_overlay_matlab.png
docs/assets/lab44_bpsk_simulink_rx_overlay_matlab.png
docs/assets/lab44_bpsk_ideal_ber_vs_snr_matlab.png
docs/assets/lab44_bpsk_simulink_metrics.json
```

## Engineering meaning

The lab intentionally separates two checks:

1. The fixed-point Simulink chain reuses the exact BPSK handoff files from Block 11.
2. The ideal BER model establishes the best-case receiver curve for coherent BPSK over AWGN.

This matters because later hardware BER results should be compared not only against previous software code, but also against the ideal reference limit.

## BER-vs-SNR convention

The ideal curve is plotted against `SNR / E_b/N_0, dB`.

For the one-sample-per-symbol ideal BPSK model used here, this is the convenient reference axis for the theoretical curve:

```text
BER_theory = 0.5 * erfc(sqrt(10^(Eb/N0_dB / 10)))
```

The Simulink sweep overlays Monte Carlo points on top of that theory curve.

Reference points of the theory curve, so you can sanity-check your plot:

| Eb/N0 | ideal BPSK BER |
|---:|---:|
| 0 dB | 7.86e-02 |
| 2 dB | 3.75e-02 |
| 4 dB | 1.25e-02 |
| 6 dB | 2.39e-03 |
| 8 dB | 1.91e-04 |
| 9.6 dB | 9.74e-06 |

The curve steepens with SNR: 2 dB buys about a factor of 2 in BER between 0 and 2 dB, but
about a factor of 12 between 6 and 8 dB. A run of
`N` bits can only resolve BERs down to about `1/N`: to see 1e-5 you need well over
100 000 bits per point, otherwise the Monte Carlo points at high SNR read as zero.

> This lab requires MATLAB/Simulink, which is not part of the automated CI. The
> reference values above are from the closed-form formula, not from a Simulink run.

## What to expect

`docs/assets/lab44_bpsk_simulink_metrics.json` holds the result of a MATLAB/Simulink run committed on 2026-06-25. It was not re-run for this page (MATLAB is not part of CI):

| Eb/N0 | 0 dB | 2 dB | 4 dB | 6 dB | 8 dB | 9 dB | 10 dB |
|---|---:|---:|---:|---:|---:|---:|---:|
| Simulink BER | 7.69e-2 | 3.80e-2 | 1.24e-2 | 2.46e-3 | 1.9e-4 | 3.0e-5 | 5e-6 |
| theory | 7.86e-2 | 3.75e-2 | 1.25e-2 | 2.39e-3 | 1.91e-4 | 3.36e-5 | 3.9e-6 |

- The fixed-point chain reproduces the Block 11 waveforms with TX RMSE 0 and RX RMSE 6.1e-5 (about 2 LSB of Q1.15).
- The largest BER difference from theory is 1.7e-3, at 0 dB, where the BER itself is 7.9e-2.
- Every simulated value is a multiple of 5e-6, which fits 200 000 bits per point. The 10 dB point is then **one** bit error, and the 9 dB point six: those two points carry almost no statistical weight.

Without MATLAB, the same yardstick is available in Python: [Lab 8.8](/zynq-sdr-course/en/labs/lab-8-8-qpsk-modem-impairments/) simulates Gray QPSK, whose per-bit BER is this same curve, and [Lab 4.3](/zynq-sdr-course/en/labs/lab-4-3-bpsk-fixed-point-chain/) runs the fixed-point BPSK chain on the same Block 11 handoff files.

## Exercises

1. Compute the 95 % interval for the 10 dB point (1 error in 200 000 bits) and for the 8 dB point (38 errors). Does either contradict the theory value?
2. How many bits per point would you need so that the 10 dB point has at least 100 errors? How long would that take at the 240 kSym/s of the hardware frame?
3. The RX RMSE is 6.1e-5 while the TX RMSE is exactly 0. Which blocks sit between the two measurement points, and which of them rounds?

## Report checklist

- [ ] Show the Simulink TX overlay against the MATLAB reference.
- [ ] Show the Simulink RX matched-filter overlay against the MATLAB reference.
- [ ] Include the BER-vs-SNR plot with theoretical and Simulink curves.
- [ ] State the SNR range and the number of bits used per simulation point.
- [ ] Explain that this curve is the ideal AWGN baseline for later Zynq measurements.

## Engineering conclusion template

```text
The Simulink fixed-point chain reproduced the reference waveforms with TX/RX RMSE = ____ / ____.
The ideal BPSK BER-vs-SNR curve was generated for SNR = ____ to ____ dB and matched theory within ____.
This model now serves as the clean Simulink baseline before HDL and hardware bring-up.
```
