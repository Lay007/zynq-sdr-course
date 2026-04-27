from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

OUTPUT_DIR = Path("docs/assets")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update(
    {
        "figure.figsize": (6.8, 4.2),
        "font.size": 10,
        "axes.grid": True,
        "grid.alpha": 0.28,
        "axes.linewidth": 0.9,
        "lines.linewidth": 1.6,
        "savefig.dpi": 160,
    }
)


def savefig(name: str) -> None:
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / name, bbox_inches="tight")
    plt.close()


def normalized_spectrum(signal: np.ndarray, fs: float) -> tuple[np.ndarray, np.ndarray]:
    n = len(signal)
    window = np.hanning(n)
    spectrum = np.fft.fftshift(np.fft.fft(signal * window))
    freqs = np.fft.fftshift(np.fft.fftfreq(n, 1 / fs))
    mag_db = 20 * np.log10(np.abs(spectrum) / np.max(np.abs(spectrum)) + 1e-12)
    return freqs, mag_db


def generate_tone_fft() -> None:
    fs = 1_000_000.0
    n = 8192
    f0 = 100_000.0
    t = np.arange(n) / fs
    rng_i = np.random.default_rng(1)
    rng_q = np.random.default_rng(2)
    signal = np.exp(2j * np.pi * f0 * t) + 0.02 * (rng_i.normal(size=n) + 1j * rng_q.normal(size=n))

    freqs, mag_db = normalized_spectrum(signal, fs)
    peak_freq = freqs[np.argmax(mag_db)] / 1e3

    plt.figure()
    plt.plot(freqs / 1e3, mag_db)
    plt.axvline(peak_freq, linestyle="--", linewidth=1.0)
    plt.annotate(
        f"Peak: {peak_freq:.1f} kHz",
        xy=(peak_freq, 0),
        xytext=(peak_freq + 45, -12),
        arrowprops={"arrowstyle": "->", "linewidth": 0.8},
    )
    plt.xlabel("Frequency, kHz")
    plt.ylabel("Normalized magnitude, dB")
    plt.title("Lab 1: Tone FFT Spectrum")
    plt.ylim(-90, 5)
    savefig("lab01_fft.png")


def generate_am_fm_spectrum() -> None:
    fs = 1_000_000.0
    n = 8192
    t = np.arange(n) / fs
    fc = 80_000.0
    fm = 5_000.0
    am_index = 0.55
    freq_dev = 28_000.0

    message = np.sin(2 * np.pi * fm * t)
    am = (1.0 + am_index * message) * np.cos(2 * np.pi * fc * t)
    fm_sig = np.cos(2 * np.pi * fc * t + (freq_dev / fm) * np.sin(2 * np.pi * fm * t))

    f_am, s_am = normalized_spectrum(am, fs)
    f_fm, s_fm = normalized_spectrum(fm_sig, fs)

    plt.figure()
    plt.plot(f_am / 1e3, s_am, label="AM: carrier + sidebands")
    plt.plot(f_fm / 1e3, s_fm, label="FM: wider occupied bandwidth")
    plt.xlabel("Frequency, kHz")
    plt.ylabel("Normalized magnitude, dB")
    plt.title("Lab 2: AM vs FM Spectrum")
    plt.xlim(-170, 170)
    plt.ylim(-90, 5)
    plt.legend(loc="upper right", frameon=True)
    savefig("lab02_am_vs_fm.png")


def generate_qpsk_constellation() -> None:
    rng = np.random.default_rng(3)
    bits_i = 2 * rng.integers(0, 2, 1600) - 1
    bits_q = 2 * rng.integers(0, 2, 1600) - 1
    symbols = (bits_i + 1j * bits_q) / np.sqrt(2)
    phase_error = np.deg2rad(5.0)
    noise = 0.14 * (rng.normal(size=symbols.size) + 1j * rng.normal(size=symbols.size))
    rx = symbols * np.exp(1j * phase_error) + noise

    plt.figure()
    plt.scatter(rx.real, rx.imag, s=7, alpha=0.65, label="Received symbols")
    ideal = np.array([1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j]) / np.sqrt(2)
    plt.scatter(ideal.real, ideal.imag, s=80, marker="x", linewidths=2, label="Ideal QPSK")
    plt.xlabel("In-phase component I")
    plt.ylabel("Quadrature component Q")
    plt.title("Lab 3: QPSK Constellation")
    plt.axis("equal")
    plt.legend(loc="upper right", frameon=True)
    savefig("lab03_constellation.png")


def generate_sync_constellation() -> None:
    rng = np.random.default_rng(4)
    n = 1400
    bits_i = 2 * rng.integers(0, 2, n) - 1
    bits_q = 2 * rng.integers(0, 2, n) - 1
    tx = (bits_i + 1j * bits_q) / np.sqrt(2)
    sample_index = np.arange(n)
    cfo = 0.018
    noise = 0.13 * (rng.normal(size=n) + 1j * rng.normal(size=n))
    before = tx * np.exp(1j * cfo * sample_index) + noise
    after = before * np.exp(-1j * cfo * sample_index)

    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.7), sharex=True, sharey=True)
    axes[0].scatter(before.real, before.imag, s=6, alpha=0.55)
    axes[0].set_title("Before CFO correction")
    axes[0].set_xlabel("I")
    axes[0].set_ylabel("Q")
    axes[0].axis("equal")

    axes[1].scatter(after.real, after.imag, s=6, alpha=0.55)
    axes[1].set_title("After CFO correction")
    axes[1].set_xlabel("I")
    axes[1].axis("equal")

    fig.suptitle("Lab 4: Synchronization Impact on QPSK Constellation")
    savefig("lab04_sync_constellation.png")


def generate_evm_comparison() -> None:
    cases = ["Clean", "Noise", "CFO", "Clipping", "I/Q mismatch"]
    evm = np.array([2.1, 7.8, 12.5, 18.2, 10.4])

    plt.figure()
    bars = plt.bar(cases, evm)
    plt.ylabel("EVM, %")
    plt.title("Lab 5: Impairment Impact on EVM")
    plt.ylim(0, 22)
    plt.xticks(rotation=20, ha="right")
    for bar, value in zip(bars, evm):
        plt.text(bar.get_x() + bar.get_width() / 2, value + 0.6, f"{value:.1f}%", ha="center", va="bottom")
    savefig("lab05_evm.png")


def generate_ber_curve() -> None:
    snr_db = np.arange(0, 15, 1)
    ber_before_sync = 0.5 * np.exp(-0.32 * snr_db) + 1e-3
    ber_after_sync = 0.35 * np.exp(-0.58 * snr_db) + 1e-5

    plt.figure()
    plt.semilogy(snr_db, ber_before_sync, marker="o", label="Before synchronization")
    plt.semilogy(snr_db, ber_after_sync, marker="s", label="After synchronization")
    plt.xlabel("SNR, dB")
    plt.ylabel("Bit error rate")
    plt.title("Lab 6: End-to-End BER Performance")
    plt.legend(loc="upper right", frameon=True)
    plt.grid(True, which="both", alpha=0.28)
    savefig("lab06_ber.png")


def main() -> None:
    generate_tone_fft()
    generate_am_fm_spectrum()
    generate_qpsk_constellation()
    generate_sync_constellation()
    generate_evm_comparison()
    generate_ber_curve()


if __name__ == "__main__":
    main()
