# Lab 4.4 - BPSK Simulink chain and ideal BER vs SNR

## Goal

Add a real Simulink stage to the BPSK route and verify that MATLAB/Simulink produces an ideal BER-vs-SNR curve for the reference AWGN case.

This lab closes the Simulink part of the route:

```text
Block 11 handoff files -> Simulink fixed-point chain -> ideal BER/SNR baseline -> HDL stage
```

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
