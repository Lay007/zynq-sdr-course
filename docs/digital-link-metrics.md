# Digital-link metric calculations

This page fixes the definitions used in the course's hardware BPSK/QPSK reports. A number without a description of the synchronization algorithm, the normalization and the sample size does not count as sufficient evidence.

## IQ preparation

A stereo WAV is converted to complex samples

```text
x[n] = I[n] + j*Q[n]
```

The values are normalized to the ADC full scale. One DC estimate is subtracted from the whole recording:

```text
mu = (1/N) * sum(x[n]), n=0..N-1
x0[n] = x[n] - mu
```

The mean of an individual burst is not subtracted: a finite deterministic sequence need not have an exactly zero mean, so that operation could alter the wanted signal.

## Burst and frame detection

For the energy detector the recording is split into blocks of `B = 256` samples:

```text
P[m] = (1/B) * sum(|x0[m*B+n]|^2), n=0..B-1
```

The threshold is set robustly relative to the median block power:

```text
P_threshold = median(P) + 10 * MAD(P)
```

A candidate must also peak above `median + 15·MAD`. Adjacent active blocks are merged into one burst. After the RRC matched filter the frame is checked against the known sequence from the RTL ROM. The normalized correlation is

```text
rho = |sum(r[k] * conj(s[k]))|
      / sqrt(sum(|r[k]|^2) * sum(|s[k]|^2))
```

In Lab 11.28 the detector accepts a frame at `rho >= 0.8`. Hardware frames gave `0.898…0.983`; control windows between bursts gave about `0.37…0.61`.

## CFO estimate and complex alignment

For the known QPSK symbols the phase error is

```text
phi[k] = unwrap(arg(r[k] * conj(s[k])))
```

A linear fit `phi[k] ~= phi0 + alpha*k` gives the residual frequency offset

```text
delta_f = alpha * symbol_rate / (2*pi)
        = alpha * sample_rate / (2*pi*SPS)
```

After the CFO correction one complex channel coefficient is estimated by least squares:

```text
g = sum(conj(s[k]) * r[k]) / sum(|s[k]|^2)
r_aligned[k] = r[k] * exp(-j*alpha*k) / g
```

This alignment removes a constant gain/phase and a linear CFO within the frame. It does not correct nonlinearity, IQ imbalance, timing jitter or a frequency-selective channel.

## BER and FER

QPSK decisions are taken from the signs of I/Q. For `N_b` known bits:

```text
BER = bit_errors / compared_bits
```

With equal frame lengths the aggregate BER is computed over all detected frames:

```text
BER_aggregate = sum(bit_errors_per_frame)
                / (detected_frames * bits_per_frame)
```

The frame error rate counts a frame as failed if it has at least one bit error:

```text
FER = frames_with_at_least_one_error / detected_frames
```

`BER = 0` is always reported together with the number of compared bits. For zero errors the approximate 95 % rule-of-three bound `BER < 3/N_b` is given. It is not a proven BER floor.

## EVM

RMS EVM is computed after the CFO correction and the complex scalar alignment:

```text
EVM_RMS_percent = 100 * sqrt(
    sum(|r_aligned[k] - s[k]|^2) / sum(|s[k]|^2)
)
```

EVM combines noise and residual distortion. A smaller EVM usually improves BER, but a one-to-one relation between them exists only for a fixed modulation, synchronization and channel model.

## SNR from EVM

The QPSK OTA analyzer does not measure SNR from a separate calibrated noise-only interval. It publishes a diagnostic estimate

```text
evm_fraction = EVM_RMS_percent / 100
SNR_from_EVM_dB = -20 * log10(evm_fraction)
```

It equals the SNR only when uncorrelated additive noise dominates and the synchronization is correct. That is why the field is called `snr_from_evm_db` and not calibrated RF SNR.

## Clipping, levels and crest factor

The clipping fraction is computed before the DC correction as the share of complex samples in which at least one axis nearly reaches full scale:

```text
clipping_fraction = count(|I[n]| > 0.999 or |Q[n]| > 0.999) / N
```

The complex peak/RMS levels in dBFS are stored as well, and

```text
crest_factor_dB = peak_level_dBFS - rms_level_dBFS
```

A zero clipping fraction rules out digital saturation in the recording, but does not prove the absence of analog compression before the ADC.

## Confidence intervals and limits

- The share of error-free bursts uses a two-sided Wilson 95 % interval.
- The aggregate BER also gets a Wilson interval, as a descriptive estimate. Errors within one RF burst can be correlated, so the model of independent Bernoulli trials is an approximation.
- Detection rate, normalized correlation, FER, BER, EVM and CFO must be read together.
- The best frame does not replace the distribution over all frames; the main Lab 11.28 report uses every detected burst.
- Absolute SNR, power and an uncertainty budget need a calibrated path and a separate noise measurement.

For `k` successes in `n` trials, `p_hat = k/n` and `z = 1.959964`, the Wilson bounds are

```text
denom  = 1 + z^2/n
center = (p_hat + z^2/(2*n)) / denom
half   = z * sqrt(p_hat*(1-p_hat)/n + z^2/(4*n^2)) / denom
interval_95 = [center-half, center+half]
```

For BER the same formula is applied to the number of bit errors, but the result is labelled descriptive because the errors may be correlated.
