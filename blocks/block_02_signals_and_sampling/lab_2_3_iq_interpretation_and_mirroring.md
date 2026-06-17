# Lab 2.3 — I/Q Interpretation and Mirrored Spectrum

## Goal

Demonstrate the difference between correct complex I/Q capture, swapped I/Q channels, and a real-valued capture that produces mirrored spectra.

## Why this matters

Complex baseband separates positive and negative frequencies. If the I/Q order is wrong, the spectrum can be mirrored. If only a real-valued channel is used, positive and negative frequency content becomes symmetric and direction information is lost.

## Experiment

The script builds a complex tone at `120 kHz` and compares three cases:

- correct complex I/Q;
- I/Q swapped by exchanging the real and imaginary parts;
- real-valued capture that keeps only the I channel.

The lab measures:

- peak position for the correct complex signal;
- mirrored peak for the swapped-I/Q case;
- positive and negative mirror peaks for the real-valued capture.

## Run

From the repository root:

```bash
python blocks/block_02_signals_and_sampling/python/iq_visualization.py
```

Or run the representative lab pack:

```bash
python tools/run_all_labs.py
```

## Expected artifacts

| Artifact | Meaning |
|---|---|
| `docs/assets/lab23_iq_components_time.png` | I/Q components in the time domain |
| `docs/assets/lab23_iq_interpretation_spectra.png` | correct, swapped and mirrored spectral views |
| `docs/assets/lab23_iq_metrics.json` | peak locations and mirroring checks |

## Interpretation checks

- The correct complex I/Q case should show the main tone near `+120 kHz`.
- The swapped-I/Q case should mirror the tone to the negative side of the spectrum.
- The real-valued capture should show matching positive and negative peaks around `+/-120 kHz`.
- The metrics JSON should confirm a small error for the correct case and near-symmetric mirror peaks for the real-valued case.

## Report checklist

- [ ] Explain why complex baseband can distinguish spectral direction.
- [ ] Attach the time-domain I/Q plot and the spectral comparison plot.
- [ ] Quote the correct, swapped and mirrored peak locations.
- [ ] Explain what acquisition or parsing mistake produces an I/Q swap in practice.
- [ ] State how the same issue would appear in a real SDR recording workflow.
