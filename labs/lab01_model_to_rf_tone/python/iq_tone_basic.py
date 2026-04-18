#!/usr/bin/env python3
from pathlib import Path
import numpy as np
FS_HZ = 1.0e6
N = 4096
F0_HZ = 100.0e3
A = 0.9
PHI = np.pi/6
idx = np.arange(N, dtype=np.float64)
x = A * np.exp(1j * (2*np.pi*F0_HZ*idx/FS_HZ + PHI))
out = Path('results'); out.mkdir(exist_ok=True)
np.savetxt(out/'iq_tone_basic_iq.txt', np.column_stack((np.real(x), np.imag(x))), fmt='%.12f')
X = np.fft.fftshift(np.fft.fft(x))
f = np.fft.fftshift(np.fft.fftfreq(N, d=1.0/FS_HZ))
np.savetxt(out/'iq_tone_basic_fft.txt', np.column_stack((f, np.abs(X))), fmt='%.12f')
print('Generated IQ tone and saved reference files to results/.')
