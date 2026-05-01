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

## Python implementation

Minimum expected script structure:

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

Minimum expected script structure:

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
