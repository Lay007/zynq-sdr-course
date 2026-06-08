# C++ ↔ MATLAB Bridge for DSP Blocks

This document describes the connection between MATLAB reference models and C++ deterministic implementations for key DSP blocks in zynq-sdr-course.

| Lab Block | MATLAB Reference | C++ Implementation | HDL Testbench | Verified Output |
|---|---|---|---|---|
| FIR Filtering (Block 03) | MATLAB FIR scripts | cpp/fir_dsp.cpp | tb_fir_iq_4tap.v | Canonical CSV + plots |
| FFT / Convolution | MATLAB fft scripts | cpp/fft_convolution.cpp | tb_fft_passthrough.v | Canonical CSV + plots |
| Tone Detection / Goertzel | MATLAB tone scripts | cpp/goertzel.cpp | tb_goertzel.v | Canonical CSV + plots |
| Delay Estimation / GCC-PHAT | MATLAB gccphat scripts | cpp/gccphat.cpp | tb_gccphat.v | Canonical CSV + plots |
| Resampling L/M | MATLAB resampling scripts | cpp/resampler_lm.cpp | tb_resampler.v | Canonical CSV + plots |

**Notes:**
- Each C++ implementation must produce canonical CSV files to verify reproducibility against MATLAB.
- HDL testbenches should consume the same canonical vectors.
- CI checks should validate that MATLAB and C++ results are aligned within defined tolerance.