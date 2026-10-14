# Board B radiates a carrier between bursts: the DAC holds the last burst sample, 2026-10-14

Raw data: [`board-b-dac-held-carrier-20261014.json`](board-b-dac-held-carrier-20261014.json).

## Setup

Board B (FishBall, course image) transmits its own fabric QPSK burst: B TX1 -> variable attenuator
(0 dB) -> 30 dB -> 3-way splitter -> B RX1, board A RX1 and the RTL-SDR. Both of B's LOs are at
915 MHz.

Board B's device tree has no DAC driver (no `cf-ad9361-dds-core-lpc`), so after boot every DAC
channel takes the internal DDS, whose scale is 0, and the modem burst is not transmitted at all.
The bridge muxes the burst into the DAC FIFO on the DMA input
(`course_dac_fifo_source_mux.v`), so the channels have to be put on that input by hand:
`devmem 0x79024418/0x79024458/0x79024498/0x790244D8 32 2`, then `devmem 0x79024044 32 1`.

## What the RTL-SDR sees at 915 MHz

Line at the TX LO, dB over the RTL-SDR's noise floor:

| B state | line |
|---|---:|
| TX LO powered down | 12.9 |
| TX 0 dB, DAC source ZERO | 13.5 |
| TX 0 dB, DAC source DDS (boot default) | 14.5 |
| TX 0 dB, DAC source DMA, after some bursts | **87.7** |
| same, with a zero DAC stream running (below) | 18.4 |

The analog LO leakage is small (about 13-18 dB over the floor). The strong line exists only with
the DAC on the DMA input. Board A, on the free splitter output, sees it as a continuous carrier at
+365 Hz from its own LO: during a burst it is 3 dB below the burst (780 against 1103 counts RMS),
and it stays on between bursts. (The RTL-SDR's time-averaged spectrum suggested 20 dB above the
burst; the bursts occupy only about 3 % of the time, so that figure was misleading.)

## Cause

`course_dac_fifo_source_mux.v` writes the DAC FIFO on the vendor stream's strobe and substitutes
the modem's samples only while it transmits. Its comment describes the fallback: "If the vendor
stream were ever stopped, `vendor_valid` would be dead and this degrades to the old `bpsk_valid`
behaviour". On board A a cyclic DMA buffer always runs (`iio_writedev`), so the vendor stream is
alive. On board B nothing starts the TX DMA, so the FIFO is written only during a burst, and
between bursts the DAC keeps outputting the last word written, a nonzero sample from the burst.
A constant at the DAC is a carrier at the LO.

## Workaround without a new bitstream

`blocks/block_11_integrated_sdr_project/sw/dac_zero_stream.c` runs B's TX DMA (ADI `axi_dmac` at
`0x7c420000`, memory -> DAC stream) in cyclic mode over one locked page of zeros, so the vendor
stream is alive and the FIFO is written with zeros between bursts. It is built and used like the
Lab 8.14 stage 3 program:

- build with the Vitis `arm-linux-gnueabihf-gcc -O2 -static`;
- unbind the idle `dma-axi-dmac` driver from `7c420000.dma`;
- start the program in the background, and stop it with a plain `kill`. On SIGTERM it stops the DMA
  first. Never use `kill -9`: the DMA would keep reading a page the kernel may reuse.

With the stream running the line drops from 87.7 to 18.4 dB over the floor, and nothing is held
after the bursts.

## Effect on the single-board link

100 frames each, Lab 11.45 mode, TX 0 dB, RX 60 dB. Columns: locked / clean / payload bit errors.

| | DC blocker on | DC blocker off |
|---|---|---|
| #65 image, no zero stream | 0 / 0 / 0 | 62 / 32 / 328 |
| #66 image, no zero stream | 24 / 4 / 442 | 53 / 40 / 199 |
| #65 image, zero stream | 62 / 60 / 4 | 73 / 70 / 9 |
| #66 image, zero stream | **75 / 75 / 0** | **75 / 75 / 0** |

The 25 frames that do not lock on the #66 image fail deterministically: with one board the latency
is fixed, and two of the eight `start_offset` values the script cycles through (3 and 4) put the
sampler on the symbol boundary. On the other six offsets 36 of 36 frames locked with 0 errors
(RX 50 and 60 dB).

## Conclusions

- Measured:
  - board B's carrier is the DAC holding the last burst sample, not analog leakage;
  - a zero vendor stream removes it;
  - with it, the single-board link on the #66 image decodes every locked frame without errors, with
    the DC blocker on or off.
- The earlier single-board DC blocker comparison
  ([`dc-blocker-persist-silicon-20261014.md`](dc-blocker-persist-silicon-20261014.md)) was taken
  with this carrier present, and it dominated the result.
- Not done: a fix in the mux. It would need a write cadence of its own when the vendor stream is
  dead, without reintroducing the occupancy staircase that its comment documents.
- Board B maintenance: after one warm reboot, its static network script did not run (random MAC,
  no 192.168.20.1). The console on the USB serial port (COM6 on this PC, 115200, root/analog)
  fixed it with `/etc/init.d/S99zstaticeth start`. The next reboot was normal.
