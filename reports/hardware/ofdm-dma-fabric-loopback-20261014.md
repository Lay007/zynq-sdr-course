# OFDM modem behind an AXI DMA, run on a Zynq board (#48 stage 3), 2026-10-14

The PS + AXI DMA + OFDM modem block design of Lab 8.14 stage 3 (`tools/build_block8_ofdm_dma_bd.py`,
bitstream WNS +0.754 ns, commit `dc3e9e8`) was loaded into a Zynq-7020 board and driven from Linux.
The modem's TX samples loop back into its RX inside the fabric; no RF. Raw results:
[`ofdm-dma-fabric-loopback-20261014.json`](ofdm-dma-fabric-loopback-20261014.json).

## How it was run

- Board: board A of the course bench (Linux 5.15, vendor image, FCLK0 = 100 MHz from the IO PLL,
  `SLCR FPGA0_CLK_CTRL = 0x00200500`).
- `tools/run_ofdm_dma_board.py`:
  1. stops `iio_writedev` and `iiod`;
  2. unbinds the drivers of the vendor PL cores (AD9361 ADC and DAC cores, two DMA controllers),
     so that no kernel code touches registers that vanish with the new bitstream;
  3. loads the bitstream through `fpga_manager` (`.bit` converted by `tools/bit_to_fpga_manager_bin.py`);
  4. runs the program;
  5. warm-reboots the board back to its own image.
- Program: `blocks/block_08_modulation_and_synchronization/sw/ofdm_dma_loopback.c`, built with the
  Vitis 2021.1 `arm-linux-gnueabihf-gcc -O2 -static`. No kernel driver:
  - registers through `/dev/mem`;
  - one locked page per DMA buffer, its physical address looked up in `/proc/self/pagemap`;
  - buffers accessed only through an uncached `/dev/mem` mapping, because HP0 is not coherent
    with the CPU caches.

  Per run:
  1. resets the modem (this arms channel training) and the DMA;
  2. sends one training symbol and 80 data symbols of random bit pairs through MM2S in one transfer;
  3. receives 80 transfers of 48 bytes through S2MM, one per OFDM symbol, because the modem ends
     every symbol with `tlast`;
  4. checks that every symbol returns each of its 48 data indices exactly once with the sent bits.
     The receive buffer is filled with `0xFF` (an invalid index) before every run, so a missing
     byte would count as an error.

## Result

| Seed | Runs × data symbols | Bits | Bit errors | Missing or duplicate bytes | DMA errors | Saturations (TX, FFT, EQ, CE) |
|---|---|---:|---:|---:|---:|---|
| 0x48D5 | 100 × 80 | 768000 | 0 | 0 | 0 | 0, 0, 0, 0 |
| 0x1 | 100 × 80 | 768000 | 0 | 0 | 0 | 0, 0, 0, 0 |
| 0xBEEF | 100 × 80 | 768000 | 0 | 0 | 0 | 0, 0, 0, 0 |
| 0x2026 | 100 × 80 | 768000 | 0 | 0 | 0 | 0, 0, 0, 0 |

- **Totals:** 3 072 000 bits through PS -> DDR -> DMA -> modem TX -> modem RX -> DMA -> DDR, with
  no errors.
- **Modem registers:**
  - ID `0x4F46444D` ("OFDM"), version `0x00030100`;
  - CONFIG `0x3E`: QPSK, channel equalizer with zero-forcing, CFO corrector, block-RAM transforms,
    one training symbol;
  - per run, 81 symbols sent and 80 received, one training completed, no frame-error flags.
- **DMA buffers:** pages at `0x3FC0C000` (TX) and `0x3FC79000` (RX).
- **Time:** one run of 81 symbols takes about 480 us, about 16 Mbit/s of payload. The CPU
  re-arms S2MM for every symbol over `/dev/mem`, which probably sets most of this time. The
  modem's own throughput was not measured.
- **Board afterwards:** after the warm reboot, board A's AD9361 initialised normally and its ADC and
  DAC cores were back.

## Limits

- Fabric loopback only: the AD9361 sample path is not in this design (it needs a clock-domain
  crossing to the AD9361 interface clock), so this is stage 3, not the RF loopback of stage 4.
- The DMA buffers are user pages located through `pagemap`, with the caches avoided by uncached
  access. This works for a demonstration and a teaching lab. A product would use a kernel DMA
  allocation (a UIO or dma-buf driver) instead.
- Interrupts are left disabled; completion is polled through the `IOC` bit of `DMASR`.
