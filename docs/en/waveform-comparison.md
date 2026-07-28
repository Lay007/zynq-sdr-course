# Digital waveform comparison

| Family | Spectral efficiency | Envelope / PAPR | Synchronization burden | Relative FPGA cost | Typical use |
|---|---|---|---|---|---|
| QPSK | 2 bits/symbol | Constant symbol envelope; shaped waveform has moderate peaks | Carrier, phase, timing and quadrant resolution | Low–medium | Robust general-purpose links |
| 16-QAM | 4 bits/symbol | Non-constant; sensitive to back-off and linearity | QPSK requirements plus tighter gain/phase accuracy | Medium | Higher-throughput linear links and OFDM payloads |
| OFDM | Many parallel carriers | High PAPR; clipping/back-off must be managed | Packet timing, CFO, pilots and channel estimation | High: FFT, buffers, pilots, equalizer | Frequency-selective broadband channels |
| GFSK | 1 bit/symbol in this lab | Constant envelope, approximately 0 dB PAPR | Symbol timing; discriminator can avoid carrier phase recovery | Low | Low-power telemetry and nonlinear transmitters |
| CSS | `SF` bits per long chirp symbol | Constant envelope | Preamble, dechirp/FFT, CFO and sample-rate tracking | Medium–high: chirp source, FFT and peak detector | Long-range/low-rate links |
| DSSS | Data rate reduced by spreading factor | BPSK-like constant envelope | PN-code acquisition and tracking | Medium: LFSR and high-rate correlator | Interference resistance and code-domain links |

These are implementation-level comparisons for the course models, not claims of standards interoperability.
