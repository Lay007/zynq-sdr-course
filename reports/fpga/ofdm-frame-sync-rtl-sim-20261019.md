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

## The OFDM image (built, not run)

`rtl/ofdm_radio_core.v` puts the modem and this block behind AXI4-Lite for the radio: a TX bit
buffer, the preamble from a ROM, the modem's training and data symbols, a digital gain, and a
dual-clock FIFO that hands the DAC FIFO one sample per request; on the RX side a dual-clock FIFO
from the ADC, at most one sample every 16 clocks into the frame search, the modem's receiver for
the first frame after RX_ARM, and an RX bit buffer. `tb_ofdm_radio_core.sv` sends two frames
through DAC -> channel (delay, DC, noise, 12 bits) -> ADC at 2.083 MS/s and gets every bit back.
In CI its sample domain runs at the sample rate with a request on every clock. On the board that
domain is the 62.5 MHz divided clock, and the DAC FIFO's requests and the ADC's strobes come once
every few dozen clocks, independently of each other; the bench has parameters for that and for a
carrier offset (2026-10-23, core 1.0, before the conditioner below):

| sample clock, strobe | ADC strobe offset | CFO | result |
|---|---:|---:|---|
| 2.083 MHz, every clock (CI) | 0 | 0 | 2 frames, every bit right |
| 62.5 MHz, every 30 clocks (2.083 MS/s) | 17 | 3 kHz | 2 frames, every bit right |
| 62.5 MHz, every 30 clocks | 17 | 10 kHz | 2 frames, every bit right |
| 62.5 MHz, every 16 clocks (3.9 MS/s) | 5 | 3 kHz | 2 frames, every bit right |
| 62.5 MHz, every 30 clocks | 5 | 20 kHz | frame found, bits wrong: beyond the modem's CFO range (+-16.3 kHz at 2.083 MS/s), as in stage 4a |

    iverilog -g2012 -s tb_ofdm_radio_core -P tb_ofdm_radio_core.SCLK_HALF_NS=8 -P tb_ofdm_radio_core.STROBE=30 \
      -P tb_ofdm_radio_core.RX_PHASE=17 -P tb_ofdm_radio_core.CFO_HZ=3000.0 -o radio.vvp rtl/ofdm_*.v tb/tb_ofdm_radio_core.sv

It does not fit next to the BPSK/QPSK bridge: that build already uses 176 of the 220 DSP48E1 and
75 % of the LUTs, and the OFDM core adds about 46 DSP. So it is an image of its own,
`COURSE_OVERLAY_MODE=ofdm_txrx`: the vendor shell, the DAC FIFO mux (which now has a third input)
and the core at 0x79060000. Vivado 2021.1: 21 261 LUT, 25 562 FF, 9.5 BRAM tiles, 74 DSP48E1,
WNS +0.253 ns, WHS +0.042 ns, every net routed, no latches (artifact `bitstreams/ofdm-txrx-48`,
md5 5de22b09). The board program is `sw/zofdm.c` (`loop` on one board, `tx` / `rx` on two).

## Core 2.0: coarse CFO and level from the preamble (2026-10-23)

`rtl/ofdm_frame_conditioner.v` sits between the frame search and the modem. The search now hands
out what it measured on the plateau: the sum of `P` (its angle is `2 pi 32 eps`), `R`, and its DC
estimate. The conditioner subtracts the DC, turns the frame back by the CFO from the angle (a
16-iteration CORDIC and an NCO; range `+-fs/64`, +-32.5 kHz at 2.083 MS/s, twice the modem's own),
and scales it by `2^(k/2)` to an RMS of about 4096. The modem corrects what is left, and RX_ARM
resets it, so every frame trains the equalizer again. CONFIG (0x040) switches both stages off;
THETA (0x044) and GAIN_K (0x048) show what the last frame measured.

Three problems showed up only in the whole chain:

1. At -28 kHz a second, false frame appeared in the silence. Subcarrier +1 lands at +4.5 kHz; the
   256-sample DC tracker followed part of it, and its decaying estimate after the burst looked
   periodic to the metric. The tracker is now 1024 samples (`DC_K = DC_F = 10`, model too).
2. At -28 kHz and -20 dB together, bit errors: turning the frame turns its DC into a tone at `-CFO`,
   between the data subcarriers. The DC estimate is subtracted before the rotation.
3. Still single errors, on one subcarrier: the tracker restarted with every RX_ARM and had learnt
   12 % of the DC in the 137 samples before the frame. It now runs all the time (`dc_rst` separate
   from `rst`); the bench gives it time to settle first (`SETTLE_SAMPLES`), as a running board does.

Results (`tb_ofdm_radio_core.sv`, the board's sample domain, two frames each, every bit checked):

| channel | preamble CFO estimate | gain | result |
|---|---:|---:|---|
| CFO 3 kHz | 3012 / 3012 Hz | `2^(-2/2)` | every bit right |
| CFO 20 kHz | 20005 / 20011 Hz | `2^(-2/2)` | every bit right |
| CFO -28 kHz | -27992 / -27978 Hz | `2^(-2/2)` | every bit right |
| CFO 3 kHz, -20 dB | 3014 / 3026 Hz | `2^(5/2)` | every bit right |
| CFO 3 kHz, +5.6 dB | 3012 / 3008 Hz | `2^(-4/2)` | every bit right |
| CFO -28 kHz, -20 dB, `SETTLE_SAMPLES=4096` | -27961 / -27927 Hz | `2^(5/2)` | every bit right |
| CFO 20 kHz, CONFIG = 2 (coarse stage off) | | | frame found, bits wrong |

`tools/run_ofdm_rtl.py` runs three of them in CI (3 kHz, -28 kHz, -20 dB); the combined case needs
about three minutes of settling and is run by hand. Vivado OOC: the search 889 LUT, 1115 FF, 12 DSP,
1 BRAM, +1.948 ns; the conditioner 1097 LUT, 467 FF, 7 DSP, +1.354 ns (after two timing fixes, see
[block8-ofdm-vivado-evidence.md](block8-ofdm-vivado-evidence.md)). The OFDM image with core 2.0:
22 479 LUT, 26 290 FF, 9.5 BRAM tiles, 81 DSP48E1, WNS +0.203 ns, WHS +0.035 ns, every net routed,
no latches, the core at 0x79060000-0x79060FFF (artifact `bitstreams/ofdm-txrx-48-v2`, md5 021489af;
`ofdm-txrx-48` is superseded).

## Not done

Nothing of this has run on a board yet. `tools/run_ofdm_radio_board.py` is ready for the bench
(`--dry-run` shows the plan).
