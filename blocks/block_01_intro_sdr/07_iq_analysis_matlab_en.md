# 07. Analysis of the Recorded Signal in MATLAB

## Purpose of the section
To learn how to load a recorded IQ file into MATLAB, build time-domain and spectral representations of the signal, and estimate the main parameters of the test tone.

## 1. Why MATLAB analysis is needed
After observing the signal in HDSDR, it is important to move to offline analysis. This allows the student to:

- work with the same recording many times;
- repeat calculations;
- compare analysis methods;
- estimate frequency and level;
- prepare for later modeling in Simulink.

MATLAB is especially convenient for the first analysis because it allows quick:
- reading of data;
- plotting;
- FFT computation;
- automation of simple measurements.

## 2. What should be known about the recorded file
Before starting the analysis, the following must be documented:
- file name;
- sample format;
- sampling rate;
- receiver tuning frequency;
- data type;
- order of I and Q samples.

A common format is:
- interleaved I/Q;
- `int8`, `int16`, or `float`;
- a sequence of the form  
  `I0, Q0, I1, Q1, I2, Q2, ...`

## 3. Main analysis tasks
Within the first block it is necessary to:

1. Load the IQ file.
2. Convert it into a complex signal.
3. Plot a fragment of the time-domain waveform.
4. Plot the spectrum.
5. Find the frequency of the main peak.
6. Estimate the tone level.
7. Save the results for the report.

## 4. General work sequence
### Step 1. Load the data
Read the raw file into an array.

### Step 2. Form the complex signal
Combine I and Q into a complex vector:
- I — real part;
- Q — imaginary part.

### Step 3. Normalize if needed
Bring the values to a convenient range.

### Step 4. Time-domain analysis
Plot the real part, imaginary part, or magnitude of the signal.

### Step 5. Spectral analysis
Compute FFT and obtain the spectral picture.

### Step 6. Peak estimation
Find the maximum index and convert it into frequency.

## 5. Example structure of a MATLAB script
```matlab
filename = 'tone_capture_iq.bin';
fs = 2.4e6;

fid = fopen(filename, 'rb');
raw = fread(fid, 'int16');
fclose(fid);

i_data = raw(1:2:end);
q_data = raw(2:2:end);

x = double(i_data) + 1j * double(q_data);

Nview = min(length(x), 2000);
t = (0:Nview-1)/fs;

figure;
plot(t, real(x(1:Nview)));
xlabel('Time, s');
ylabel('Amplitude');
title('Real part of IQ signal');
grid on;

Nfft = 4096;
X = fftshift(fft(x(1:Nfft), Nfft));
f = (-Nfft/2:Nfft/2-1)*(fs/Nfft);

figure;
plot(f, 20*log10(abs(X)+1e-12));
xlabel('Frequency, Hz');
ylabel('Magnitude, dB');
title('Spectrum of recorded tone');
grid on;

[~, idx] = max(abs(X));
f_peak = f(idx);

disp(['Peak frequency = ', num2str(f_peak), ' Hz']);
```

## 6. What should be seen on the plots
### In the time domain
The student should see:
- regular oscillation;
- a stable signal shape;
- no obvious spikes or strong distortion.

### In the spectrum
The student should see:
- a pronounced narrow peak;
- peak location corresponding to the tone;
- noise floor;
- possibly weak parasitic components.

## 7. Useful parameters to estimate
Within the first analysis it is useful to determine:
- frequency of the maximum spectral peak;
- relative peak level;
- peak width;
- noise-floor level;
- possible mirror components;
- possible DC component near zero frequency.

## 8. What to pay attention to
### 1. Data format
If the type or I/Q order is wrong, the spectrum will be incorrect.

### 2. Frequency scale
Sampling frequency and center frequency must be interpreted correctly.

### 3. Analysis window
Too short a fragment may degrade frequency resolution.

### 4. Overload
If the receiver was overloaded, this may appear as:
- extra peaks;
- a wide “dirty” spectrum;
- time-domain distortion.

## 9. What to include in the report
It is recommended to add:
- a short description of the file used;
- recording parameters;
- time-domain plot;
- spectrum plot;
- estimated peak frequency;
- a short comment on signal quality.

## 10. Conclusions
After this stage the student should:
- be able to load an IQ file into MATLAB;
- build a time-domain waveform and a spectrum;
- determine the frequency of the main tone;
- understand how offline analysis confirms the observation made in HDSDR.
