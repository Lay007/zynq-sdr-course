# Lab 11.47 — One board receives its own burst

## Idea

The two-board labs need two boards and a second transmitter. One board can also send its fabric
QPSK burst out of TX1 and decode it from RX1 through a cable. TX and RX then share one reference
oscillator: there is no carrier offset, no oscillator wander, and the whole modem can be checked
with a single board.

On the course bench board B did not manage this at first: the frame was found in fewer than one
reception out of ten, with many bit errors. The cause was not in the modem but in how the course
bitstream feeds the DAC. That cause is the subject of this lab.

## Bench

```text
board B TX1 -> attenuators (at least 30 dB in total) -> board B RX1
```

- Never connect TX1 straight to RX1. With TX at 0 dB and 30 dB in the path the receiver sees about
  -30 dBm; the AD9361's input limit is +2.5 dBm.
- The course bench used a variable attenuator (0 dB) -> 30 dB -> a 3-way splitter, whose other
  outputs went to board A's RX1 and an RTL-SDR as independent witnesses.
- Board B has no fan. The script reads the Zynq temperature from the XADC before and after and
  refuses to start above 80 °C; on the bench it stayed at 61-70 °C.

## What is special about board B

Board B runs the course image, whose device tree has no DAC driver (`cf-ad9361-dds-core-lpc` is
missing). Two consequences:

1. After boot every DAC channel takes the internal DDS, whose scale is 0. The bridge muxes the modem
   burst into the DAC FIFO on the **DMA** input (`course_dac_fifo_source_mux.v`), so until the
   channels are switched to it (`devmem 0x79024418 32 2` and the same for 0x...58, 0x...98,
   0x...D8), the burst is not transmitted at all.
2. Nothing runs the vendor TX DMA. That is the subject of the next section.

## A DAC that holds its last sample

With the channels on the DMA input the burst does go out, but an RTL-SDR on the splitter shows a
strong continuous line at the LO. Its level over the RTL-SDR's noise floor in different states:

| board B state | line at 915 MHz |
|---|---:|
| TX LO powered down | 12.9 dB |
| DAC source ZERO | 13.5 dB |
| DAC source DDS (boot default) | 14.5 dB |
| DAC source DMA, after some bursts | **87.7 dB** |

So it is not analog LO leakage. The mux writes the DAC FIFO on the vendor stream's strobe and
substitutes the burst only while it transmits. On board A a cyclic DMA buffer always runs
(`iio_writedev`), so the strobe never stops. On board B nothing starts the TX DMA, so the FIFO is
written only during a burst, and between bursts the DAC keeps outputting the last word written, a
nonzero burst sample. A constant at the DAC is a carrier at the LO. Measured on board A, during a
burst it is only 3 dB below the burst, and it never goes away. At board B's own receiver it is a DC
component as strong as the signal.

## The fix used here

`blocks/block_11_integrated_sdr_project/sw/dac_zero_stream.c` keeps the vendor stream alive with
zeros. It locks one page of memory, looks up its physical address in `/proc/self/pagemap`, and runs
the ADI `axi_dmac` at `0x7c420000` (memory -> DAC stream) cyclically over it. Before starting it,
the idle kernel driver of that DMA is unbound. The program stops the DMA when it receives SIGTERM,
so it must be stopped with a plain `kill`. After `kill -9` the DMA would keep reading a page the
kernel may hand to someone else, and transmit it.

The script below builds the program with the Vitis `arm-linux-gnueabihf-gcc -static` (as in
Lab 8.14 stage 3), starts it, switches the DAC channels, runs the frames and stops it again.

## Run

```bash
cd blocks/block_11_integrated_sdr_project/python
python lab_11_47_single_board_selfota.py --frames 60
python lab_11_47_single_board_selfota.py --frames 60 --no-zero-stream
```

Board B image `3d492301` (#66), TX 0 dB, RX 60 dB, Lab 11.45 differential mode, 915 MHz:

| | frames | locked | clean | payload bit errors |
|---|---:|---:|---:|---:|
| zero stream | 60 | 52 | 52 | 0 / 13312 |
| no zero stream (held sample) | 60 | 5 | 0 | 220 / 1280 |

Every locked frame is clean with the zero stream; without it the link is practically lost.

## Exercises

1. Run with `--offsets 0 1 2 3 4 5 6 7`. Why do some `start_offset` values never lock on one board,
   while on the two-board bench every value works? Compare with the sampling-phase sweep of
   Lab 5.8.
2. Run with and without `--no-dc-blocker`. Before the fix of issue #66 the DC blocker cost frames
   on this link; what does it cost now, and why could a DC blocker not remove the held sample?
3. A passive coaxial DC block in the RF path was offered as a fix during the investigation. Why
   would it change nothing?
4. The mux comment explains why the FIFO must be written at a rigid cadence. What would go wrong
   if the RTL simply wrote zeros on its own clock whenever the burst is not selected?

<details markdown="1">
<summary>Answers</summary>

1. With one board the delay from the modem's TX to its RX is fixed, so the frame always arrives at
   the same sub-symbol phase. Each `start_offset` places the sampler at one phase; two of the eight
   land on the symbol boundary, where the eye is closed. On two boards the start relative to the
   received stream is random, so every value lands at a good phase most of the time.
2. On the bench both settings locked the same frames with 0 errors (75 of 100 each, with eight
   offsets). The held sample is a carrier at the LO, which reaches the receiver as a DC component,
   but it was present from the start and as strong as the signal; with the per-frame reset of the
   old DC blocker the receiver locked no frame at all. A DC blocker can only remove an offset
   slowly and approximately; removing the cause at the transmitter is better.
3. The carrier is at 915 MHz on the cable. A DC block is a series capacitor: it stops a DC voltage
   and passes RF. The carrier becomes "DC" only after the receiver has moved it to zero frequency.
4. The FIFO crosses from the fabric clock to the DAC clock. If the number of writes per DAC read
   depends on what is transmitted, the FIFO occupancy, and with it the delay of the burst to the
   antenna, changes from burst to burst. The mux comment records exactly that: the frame arrived
   at a different sub-symbol phase in a repeating pattern. The cadence has to follow the DAC's read
   rate.

</details>

## Evidence

- [`board-b-dac-held-carrier-20261014.md`](https://github.com/Lay007/zynq-sdr-course/blob/main/reports/hardware/board-b-dac-held-carrier-20261014.md):
  the RTL-SDR table, board A's view and the DC-blocker comparison on one board;
- issue [#67](https://github.com/Lay007/zynq-sdr-course/issues/67): the mux behaviour and possible
  permanent fixes (board B's device tree, or the RTL).

## What this lab does and does not show

It shows a single-board link that decodes every locked frame without errors once the DAC FIFO is
fed correctly, and how an infrastructure detail far from the modem can look like a modem problem.
It does not fix the mux: the zero stream is a workaround that has to run while board B transmits.
