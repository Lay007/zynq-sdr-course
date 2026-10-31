# Lab 11.53 — Local SPI Display for an SDR Receiver

**Status:** proposed lab and validation procedure. Photographs show a display wired to a ZynqSDR board, but the electrical pin mapping, display controller and successful operation on the board have **not** yet been verified.

## Goal

Turn a Zynq-7020 + AD9361 board into a compact stand-alone SDR instrument with spectrum, optional waterfall and receiver metrics. This is a system-integration exercise, not merely an LCD driver: every displayed number needs a traceable source.

Prerequisites: Block 3 FFT and frequency axes, Block 8 link metrics, Block 9 IQ/IIO analysis and Block 10 electrical bring-up.

## Equipment and assumptions

- Zynq-7020 + AD9361 board with a known-good Linux/IIO and FPGA image;
- 2.8-inch SPI TFT, 240×320 pixels (landscape 320×240), optionally with a resistive touchscreen;
- multimeter, short wires and actual pin documentation for both boards;
- a level shifter **only when** the measured I/O voltages require one.

The controller is **not confirmed**. ILI9341 is a likely candidate, not an established fact. The touch controller and optional MISO need independent identification.

## Architecture

```text
AD9361 → PL/AXI → IQ samples / modem results → Linux on PS
                                             ├─ FFT / level → spectrum bins
                                             ├─ CFO, EVM, BER → telemetry
                                             └─ display adapter → SPI TFT
```

Choose a data source that actually exists in the loaded design: IIO, modem registers, or a reproducible IQ recording. Do not forward raw continuous IQ to the LCD. Send downsampled spectrum bins and a compact metrics structure. Start with a synthetic spectrum renderer, without changing the FPGA image.

**The current ZynqSDR design uses SPI0 for AD9361 control.** Do not attach a screen to the same signals, or treat `/dev/spidev0.0` as a spare display bus without checking the hardware design and device tree. Options are separately verified spare GPIOs with software SPI, or a properly routed SPI1/EMIO/PL controller. A header pin is not automatically a Linux-accessible signal.

## Stage 1: Electrical bring-up (power disconnected)

1. Identify TFT VCC and logic-level requirements, the selected Zynq GPIO bank voltage, HV/LV supplies and a shared ground from documentation and measurement. **Do not assume all Zynq GPIO is 3.3 V.**
2. Record TFT pins GND, VCC, LCD_CS, RESET, DC, MOSI/SDI, SCK and LED. Keep touchscreen and microSD connections out of the initial driver.
3. Check adjacent solder joints for shorts, verify shifter direction/supply and whether it handles push-pull SPI, and ensure that no power pin is floating.
4. Build a wiring table: TFT signal → translator pin → Zynq physical pin → bank and voltage → evidence source.
5. Only then apply power and check idle logic levels. Do not interfere with the AD9361 SPI bus.

If a pin mapping or voltage cannot be confirmed, stop rather than guessing. Initial SPI bring-up can start around 0.5–1 MHz; the safe operating frequency must be established for the actual translator, wiring and TFT.

## Stage 2: LCD driver and pattern test

1. Identify the display-controller part from the module data and confirm its reset and initialization sequence.
2. Using only the verified independent interface, initialize the LCD and fill it with red, green, blue and black patterns.
3. Test portrait/landscape rotation, RGB/BGR order, text and rectangles.
4. Keep the display renderer independent from the FFT source. Touch and microSD are optional follow-ups.
5. Record GPIO assignments, SPI frequency, voltages, software versions and photographs of successful output.

**Bandwidth check:** a full 320×240 RGB565 image transfers `320 × 240 × 2 = 153,600` bytes. At 1 Mbit/s, pixel transfer alone takes at least **1.23 s**. Use partial redraws for spectrum/waterfall; determine actual update rate by measurement, not by assuming full-frame 10–30 fps.

## Stage 3: Spectrum and receive results

1. Draw an offline synthetic tone/noise spectrum first; verify frequency axis, FFT window, amplitudes and peak location.
2. Read a validated real IQ source (such as IIO), compute the FFT and map bins to display width. Show center frequency, sample bandwidth and acquisition settings.
3. Redraw only changed regions. Keep a bounded waterfall line buffer and measure PS and SPI overhead.
4. Add CFO, SNR, EVM, BER and sync status **only** when those values are available from the active receiver. Missing values must show “N/A”, not zero.
5. Label uncalibrated spectra dBFS or relative scale, never dBm without documented RF gain/path calibration.

## Acceptance and report

| Check | Evidence |
|---|---|
| Electrical safety | pin table, voltages and continuity results |
| LCD | documented color, text and rotation test |
| Synthetic signal | expected FFT peak and correct frequency axis |
| RF capture | LCD spectrum reconciled with stored IQ/reference FFT under identical settings |
| Metrics | source, units, update cadence and missing-data state |
| Performance | measured display rate and PS load; AD9361/IIO still functional |
| Reproducibility | FPGA/Linux versions, controller ID, wiring and commands |

**Evidence boundaries:** a wiring plan is not a verified board; synthetic display data is not RF evidence; displayed values are not calibrated measurements by default.

## Extension

Show a received message from [Lab 11.46](lab-11-46-two-board-console-message.md) or later mailbox labs 11.49–11.52. A touchscreen mode selector is optional.

## References in this course

- [Lab 11.3: FPGA/RF integration](lab-11-3-fpga-rf-integration-checklist.md)
- [Lab 9.2: IQ reader and spectrum](lab-9-2-read-ci16-iq-and-analyze.md)
- [Block 10: electrical bring-up](../blocks/10-kicad-and-basic-electronics.md)
