# 03. FFT and the frequency axis

## The problem

The FFT returns bin indices, not physical frequencies.

## Correct frequency axis formula

```text
f[k] = (k − N/2) × Fs / N
```

After centering the FFT output (fftshift), bin `k` corresponds to frequency
`f[k]` relative to the receiver's center frequency.

## Relation to SDR

```text
f_absolute = Fc + f_baseband
```

where `Fc` is the receiver LO center frequency and `f_baseband` is the
baseband offset calculated above.

## Common mistakes

| Mistake | Symptom |
|---|---|
| Wrong `Fs` used | incorrect frequency scale |
| Missing `Fc` offset | cannot map baseband peak to RF frequency |
| FFT shift not applied | spectrum appears "shifted" or wrapped |

## Mini lab

1. Plot the FFT with raw bin indices (no frequency axis).
2. Plot the FFT with the correct axis using the formula above.
3. Compare the two plots and confirm the peak appears at the expected frequency.
