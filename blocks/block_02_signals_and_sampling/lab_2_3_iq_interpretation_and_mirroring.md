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

## What to expect

```text
Correct peak: 119995.117 Hz
I/Q swapped peak: -119995.117 Hz
Real-valued positive/negative peaks: 119995.117/-119995.117 Hz
```

- **Swapping I and Q mirrors the spectrum exactly**: +120 kHz becomes -120 kHz. Swapping the two
  parts turns `x` into `j * conj(x)`, and conjugation reverses the direction of rotation.
- **A real-valued capture shows both +120 and -120 kHz with equal height**. A real signal cannot
  tell the two directions apart; this is why an SDR delivers two channels, I and Q.
- A mirrored spectrum is the typical symptom of a wrong `i_first` setting or of a receiver that
  uses the other sign convention for the LO. Nothing in the samples says which one is right, so
  it has to be recorded in the metadata and checked with a known tone.

## Exercises

1. Conjugate the correct signal (`np.conj(x)`) instead of swapping I and Q. Compare the peak with
   the swapped case. Why are they equal?
2. You record a known FM station that should appear at +300 kHz and it appears at -300 kHz.
   List two possible causes and one experiment that separates them.
3. Why does the real-valued capture need twice the sample rate of the complex one to cover the
   same bandwidth?

<details markdown="1">
<summary>Answers (checked by running the lab script)</summary>

1. Swapping I and Q gives `Q + jI = j·conj(x)`: the conjugate multiplied by a constant phase. The magnitude spectrum is the same, so both move the tone to `−f` at the same level.
2. Either the I/Q order or the sign of Q is wrong somewhere in the capture or the reader, or the RF chain inverts the spectrum (a mixing stage with the LO above the signal). To separate them, open the same recording in a different program (HDSDR, SDR++): if it shows +300 kHz, your reader is at fault; if every program shows −300 kHz, the inversion happened before the file was written.
3. A real signal's spectrum is symmetric, `X(−f) = X*(f)`, so the samples carry only 0 to `Fs/2` uniquely; a complex signal carries −`Fs/2` to +`Fs/2`. The amount of data is the same: the complex stream has two real numbers per sample.

</details>

## Report checklist

- [ ] Explain why complex baseband can distinguish spectral direction.
- [ ] Attach the time-domain I/Q plot and the spectral comparison plot.
- [ ] Quote the correct, swapped and mirrored peak locations.
- [ ] Explain what acquisition or parsing mistake produces an I/Q swap in practice.
- [ ] State how the same issue would appear in a real SDR recording workflow.
