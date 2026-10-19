# OFDM frame synchronization in RTL, in front of the modem receiver (#48, stage 4b, simulation)

Stage 4a ([ofdm-rf-link-sync-sim-20261019.md](ofdm-rf-link-sync-sim-20261019.md)) found the frame
on the PC, in floating point, and handed the RTL receiver symbols that were already cut. On the
board the frame has to be found in the fabric, in the continuous ADC stream. This stage writes that
block, `rtl/ofdm_frame_sync.v`, and its bit-exact model `tools/ofdm_frame_sync_fixed.py`, and runs
the block and the unchanged modem receiver together. **Simulation, plus an out-of-context Vivado
implementation of the block alone; nothing ran on a board.**

## What the block does

The input is the AD9361 stream as the fabric sees it, Q1.15, one sample per converter clock, with
no back-pressure. The block works on 12 bits (the input shifted right by 4) and first removes DC
with a tracker, `m += (x - m) >> 8`. Without it, in the fixed-point model, a burst followed by
silence with a 3 % DC offset gave a second, false frame 93 samples after the burst: a constant is
perfectly "periodic" for the correlation of two halves.

Then the same Schmidl and Cox metric as in stage 4a, kept as running sums so that every sample
costs a constant amount of work: P is the sum of the last 32 products conj(x[n-32]) x[n], E the sum
of the last 64 energies, R = E / 2. Division is avoided by comparing squares: a sample is "above"
when R exceeds a floor (E_MIN = 2000) and 4 |P|^2 > 3 R^2, that is M > 0.75, both sides shifted
right by 8 first so the products stay in 56 bits. A run of at least 8 such samples is the plateau of
the preamble; its centre gives the first symbol after the preamble, put 4 samples early inside the
cyclic prefix as before.

The decision comes about 70 samples after the first symbol has started, so the input goes through a
128-sample delay line, and from the decided sample on, FRAME_SYMBOLS times 80 samples go out with
`last` on every 80th, which is exactly what the modem receiver expects. A plateau that ends while a
frame is still going out is counted in `frames_missed` and ignored.

## The output FIFO, and what the receiver can take

The modem receiver is not always ready: after every symbol its sequential FFT holds `tready` low
for about 107 clocks. With no FIFO, at 48 clocks per sample (2.083 MS/s at 100 MHz, the board), the
first chain run lost 2 samples per symbol and the frame fell apart. The block now ends in a
16-sample FIFO with `out_ready` and an `overflows` counter. The FIFO covers the stall, not a rate the
receiver cannot sustain on average; with the committed vectors:

| clocks per sample | FIFO overflows | result |
|---:|---:|---|
| 4 | 144 | fail |
| 8 | 31 | fail |
| 12 | 0 | 192/192 bit pairs right |
| 48 (board) | 0 | 0 bit errors (runs below) |

So the receiver needs between 9 and 12 clocks per sample on average. The board gives 48.

## Results

The model against the true position of the first symbol: 0 to 3 samples early, never late, with no
false frame after the DC tracker; at SNR 5 dB 2 of 4 frames were missed (the floating-point finder
of stage 4a works to about 10 dB). The RTL block against the model: bit-exact, the samples the block
hands over are exactly the received samples from the model's first-symbol index on
(`rtl_matches_model` below).

The whole chain, `tools/run_ofdm_sync_chain.py`: frames of the RTL transmitter (training symbol +
10 data symbols) through the channel model of stage 4a, then `ofdm_frame_sync` and the modem
receiver in one testbench (`tb_ofdm_rx_sync_chain.sv`), 48 clocks per sample, 3 frames per case:

| case | rtl_matches_model | bit errors / 2880 |
|---|---|---:|
| SNR 20 dB, CFO 10 kHz, fractional delay | yes | 0 |
| SNR 25 dB, CFO 3 kHz, fractional, DC 5 %, I/Q 0.3 dB / 2 deg | yes | 0 |
| SNR 15 dB, CFO 3 kHz, fractional | yes | 0 |

## Checked in CI

`tb_ofdm_rx_sync_chain.sv` without arguments checks itself on committed vectors
(`verification/vectors/block08_ofdm_sync_chain_*.txt`, from `tools/generate_ofdm_sync_chain_vectors.py`:
one frame, SNR 30 dB, CFO 3 kHz, fractional delay): exactly one frame, no overflow, no frame error,
all 192 data bit pairs right, at 12 clocks per sample. `tb_ofdm_modem_file.sv` (the file bench of
stage 4a) used to print FAIL and still exit 0 when started without files, as `tools/run_ofdm_rtl.py`
starts every bench; it now runs a TX to RX loopback through the modem in that case and stops with
an error if any bit pair differs. `tests/test_ofdm_frame_sync_fixed.py` checks the model. All 27
OFDM benches pass (`python tools/run_ofdm_rtl.py`).

## Vivado

Out of context on `xc7z020clg400-2` at 100 MHz, ports timed with 0 ns delays
([block8-ofdm-vivado-evidence.md](block8-ofdm-vivado-evidence.md)): 777 LUT, 842 FF, 12 DSP48E1,
1 BRAM tile, WNS +2.435 ns. The first version, all arithmetic for a sample in one clock, had
WNS -16.063 ns (34 logic levels) and 7022 flip-flops; the rings, cleared on reset, could not
become RAM. The block is now a 10-clock pipeline with unreset rings that read as zero until
filled, so it behaves as the model whenever samples are at least 11 clocks apart (the board: 48).
`tools/run_ofdm_sync_chain.py` also compares the number of frames with the model now: at SNR 6 dB
the model and the RTL both missed the same 2 of 3 frames, which the first version of the script
reported as a mismatch.

## Not done

The block is not in a bitstream. On the board it would sit between the ADC path and the modem
receiver, with a level normalization in front of it (E_MIN assumes the RX level of the bench) and a
modem retrain on `frame_start`, so that every frame trains the equalizer again; none of this is
written yet.
