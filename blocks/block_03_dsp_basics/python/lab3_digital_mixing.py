import numpy as np
import matplotlib.pyplot as plt

Fs = 1e6
N = 4096

t = np.arange(N)/Fs

# input tone
f_sig = 50e3
x = np.exp(1j*2*np.pi*f_sig*t)

# frequency shift
f_shift = 100e3
nco = np.exp(1j*2*np.pi*f_shift*t)

y = x * nco

# FFT helper

def plot_fft(sig, title):
    X = np.fft.fftshift(np.fft.fft(sig))
    f = np.fft.fftshift(np.fft.fftfreq(len(sig), 1/Fs))
    plt.plot(f/1e3, 20*np.log10(np.abs(X)+1e-12))
    plt.title(title)
    plt.xlabel("Frequency (kHz)")
    plt.ylabel("Magnitude (dB)")

plt.figure(figsize=(10,6))

plt.subplot(2,1,1)
plot_fft(x, "Before mixing")

plt.subplot(2,1,2)
plot_fft(y, "After mixing")

plt.tight_layout()
plt.show()
