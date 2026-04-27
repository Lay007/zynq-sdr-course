import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import firwin, lfilter, freqz

# Parameters
Fs = 1e6
N = 4096

t = np.arange(N)/Fs

# Signal: useful tone + interference
f_sig = 50e3
f_int = 250e3

x = np.exp(1j*2*np.pi*f_sig*t) + 0.5*np.exp(1j*2*np.pi*f_int*t)

# FIR design
cutoff = 100e3
num_taps = 101

h = firwin(num_taps, cutoff/(Fs/2))

# Filtering
y = lfilter(h, 1.0, x)

# FFT helper
def plot_fft(sig, title):
    X = np.fft.fftshift(np.fft.fft(sig))
    f = np.fft.fftshift(np.fft.fftfreq(len(sig), 1/Fs))
    plt.plot(f/1e3, 20*np.log10(np.abs(X)+1e-12))
    plt.title(title)
    plt.xlabel("Frequency (kHz)")
    plt.ylabel("Magnitude (dB)")

# Plot
plt.figure(figsize=(10,8))

plt.subplot(3,1,1)
plot_fft(x, "Before filtering")

plt.subplot(3,1,2)
w, H = freqz(h, worN=1024)
plt.plot(w/np.pi*(Fs/2)/1e3, 20*np.log10(np.abs(H)+1e-12))
plt.title("FIR Frequency Response")
plt.xlabel("Frequency (kHz)")
plt.ylabel("Magnitude (dB)")

plt.subplot(3,1,3)
plot_fft(y, "After filtering")

plt.tight_layout()
plt.show()
