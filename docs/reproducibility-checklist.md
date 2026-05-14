# Reproducibility Checklist

This checklist helps students and contributors reproduce SDR experiments consistently.

## Before running experiments

- Verify sample-rate configuration.
- Verify RF center frequency.
- Verify gain settings.
- Verify clock source assumptions.
- Record software and firmware versions.

## During recording

Store:

- IQ format;
- sample rate;
- timestamp;
- RF bandwidth;
- capture duration;
- hardware configuration.

## During analysis

Document:

- FFT parameters;
- synchronization configuration;
- filtering assumptions;
- BER/EVM calculation method.

## Recommended artifacts

| Artifact | Purpose |
|---|---|
| capture metadata | experiment traceability |
| screenshots | visual verification |
| FFT plots | spectral validation |
| constellation plots | synchronization quality |
| BER/EVM reports | quantitative validation |

## Educational objective

Students should learn not only how to run SDR experiments, but also how to make them reproducible and reviewable.
