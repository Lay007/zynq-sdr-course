"""Minimal RTL-SDR capture through ctypes on rtlsdr.dll (pyrtlsdr 0.4 does not match this DLL).

usage: python tools/rtl_sdr_capture.py <center_hz> <sample_rate> <gain_tenths_db|auto> <n_samples> <out.npy>
Writes complex64 samples normalised to +-1 and prints the device's tuner gains and the actual rate.
"""
import ctypes as C
import ctypes.util
import os
import sys

import numpy as np

# The DLL that ships with SDR++ or rtl-sdr-blog; set RTLSDR_DLL to pick one explicitly.
DLL = os.environ.get("RTLSDR_DLL") or ctypes.util.find_library("rtlsdr") or "rtlsdr"


def capture(center_hz: int, rate: int, gain: str, n: int):
    lib = C.CDLL(DLL)
    dev = C.c_void_p()
    if lib.rtlsdr_get_device_count() < 1:
        raise SystemExit("no RTL-SDR found")
    if lib.rtlsdr_open(C.byref(dev), 0) != 0:
        raise SystemExit("rtlsdr_open failed (is SDR++ or another program holding it?)")
    try:
        lib.rtlsdr_set_sample_rate(dev, C.c_uint32(rate))
        lib.rtlsdr_set_center_freq(dev, C.c_uint32(center_hz))
        gains = (C.c_int * 64)()
        ng = lib.rtlsdr_get_tuner_gains(dev, gains)
        if gain == "auto":
            lib.rtlsdr_set_tuner_gain_mode(dev, 0)
        else:
            lib.rtlsdr_set_tuner_gain_mode(dev, 1)
            lib.rtlsdr_set_tuner_gain(dev, int(gain))
        lib.rtlsdr_reset_buffer(dev)
        nbytes = 2 * n
        buf = (C.c_ubyte * nbytes)()
        got = C.c_int()
        # Discard the first read: the tuner settles after a retune.
        lib.rtlsdr_read_sync(dev, buf, 2 * 262144, C.byref(got))
        if lib.rtlsdr_read_sync(dev, buf, nbytes, C.byref(got)) != 0:
            raise SystemExit("rtlsdr_read_sync failed")
        raw = np.frombuffer(bytes(buf)[: got.value], dtype=np.uint8).astype(np.float32)
        iq = ((raw[0::2] - 127.4) + 1j * (raw[1::2] - 127.4)) / 128.0
        info = {
            "center_hz": lib.rtlsdr_get_center_freq(dev),
            "rate": lib.rtlsdr_get_sample_rate(dev),
            "tuner_gain_tenths_db": lib.rtlsdr_get_tuner_gain(dev),
            "available_gains_tenths_db": list(gains[:ng]),
            "samples": int(iq.size),
        }
        return iq.astype(np.complex64), info
    finally:
        lib.rtlsdr_close(dev)


if __name__ == "__main__":
    center, rate, gain, n, out = int(float(sys.argv[1])), int(float(sys.argv[2])), sys.argv[3], int(sys.argv[4]), sys.argv[5]
    iq, info = capture(center, rate, gain, n)
    np.save(out, iq)
    print(info)
    print(f"rms {np.sqrt(np.mean(np.abs(iq) ** 2)):.4f}  peak {np.max(np.abs(iq)):.3f}  "
          f"clipped {np.mean((np.abs(iq.real) > 0.99) | (np.abs(iq.imag) > 0.99)) * 100:.3f} %")
