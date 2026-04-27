import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

OUTPUT_DIR = Path("docs/assets")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# IEEE-style plotting defaults
plt.rcParams.update({
    "figure.figsize": (6, 4),
    "font.size": 10,
    "axes.grid": True,
    "grid.alpha": 0.3,
})


def generate_tone_fft():
    fs = 1e6
    t = np.arange(0, 0.01, 1/fs)
    f0 = 100e3
    signal = np.exp(2j * np.pi * f0 * t)

    spectrum = np.fft.fftshift(np.fft.fft(signal))
    freqs = np.fft.fftshift(np.fft.fftfreq(len(signal), 1/fs))

    plt.figure()
    plt.plot(freqs / 1e3, 20*np.log10(np.abs(spectrum)))
    plt.xlabel("Frequency (kHz)")
    plt.ylabel("Magnitude (dB)")
    plt.title("Tone FFT Spectrum")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "lab01_fft.png")
    plt.close()


def generate_qpsk_constellation():
    np.random.seed(0)
    symbols = (2*(np.random.randint(0, 2, 1000)-0.5) +
               1j*2*(np.random.randint(0, 2, 1000)-0.5))

    noise = 0.2 * (np.random.randn(1000) + 1j*np.random.randn(1000))
    rx = symbols + noise

    plt.figure()
    plt.scatter(rx.real, rx.imag, s=5)
    plt.xlabel("I")
    plt.ylabel("Q")
    plt.title("QPSK Constellation")
    plt.axis("equal")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "lab03_constellation.png")
    plt.close()


def main():
    generate_tone_fft()
    generate_qpsk_constellation()


if __name__ == "__main__":
    main()
