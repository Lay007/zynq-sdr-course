# Lab 8.13 — DSSS acquisition and processing gain

## Goal

Build a direct-sequence spread-spectrum link:

- generate a length-127 maximal PN sequence;
- spread and despread BPSK data;
- acquire packet timing by correlation;
- measure processing gain against AWGN and a narrowband tone interferer;
- report BER with compared-bit counts.

## Run

```bash
python blocks/block_08_modulation_and_synchronization/python/lab_8_13_dsss_processing_gain.py
```

## Artifacts

```text
docs/assets/lab813_dsss_autocorrelation.png
docs/assets/lab813_dsss_acquisition.png
docs/assets/lab813_dsss_ber.png
docs/assets/lab813_dsss_metrics.json
```

## Interpretation

The 127-chip code has an ideal two-level cyclic autocorrelation and nominal processing gain `10·log10(127) ≈ 21 dB`. Correlation supplies acquisition timing, while despreading distributes a narrowband interferer across the output bandwidth. This robustness costs chip rate, bandwidth and correlator/PN synchronization logic.
