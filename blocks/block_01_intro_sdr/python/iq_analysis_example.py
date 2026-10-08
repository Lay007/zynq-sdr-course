"""Find the test tone in a recorded interleaved IQ file and plot its spectrum.

    python blocks/block_01_intro_sdr/python/iq_analysis_example.py capture.ci16 --fs 2.4e6
    python blocks/block_01_intro_sdr/python/iq_analysis_example.py capture.cu8 --dtype uint8

`--dtype uint8` is the raw `rtl_sdr` format (unsigned, offset 127.5); `int16` is the
course/AD9363 `.ci16` format. The printed peak frequency is the offset from the
receiver's tuning frequency.
"""

import argparse
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


def load_iq_file(path: Path, dtype: np.dtype) -> np.ndarray:
    raw = np.fromfile(path, dtype=dtype)
    if raw.size % 2 != 0:
        raise ValueError("IQ file must contain an even number of values")
    values = raw.astype(np.float64)
    if dtype == np.uint8:
        values -= 127.5  # rtl_sdr writes unsigned samples centred on 127.5
    return values[0::2] + 1j * values[1::2]


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze recorded IQ tone")
    parser.add_argument("filename", help="Path to IQ file")
    parser.add_argument("--fs", type=float, default=2.4e6, help="Sample rate, Hz")
    parser.add_argument("--dtype", default="int16", help="Input numeric type: int16 (.ci16) or uint8 (rtl_sdr .cu8)")
    parser.add_argument("--nfft", type=int, default=4096, help="FFT length")
    parser.add_argument("--out", help="save the spectrum plot to this PNG instead of showing it")
    args = parser.parse_args()

    x = load_iq_file(Path(args.filename), np.dtype(args.dtype))

    nfft = min(len(x), args.nfft)
    X = np.fft.fftshift(np.fft.fft(x[:nfft], nfft))
    f = np.fft.fftshift(np.fft.fftfreq(nfft, d=1 / args.fs))
    magnitude_db = 20 * np.log10(np.abs(X) + 1e-12)

    peak = int(np.argmax(magnitude_db))
    print(f"samples: {len(x)}, FFT length: {nfft}, bin width: {args.fs / nfft:.1f} Hz")
    print(f"peak offset from the tuning frequency: {f[peak]:.1f} Hz")
    print(f"peak above the median spectrum level: {magnitude_db[peak] - np.median(magnitude_db):.1f} dB")

    plt.figure()
    plt.plot(f, magnitude_db)
    plt.xlabel("Frequency offset, Hz")
    plt.ylabel("Magnitude, dB")
    plt.title("Spectrum of recorded tone")
    plt.grid(True)
    if args.out:
        plt.savefig(args.out, dpi=120)
        print(f"plot: {args.out}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
