import argparse
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt


def load_iq_file(path: Path, dtype: np.dtype) -> np.ndarray:
    raw = np.fromfile(path, dtype=dtype)
    if raw.size % 2 != 0:
        raise ValueError("IQ file must contain an even number of values")
    i_data = raw[0::2].astype(np.float64)
    q_data = raw[1::2].astype(np.float64)
    return i_data + 1j * q_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze recorded IQ tone")
    parser.add_argument("filename", help="Path to IQ file")
    parser.add_argument("--fs", type=float, default=2.4e6, help="Sample rate, Hz")
    parser.add_argument("--dtype", default="int16", help="Input numeric type, e.g. int16")
    parser.add_argument("--nfft", type=int, default=4096, help="FFT length")
    args = parser.parse_args()

    path = Path(args.filename)
    x = load_iq_file(path, np.dtype(args.dtype))

    nfft = min(len(x), args.nfft)
    X = np.fft.fftshift(np.fft.fft(x[:nfft], nfft))
    f = np.fft.fftshift(np.fft.fftfreq(nfft, d=1 / args.fs))

    plt.figure()
    plt.plot(f, 20 * np.log10(np.abs(X) + 1e-12))
    plt.xlabel("Frequency, Hz")
    plt.ylabel("Magnitude, dB")
    plt.title("Spectrum of recorded tone")
    plt.grid(True)
    plt.show()


if __name__ == "__main__":
    main()
