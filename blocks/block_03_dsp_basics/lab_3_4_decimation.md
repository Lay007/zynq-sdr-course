# Lab 3.4 — Decimation with Anti-Aliasing Filter

## Goal

Reduce the sample rate of an IQ signal without corrupting the spectrum.

This lab connects multirate DSP theory with SDR receiver implementation and future FPGA rate-change blocks.

## Theory

Decimation by factor `M` keeps every `M`-th sample:

```text
y[k] = x[kM]
```

However, direct downsampling causes aliasing unless the signal is first filtered by a low-pass anti-aliasing filter.

Important concepts:

- decimation factor;
- new sample rate `Fs_out = Fs_in / M`;
- anti-aliasing filter;
- transition band;
- guard band;
- polyphase FIR implementation;
- FPGA resource/latency trade-off.

## Experiment

Generate or load complex IQ data with:

- wanted signal near DC;
- unwanted signal outside the future Nyquist band;
- optional noise.

Then compare:

1. direct downsampling without anti-aliasing;
2. FIR low-pass filtering followed by downsampling;
3. spectra before and after decimation;
4. alias location and suppression.

## Run the reference script

```bash
python blocks/block_03_dsp_basics/python/lab_3_4_decimation.py
```

The script is deterministic and writes:

```text
docs/assets/lab34_decimation.png
docs/assets/lab34_decimation_metrics.json
```

Run it first and read its numbers against the section *What to expect* below. Then write your own
version from the minimum structure that follows; the reference script is your answer key.

## Python implementation

Minimum structure for your own implementation:

```python
import numpy as np
import matplotlib.pyplot as plt

fs = 2.4e6
M = 4
fs_out = fs / M
n = 65536
t = np.arange(n) / fs

wanted = np.exp(1j * 2*np.pi*80e3*t)
interferer = 0.5 * np.exp(1j * 2*np.pi*520e3*t)
x = wanted + interferer

# Bad path: no anti-aliasing
y_bad = x[::M]

# Good path: FIR anti-aliasing before decimation
num_taps = 129
cutoff = 0.40 * fs_out
m = np.arange(num_taps) - (num_taps - 1) / 2
h = 2 * cutoff / fs * np.sinc(2 * cutoff / fs * m)
h *= np.blackman(num_taps)
h /= np.sum(h)

x_filt = np.convolve(x, h, mode="same")
y_good = x_filt[::M]

freq_in = np.fft.fftshift(np.fft.fftfreq(n, d=1/fs))
freq_out = np.fft.fftshift(np.fft.fftfreq(len(y_good), d=1/fs_out))

X = np.fft.fftshift(np.fft.fft(x * np.hanning(n)))
Y_bad = np.fft.fftshift(np.fft.fft(y_bad * np.hanning(len(y_bad))))
Y_good = np.fft.fftshift(np.fft.fft(y_good * np.hanning(len(y_good))))

plt.figure()
plt.plot(freq_out/1e3, 20*np.log10(np.maximum(np.abs(Y_bad), 1e-12)), label="bad: no anti-alias")
plt.plot(freq_out/1e3, 20*np.log10(np.maximum(np.abs(Y_good), 1e-12)), label="good: FIR + decimate")
plt.grid(True)
plt.xlabel("Frequency, kHz")
plt.ylabel("Magnitude, dB")
plt.legend()
plt.show()
```

## MATLAB implementation

Minimum structure for your own implementation:

```matlab
fs = 2.4e6;
M = 4;
fsOut = fs / M;
N = 65536;
t = (0:N-1).' / fs;

wanted = exp(1j*2*pi*80e3*t);
interferer = 0.5 * exp(1j*2*pi*520e3*t);
x = wanted + interferer;

% Bad path: no anti-aliasing
yBad = x(1:M:end);

% Good path: FIR anti-aliasing before decimation
numTaps = 129;
cutoff = 0.40 * fsOut;
m = (0:numTaps-1).' - (numTaps-1)/2;
h = 2*cutoff/fs * sinc(2*cutoff/fs * m);
h = h .* blackman(numTaps);
h = h ./ sum(h);

xFilt = conv(x, h, 'same');
yGood = xFilt(1:M:end);

freqOut = fftshift((-floor(numel(yGood)/2):ceil(numel(yGood)/2)-1).' * fsOut / numel(yGood));
YBad = fftshift(fft(yBad .* hann(numel(yBad))));
YGood = fftshift(fft(yGood .* hann(numel(yGood))));

figure; hold on;
plot(freqOut/1e3, 20*log10(max(abs(YBad), 1e-12)), 'DisplayName', 'bad: no anti-alias');
plot(freqOut/1e3, 20*log10(max(abs(YGood), 1e-12)), 'DisplayName', 'good: FIR + decimate');
grid on;
xlabel('Frequency, kHz');
ylabel('Magnitude, dB');
legend('Location', 'best');
```

## C++ bridge

A future C++ decimator should make the anti-aliasing filter explicit:

```cpp
std::vector<std::complex<float>> decimate_fir(
    const std::vector<std::complex<float>>& x,
    const std::vector<float>& taps,
    int factor);
```

Validation tests:

- output sample rate is correct;
- output length is correct;
- passband tone is preserved;
- out-of-band tone is suppressed before downsampling;
- direct downsampling failure case is reproducible.

## FPGA / Verilog bridge

A hardware decimator can be implemented as:

```text
input stream -> FIR anti-alias filter -> downsample-by-M enable -> output stream
```

More efficient implementation:

```text
polyphase FIR decimator
```

Hardware questions:

- What is the decimation factor?
- What stopband attenuation is required?
- Can the FIR run at input sample rate?
- Is polyphase decomposition needed?
- What is the output valid pattern?
- What is the latency?

## Expected plots

Produce at least:

1. input spectrum;
2. output spectrum without anti-aliasing;
3. output spectrum with FIR anti-aliasing;
4. optional zoom around aliased component;
5. optional FIR response.

## What to expect

Default run (`Fs_in = 2.4 MS/s`, `M = 4`, `Fs_out = 600 kS/s`; wanted tone +80 kHz, interferer 0.5 at
+520 kHz; 129-tap Blackman low-pass with cutoff `0.4 * Fs_out = 240 kHz`):

```text
Fs in/out: 2.4 / 600 kS/s, new Nyquist band +/-300 kHz
520 kHz interferer is predicted to alias to -80 kHz
Alias relative to wanted tone: no filter -6.0 dBc, with FIR -111.8 dBc
Alias suppression by the anti-aliasing filter: 105.8 dB
```

- **Predict before you measure.** A complex tone lands at `((f + Fs_out/2) mod Fs_out) - Fs_out/2`:
  520 kHz folds to 520 - 600 = **-80 kHz**, the mirror of the wanted +80 kHz. The script's
  `alias_hz()` does exactly this arithmetic.
- **Without a filter the alias is -6 dBc**, i.e. the interferer's full 0.5 amplitude, now sitting
  inside the band as if it were a real signal at -80 kHz. Nothing in the decimated data tells you
  it came from 520 kHz. Aliasing is irreversible.
- **Filtering first removes it: -111.8 dBc, 105.8 dB of suppression.** The filter must act at the
  *input* rate, before samples are discarded; that is why decimators are expensive and why a
  polyphase structure (compute only the samples you keep) saves a factor of `M` in multipliers.

![Decimation with and without anti-aliasing](/zynq-sdr-course/assets/lab34_decimation.png)

## Exercises

1. Use `alias_hz()` to predict where 250, 310, 350 and 700 kHz land at 600 kS/s (expected 250,
   -290, -250 and +100 kHz). Which of them are dangerous for a channel at +80 kHz?
2. Reduce the filter to 17, 33 and 65 taps (expected alias about -40, -86 and -106 dBc). What is the
   shortest filter that keeps the alias 60 dB below the wanted tone?
3. Move the interferer to 290 kHz, just inside the new Nyquist band but beyond the filter's
   passband. It does not alias. Does it still reach the output, and how strongly?
4. Compute the multiply count per output sample for the direct filter and for a polyphase version
   with the same 129 taps.

## Report checklist

- [ ] State `Fs_in`, decimation factor and `Fs_out`.
- [ ] Identify the new Nyquist band.
- [ ] Show why direct downsampling fails.
- [ ] Design the anti-aliasing filter.
- [ ] Compare spectra before/after decimation.
- [ ] Estimate alias suppression.
- [ ] Explain polyphase decimator advantage.
- [ ] Describe FPGA valid-rate behavior.

## Engineering conclusion template

```text
Direct downsampling aliases the ____ kHz component into the output band.
The FIR anti-aliasing filter suppresses it by approximately ____ dB before
rate reduction. In FPGA, this block should be implemented as a FIR decimator
or polyphase decimator depending on resource and sample-rate constraints.
```
