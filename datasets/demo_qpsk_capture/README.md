# Demo QPSK Capture Dataset

This folder defines a small dataset package for QPSK replay and future hardware validation.

The raw IQ file is intentionally not committed yet. The first version is a manifest contract that can be used with synthetic replay data or with a future validated capture from the Zynq/AD9363 stand.

## Intended use

- QPSK constellation analysis.
- EVM and SNR computation.
- Dataset manifest validation.
- Final project report evidence.

## Files

| File | Role |
|---|---|
| `manifest.yaml` | Stable dataset description and expected analysis targets |

## Next steps

1. Generate or capture a short QPSK IQ file.
2. Compute SHA256.
3. Update `manifest.yaml`.
4. Add preview plots under `docs/assets` or this folder.
5. Link the dataset from a final report page.
