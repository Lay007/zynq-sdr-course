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

## Run the reference script

```bash
python blocks/block_03_dsp_basics/python/lab_3_1_fft_windows.py
```

The script is deterministic and writes:

```text
docs/assets/lab31_fft_windows_leakage.png
docs/assets/lab31_fft_windows_metrics.json
```

Run it first and read its numbers against the section *What to expect* below. Then write your own
version from the minimum structure that follows; the reference script is your answer key.

## Python implementation

Minimum structure for your own implementation:

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

Minimum structure for your own implementation:

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

## What to expect

Default run (`Fs = 2.4 MS/s`, `N = 4096`, bin spacing 585.94 Hz; a full-scale tone 0.35 bin off
bin 250, and a second tone at -60 dBc exactly 12 bins above bin 250):

```text
window         ENBW  scallop  leak@20  weak vis
rectangular    1.00    1.83dB   -35.0dB    -27.7dB
hann           1.50    0.69dB   -87.8dB     14.8dB
hamming        1.36    0.85dB   -52.7dB    -10.8dB
blackman       1.73    0.54dB   -95.4dB     22.5dB
```

- **ENBW** (equivalent noise bandwidth, in bins) is the price of a window: 1.0 for rectangular,
  exactly 1.5 for Hann, 1.73 for Blackman. A wider ENBW lets more noise into each bin, so a
  noise-floor reading in dB/bin rises by `10*log10(ENBW)`: +1.8 dB for Hann, +2.4 dB for Blackman.
- **Scalloping loss** is how much an off-bin tone reads low. With a rectangular window a tone
  0.35 bin off-grid reads 1.83 dB low; Blackman loses only 0.54 dB. If you read tone amplitudes
  off an FFT, this is an amplitude error, not a signal change.
- **Leakage 20 bins away** is where windows really differ: -35 dBc for rectangular against
  -88 to -95 dBc for Hann and Blackman.
- **Weak-tone visibility** puts it together. With a rectangular window the -60 dBc neighbour sits
  **27.7 dB under the leakage skirt** of the strong tone and is invisible. Hamming (-10.8 dB) is
  not enough either: its far side lobes fall slowly. Hann shows it 14.8 dB above the skirt,
  Blackman 22.5 dB. The same weak signal is either "not there" or clearly present depending
  only on a processing choice.

![Non-coherent tone with a -60 dBc neighbour under four windows](/zynq-sdr-course/assets/lab31_fft_windows_leakage.png)

## Exercises

1. Change `NONCOHERENT_BIN` from 250.35 to 250.5 (the worst case, exactly between two bins).
   How much does the rectangular scalloping loss grow? The textbook value is 3.92 dB.
2. Move the weak tone from 12 bins to 40 bins away (`WEAK_OFFSET_BINS`). Does Hamming now show
   it? Why does the answer depend on distance for Hamming but hardly for Blackman?
3. Double `N` to 8192 while keeping `Fs`. What happens to the bin spacing, and to the leakage
   *in hertz* at a fixed frequency offset?
4. You must report the noise floor of a capture in dBm/Hz. Which correction do you apply for a
   Blackman window, and by how many dB?

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
