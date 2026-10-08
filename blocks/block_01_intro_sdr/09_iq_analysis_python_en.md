# 09. Analysis of the Recorded Signal in Python

## Purpose of the section
To learn how to analyze a recorded IQ signal in Python and use a scripting approach to automate measurements.

## 1. Why Python is needed
Python is useful in the course as a fast universal tool. It allows the student to:

- read IQ files;
- plot graphs;
- compute FFT;
- automate repetitive measurements;
- prepare small utilities for processing recordings.

For engineering practice this is especially important because Python is well suited for quickly testing hypotheses.

## 2. Tasks of the analysis
Within the first block it is necessary to:

- read the IQ data file;
- convert the data to a complex signal;
- plot the time waveform;
- plot the spectrum;
- find the main tone frequency;
- save the results.

## 3. Recommended libraries
For the first analysis, the following are enough:

- `numpy`
- `matplotlib`

If needed, one can also use:

- `scipy`

## 4. General work sequence
1. Open the file.
2. Read the raw array.
3. Separate I and Q.
4. Form the complex array.
5. Plot the time waveform.
6. Compute FFT.
7. Find the spectral peak.
8. Output numerical results.

## 5. Example Python script
```python
import numpy as np
import matplotlib.pyplot as plt

filename = "tone_capture_iq.bin"
fs = 2.4e6

raw = np.fromfile(filename, dtype=np.int16)

i_data = raw[0::2]
q_data = raw[1::2]

x = i_data.astype(np.float64) + 1j * q_data.astype(np.float64)

n_view = min(len(x), 2000)
t = np.arange(n_view) / fs

plt.figure()
plt.plot(t, np.real(x[:n_view]))
plt.xlabel("Time, s")
plt.ylabel("Amplitude")
plt.title("Real part of IQ signal")
plt.grid(True)

nfft = 4096
X = np.fft.fftshift(np.fft.fft(x[:nfft], nfft))
f = np.fft.fftshift(np.fft.fftfreq(nfft, d=1/fs))

plt.figure()
plt.plot(f, 20 * np.log10(np.abs(X) + 1e-12))
plt.xlabel("Frequency, Hz")
plt.ylabel("Magnitude, dB")
plt.title("Spectrum of recorded tone")
plt.grid(True)

peak_index = np.argmax(np.abs(X))
peak_freq = f[peak_index]

print(f"Peak frequency: {peak_freq:.2f} Hz")

plt.show()
```

The script reads `int16` samples, the course `.ci16` format. A raw `rtl_sdr` file is unsigned 8-bit with an offset of 127.5, and an HDSDR recording is a WAV file; see the format table on page 07. The course readers of Lab 9.3 (`ci16`, `cu8`, `cf32`) and Lab 9.4 (WAV IQ) handle them for you.

## 5a. Run the course version and check it against a known tone
The same analysis, with the peak printed and the plot saved, is `blocks/block_01_intro_sdr/python/iq_analysis_example.py`. Before trusting it on a real recording, run it on a file whose answer you know. A 200 kHz tone sampled at 2.4 MS/s, written as `.ci16`, gives:

```text
samples: 65536, FFT length: 4096, bin width: 585.9 Hz
peak offset from the tuning frequency: 199804.7 Hz
peak above the median spectrum level: 63.6 dB
```

The peak is 195 Hz short of 200 kHz. That is not an error: the FFT only has bins every `fs/nfft = 585.9 Hz`, and 199 804.7 Hz is the bin nearest to the tone.

```bash
python blocks/block_01_intro_sdr/python/iq_analysis_example.py capture.ci16 --fs 2.4e6 --out spectrum.png
python blocks/block_01_intro_sdr/python/iq_analysis_example.py capture.cu8 --dtype uint8
```

## 6. What the student should see
### In the time domain
- a stable waveform;
- no random jumps;
- periodic structure.

### In the spectrum
- the main spectral peak;
- noise floor;
- possibly weak parasitic components.

## 7. Advantages of Python in this block
Python is convenient because it allows the student to quickly:

- change analysis parameters;
- process several files;
- automatically compute peak frequency;
- save plots;
- build simple measurement tools.

This is especially useful for later work with large amounts of IQ data.

## 8. What should be checked
During the analysis, make sure that:

- the correct data type is chosen;
- I and Q are not swapped;
- the sampling frequency is set correctly;
- a sufficiently long fragment is analyzed;
- the frequency scale is interpreted correctly.

## 9. What can be improved in the next script version
Later the student may extend the script by:

- adding a window function;
- estimating the noise-floor level;
- automatically finding several peaks;
- saving results to a file;
- building a spectrogram;
- comparing several recordings.

## 9a. Exercises
1. Write the same 200 kHz tone as an `rtl_sdr` file (`uint8`, offset 127.5) and analyse it with `--dtype uint8`. Then analyse the same file with the default `int16`. The wrong type gives a confident, wrong answer: a peak near −400 kHz, about 48 dB above the median. Why does a format error not look like noise?
2. Change `--nfft` from 4096 to 65536. How close does the peak get to 200 000 Hz, and what is the bin width now?
3. Swap I and Q in the loader. Where does the tone move, and why?

## 10. What to include in the report
It is recommended to include:

- the text or fragment of the Python script;
- a time-domain plot;
- a spectrum plot;
- the found peak frequency;
- a short conclusion.

## 11. Conclusions
After this stage the student should:

- be able to read an IQ file in Python;
- build a basic spectral analysis;
- automatically find the frequency of the test tone;
- use Python as a tool for engineering automation.
