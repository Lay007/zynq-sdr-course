# Lab 3.2 — FIR Low-Pass Filtering of IQ Data

## Goal

Design, apply and evaluate a low-pass FIR filter for complex IQ data.

The lab connects filtering theory with practical SDR processing and prepares the student for a future streaming FIR block in Verilog.

## Theory

A low-pass FIR filter is commonly used to isolate a baseband signal, suppress adjacent channels, reduce noise bandwidth or prepare a signal for decimation.

Important concepts:

- passband;
- stopband;
- transition bandwidth;
- filter order / number of taps;
- group delay;
- windowed-sinc design;
- convolution;
- complex IQ filtering;
- fixed-point coefficient quantization.

## Experiment

Generate or load complex IQ data with:

- desired low-frequency component;
- undesired high-frequency component;
- optional additive noise.

Then:

1. design a low-pass FIR filter;
2. plot filter impulse response;
3. plot filter frequency response;
4. filter the IQ data;
5. compare spectra before and after filtering;
6. measure basic signal quality improvement.

## Run the reference script

```bash
python blocks/block_03_dsp_basics/python/lab_3_2_fir_low_pass.py
```

The script is deterministic and writes:

```text
docs/assets/lab32_fir_low_pass.png
docs/assets/lab32_fir_low_pass_metrics.json
```

Run it first and read its numbers against the section *What to expect* below. Then write your own
version from the minimum structure that follows; the reference script is your answer key.

## Python implementation

Minimum structure for your own implementation:

```python
import numpy as np
import matplotlib.pyplot as plt

fs = 2.4e6
n = 32768
t = np.arange(n) / fs

wanted = np.exp(1j * 2*np.pi*120e3*t)
interferer = 0.35 * np.exp(1j * 2*np.pi*620e3*t)
noise = 0.03 * (np.random.randn(n) + 1j*np.random.randn(n))
x = wanted + interferer + noise

num_taps = 129
cutoff = 250e3
m = np.arange(num_taps) - (num_taps - 1) / 2
h = 2 * cutoff / fs * np.sinc(2 * cutoff / fs * m)
h *= np.blackman(num_taps)
h /= np.sum(h)

y = np.convolve(x, h, mode="same")

freq = np.fft.fftshift(np.fft.fftfreq(n, d=1/fs))
X = np.fft.fftshift(np.fft.fft(x))
Y = np.fft.fftshift(np.fft.fft(y))

plt.figure()
plt.plot(freq/1e3, 20*np.log10(np.maximum(np.abs(X), 1e-12)), label="before")
plt.plot(freq/1e3, 20*np.log10(np.maximum(np.abs(Y), 1e-12)), label="after")
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
N = 32768;
t = (0:N-1).' / fs;

wanted = exp(1j*2*pi*120e3*t);
interferer = 0.35 * exp(1j*2*pi*620e3*t);
noise = 0.03 * (randn(N,1) + 1j*randn(N,1));
x = wanted + interferer + noise;

numTaps = 129;
cutoff = 250e3;
m = (0:numTaps-1).' - (numTaps-1)/2;
h = 2*cutoff/fs * sinc(2*cutoff/fs * m);
h = h .* blackman(numTaps);
h = h ./ sum(h);

y = conv(x, h, 'same');

freq = fftshift((-floor(N/2):ceil(N/2)-1).' * fs / N);
X = fftshift(fft(x));
Y = fftshift(fft(y));

figure; hold on;
plot(freq/1e3, 20*log10(max(abs(X), 1e-12)), 'DisplayName', 'before');
plot(freq/1e3, 20*log10(max(abs(Y), 1e-12)), 'DisplayName', 'after');
grid on;
xlabel('Frequency, kHz');
ylabel('Magnitude, dB');
legend('Location', 'best');
```

## C++ bridge

The same FIR operation should later be implemented as a deterministic C++ primitive:

```cpp
std::vector<std::complex<float>> fir_filter(
    const std::vector<std::complex<float>>& x,
    const std::vector<float>& taps);
```

Minimum C++ validation:

- impulse response test;
- sine/tone attenuation test;
- MATLAB/Python vector comparison;
- coefficient normalization check;
- group delay check.

## FPGA / Verilog bridge

The FIR filter maps naturally to a streaming RTL block:

```text
clk, rst
in_valid,  in_i,  in_q
out_valid, out_i, out_q
```

Hardware questions:

- How many taps are required?
- How many multipliers are available?
- Is the FIR fully parallel or time-multiplexed?
- What is the coefficient word length?
- What is the accumulator width?
- What latency is acceptable?

## Expected plots

Produce at least:

1. FIR impulse response;
2. FIR magnitude response;
3. spectrum before filtering;
4. spectrum after filtering;
5. optional time-domain comparison.

## What to expect

Default run (129-tap Blackman windowed-sinc, cutoff 250 kHz, `Fs = 2.4 MS/s`; wanted tone
120 kHz, interferer 0.35 at 620 kHz, noise 0.03 rms, seed 32):

```text
Gain at 120 kHz / 620 kHz: -0.000 / -116.9 dB
-3 dB edge: 240.3 kHz, first -60 dB point: 296.9 kHz
Transition width (-3 to -60 dB): 56.6 kHz
Stopband peak above 400 kHz: float -89.7 dB, Q1.15 -71.0 dB
Group delay: 64 samples (26.67 us)
Interferer: -9.1 -> -126.1 dBFS (suppression 116.9 dB), wanted change -0.000 dB
```

- **The -3 dB edge is 240 kHz, not the 250 kHz "cutoff".** In a windowed-sinc design the cutoff
  parameter is the -6 dB point; the transition band is spread symmetrically around it.
- **Transition width 56.6 kHz** is set by the number of taps and the window, not by the cutoff.
  A useful rule for Blackman is `transition ≈ 5.5 * Fs / N_taps`, here about 100 kHz for the full
  0-to-stopband span; measured from -3 to -60 dB it is 57 kHz.
- **The interferer drops 116.9 dB, exactly the filter gain at 620 kHz**, while the wanted tone is
  untouched (0.000 dB): in a linear filter the measured suppression *is* the frequency response.
- **Group delay is 64 samples, (N-1)/2**, for every frequency, because the taps are symmetric
  (linear phase). In hardware this is latency you must budget for.
- **Quantizing the taps to Q1.15 lifts the stopband from -89.7 to -71.0 dB.** The small outer
  taps of a long filter are only a few LSB in 16 bits; their rounding error is a noise floor on
  the response. This is why coefficient width is a design decision, not a formality.

![FIR response and spectra before/after filtering](/zynq-sdr-course/assets/lab32_fir_low_pass.png)

## Exercises

1. Call `design_lowpass(num_taps=...)` with 33, 65, 129 and 257 taps and read the gain at 620 kHz
   (expected about -79, -96, -117 and -153 dB). How does the first -60 dB point move? What does
   doubling the taps cost in an FPGA?
2. Quantize the taps to 12 bits instead of 16. Where does the stopband floor land? How many
   coefficient bits does a 100 dB stopband need?
3. Replace `np.blackman` with `np.hanning`. Compare transition width and stopband peak.
4. Move the interferer to 280 kHz, inside the transition band. What suppression do you get, and
   what does this tell you about guard bands between channels?

## Report checklist

- [ ] State `Fs`, cutoff frequency and number of taps.
- [ ] Plot and explain FIR frequency response.
- [ ] Estimate transition bandwidth.
- [ ] Explain group delay.
- [ ] Compare spectrum before/after filtering.
- [ ] Estimate suppression of the interferer.
- [ ] Explain what changes in fixed-point implementation.
- [ ] Describe how this FIR would map to Verilog.

## Engineering conclusion template

```text
The FIR low-pass filter suppresses the unwanted component by approximately ____ dB.
The cost is ____ samples of group delay and ____ taps, which directly affects
FPGA multiplier count, accumulator width and latency.
```
