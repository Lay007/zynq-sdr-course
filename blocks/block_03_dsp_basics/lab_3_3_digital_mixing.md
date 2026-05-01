# Lab 3.3 — Digital Mixing and Frequency Shift

## Goal

Shift a complex IQ signal in frequency using a numerically controlled oscillator (NCO) and complex multiplication.

This lab is the direct bridge between SDR software processing and FPGA blocks such as DDS/NCO, complex multiplier, frequency translator and digital downconverter.

## Theory

Digital mixing multiplies the input complex signal by a complex exponential:

```text
y[n] = x[n] * exp(j * 2*pi*f_shift*n/Fs)
```

For a complex baseband signal, this shifts the spectrum by `f_shift`.

Important concepts:

- complex sinusoid;
- NCO / DDS;
- phase accumulator;
- frequency resolution;
- complex multiplication;
- positive and negative frequency shifts;
- spectral images and wraparound;
- fixed-point phase and sine/cosine representation.

## Experiment

Generate or load an IQ signal with a tone or modulated waveform located away from DC.

Then:

1. estimate or define the input frequency offset;
2. generate an NCO;
3. multiply the signal by the NCO;
4. compare spectra before and after frequency shift;
5. verify that the target signal moves to the expected frequency;
6. discuss NCO frequency resolution and fixed-point phase accumulator width.

## Python implementation

Minimum expected script structure:

```python
import numpy as np
import matplotlib.pyplot as plt

fs = 2.4e6
n = 32768
t = np.arange(n) / fs

f0 = 420e3
x = np.exp(1j * 2*np.pi*f0*t)

f_shift = -420e3
nco = np.exp(1j * 2*np.pi*f_shift*t)
y = x * nco

freq = np.fft.fftshift(np.fft.fftfreq(n, d=1/fs))
X = np.fft.fftshift(np.fft.fft(x * np.hanning(n)))
Y = np.fft.fftshift(np.fft.fft(y * np.hanning(n)))

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

f0 = 420e3;
x = exp(1j*2*pi*f0*t);

fShift = -420e3;
nco = exp(1j*2*pi*fShift*t);
y = x .* nco;

freq = fftshift((-floor(N/2):ceil(N/2)-1).' * fs / N);
X = fftshift(fft(x .* hann(N)));
Y = fftshift(fft(y .* hann(N)));

figure; hold on;
plot(freq/1e3, 20*log10(max(abs(X), 1e-12)), 'DisplayName', 'before');
plot(freq/1e3, 20*log10(max(abs(Y), 1e-12)), 'DisplayName', 'after');
grid on;
xlabel('Frequency, kHz');
ylabel('Magnitude, dB');
legend('Location', 'best');
```

## C++ bridge

A future C++ primitive should separate NCO generation from complex multiplication:

```cpp
struct NcoState {
    uint64_t phase;
    uint64_t phase_step;
};

std::complex<float> next_nco_sample(NcoState& nco);
std::complex<float> mix_sample(std::complex<float> x, std::complex<float> osc);
```

Validation tests:

- generated frequency matches target shift;
- phase continuity is preserved;
- positive and negative shifts are correct;
- mixed tone lands at expected FFT bin;
- fixed-point NCO error is bounded.

## FPGA / Verilog bridge

Hardware mapping:

| Function | RTL block |
|---|---|
| phase accumulation | NCO phase accumulator |
| sine/cosine generation | LUT, CORDIC or vendor DDS |
| complex multiply | four multipliers or optimized three-multiplier form |
| output scaling | fixed-point rounding and saturation |

Streaming interface target:

```text
clk, rst
in_valid,  in_i,  in_q
out_valid, out_i, out_q
```

## NCO frequency resolution

For an accumulator of width `A` bits:

```text
df = Fs / 2^A
```

| Accumulator width | Frequency resolution |
|---:|---|
| 24 bit | `Fs / 16,777,216` |
| 32 bit | `Fs / 4,294,967,296` |
| 48 bit | `Fs / 281,474,976,710,656` |

## Expected plots

Produce at least:

1. spectrum before mixing;
2. spectrum after mixing;
3. zoomed view around target frequency;
4. optional phase accumulator trace;
5. optional NCO quantization error plot.

## Report checklist

- [ ] State `Fs`, input tone frequency and target shift.
- [ ] Show the complex NCO equation.
- [ ] Plot spectrum before and after mixing.
- [ ] Verify the final frequency location.
- [ ] Explain positive vs negative frequency shifts.
- [ ] Calculate NCO resolution for at least 32-bit phase accumulator.
- [ ] Explain how the mixer maps to FPGA.
- [ ] Discuss fixed-point scaling and saturation.

## Engineering conclusion template

```text
Digital mixing shifts the signal from ____ kHz to ____ kHz. In FPGA, the same
operation becomes an NCO plus complex multiplier. The main hardware trade-offs
are phase accumulator width, sine/cosine generation method, multiplier count and
output scaling.
```
