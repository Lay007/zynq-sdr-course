# Lab 3.1 — FFT Windows and Spectral Leakage

## Goal

Understand how FFT window selection changes spectral leakage, frequency resolution, amplitude interpretation and measurement confidence.

This lab connects directly to SDR measurement work: if the FFT window and frequency axis are wrong, the measured spectrum can look convincing but lead to incorrect engineering conclusions.

## Theory

A finite-length FFT observes only a limited time window of the signal. If the signal frequency does not fall exactly on an FFT bin, the spectrum spreads into nearby bins. This is spectral leakage.

Important concepts:

- sampling rate `Fs`;
- FFT length `N`;
- bin spacing `df = Fs / N`;
- coherent vs non-coherent tone frequency;
- rectangular, Hann, Hamming and Blackman windows;
- main-lobe width;
- side-lobe suppression;
- amplitude correction.

## Experiment

Generate two complex tones:

1. a coherent tone exactly on an FFT bin;
2. a non-coherent tone between FFT bins.

For each tone, compute spectra using:

- rectangular window;
- Hann window;
- Hamming window;
- Blackman window.

Compare:

- peak bin;
- leakage level;
- apparent amplitude;
- frequency estimate error;
- ability to see a weak nearby tone.

## Python implementation

Minimum expected script structure:

```python
import numpy as np
import matplotlib.pyplot as plt

fs = 2.4e6
n = 4096
t = np.arange(n) / fs

f_bin = 250 * fs / n
f_off = (250.35) * fs / n

x = np.exp(1j * 2 * np.pi * f_off * t)

windows = {
    "rectangular": np.ones(n),
    "hann": np.hanning(n),
    "hamming": np.hamming(n),
    "blackman": np.blackman(n),
}

freq = np.fft.fftshift(np.fft.fftfreq(n, d=1/fs))

for name, w in windows.items():
    xw = x * w
    spec = np.fft.fftshift(np.fft.fft(xw))
    mag_db = 20 * np.log10(np.maximum(np.abs(spec) / np.sum(w), 1e-12))
    plt.plot(freq / 1e3, mag_db, label=name)

plt.grid(True)
plt.xlabel("Frequency, kHz")
plt.ylabel("Magnitude, dBFS")
plt.legend()
plt.show()
```

## MATLAB implementation

Minimum expected script structure:

```matlab
fs = 2.4e6;
N = 4096;
t = (0:N-1).' / fs;

f_bin = 250 * fs / N;
f_off = 250.35 * fs / N;

x = exp(1j * 2*pi*f_off*t);

windows = {
    'rectangular', ones(N, 1);
    'hann', hann(N);
    'hamming', hamming(N);
    'blackman', blackman(N)
};

freq = fftshift((-floor(N/2):ceil(N/2)-1).' * fs / N);

figure; hold on;
for k = 1:size(windows, 1)
    name = windows{k, 1};
    w = windows{k, 2};
    spec = fftshift(fft(x .* w));
    magDb = 20*log10(max(abs(spec) / sum(w), 1e-12));
    plot(freq/1e3, magDb, 'DisplayName', name);
end

grid on;
xlabel('Frequency, kHz');
ylabel('Magnitude, dBFS');
legend('Location', 'best');
```

## C++ / FPGA bridge

This lab is not only about plotting. The same FFT/window discipline appears in FPGA and embedded diagnostics.

Engineering bridge:

| Concept | Software view | FPGA / hardware view |
|---|---|---|
| Window coefficients | floating-point vector | ROM or coefficient memory |
| Multiplication by window | vector multiply | DSP slices or fixed-point multiplier |
| FFT length | array size | latency, memory and resource cost |
| Leakage | plot artifact | real measurement limitation |
| Amplitude correction | divide by window sum | fixed gain compensation |

## Expected plots

Produce at least:

1. coherent tone spectrum with multiple windows;
2. non-coherent tone spectrum with multiple windows;
3. zoomed view around the tone;
4. optional weak-tone detection case.

## Report checklist

- [ ] State `Fs`, `N`, `df` and tone frequency.
- [ ] Explain whether the tone is coherent with FFT bins.
- [ ] Compare main-lobe width for each window.
- [ ] Compare side-lobe suppression.
- [ ] Explain which window is best for amplitude measurement.
- [ ] Explain which window is best for detecting a weak nearby tone.
- [ ] Add a short note on FPGA cost of applying a window.

## Engineering conclusion template

```text
For this signal and FFT length, the ______ window gives the best leakage suppression,
but it increases the main-lobe width. For SDR measurements, this means that window
choice must be documented together with Fs, FFT length and amplitude normalization.
```
