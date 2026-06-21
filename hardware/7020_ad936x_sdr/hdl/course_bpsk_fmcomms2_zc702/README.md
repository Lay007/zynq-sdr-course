# Course BPSK FMCOMMS2 Overlay for the CLG400 Zynq SDR

This directory is the course-specific Vivado overlay for the imported AD9361/FMCOMMS2 reference captured from the working board image. It keeps the vendor HDL baseline intact and adds one deterministic BPSK burst path suitable for the first over-the-air discovery experiment.

## What this overlay changes

- targets the real board part `xc7z020clg400-2`;
- reuses the imported vendor AD9361 block-design shell from `vendor_system_bd_clg400.tcl`;
- adds an `axi_gpreg` control/status plane at `0x79040000`;
- inserts `bpsk_zynq_ber_gpreg_bridge.v`, which clocks the modem from `util_ad9361_divclk/clk_out`;
- keeps the optional `axi_gpreg` clock-monitor input disabled, because the live overlap probe on `2026-06-21` linked that path to AXI-Lite external-abort failures during concurrent host IIO capture;
- routes `RX1 I/Q` samples from `util_ad9361_adc_fifo` into the BPSK BER core;
- keeps the stock DAC DMA and `util_ad9361_dac_upack` blocks instantiated for Linux compatibility, but overrides the DAC FIFO write-side samples through a small mux so the deterministic BPSK burst still owns the RF transmit waveform.

That last point is intentional: this overlay is for the first short discovery burst, not for general IIO TX streaming, but it no longer breaks the Linux expectation that the DAC DMA path exists in hardware.

## Control-plane contract

Base address: `0x79040000`

| Offset | Meaning |
|---|---|
| `0x000` | `axi_gpreg` version register |
| `0x004` | `axi_gpreg` ID, configured to `0x4250534B` |
| `0x404` | GPREG0 output: control word, bit `0` = start edge, bit `1` = clear sticky done |
| `0x408` | GPREG0 input: status word, bit `0` = synchronized start level, bit `1` = busy, bit `2` = sticky done, bit `3` = sticky RX timeout/abort |
| `0x444` | GPREG1 output: `FRAME_BIT_COUNT` |
| `0x448` | GPREG1 input: `RECEIVED_BITS` |
| `0x484` | GPREG2 output: `PREAMBLE_COUNT` |
| `0x488` | GPREG2 input: `TOTAL_ERRORS` |
| `0x4C4` | GPREG3 output: `START_OFFSET` |
| `0x4C8` | GPREG3 input: `PAYLOAD_ERRORS` |
| `0x508` | GPREG4 input: bridge signature word `0x4250534B` |

## Build prerequisites

The Block 5 ROM images are generated files and are intentionally not committed. Generate them from the repository root before running Vivado:

```bash
python blocks/block_05_fpga_hdl_flow/python/generate_bpsk_rrc_tx_fir_vectors.py
python blocks/block_05_fpga_hdl_flow/python/generate_bpsk_framed_loopback_vectors.py
```

## Vivado flow

Use Vivado `2021.1` from the repository root:

```bash
vivado -mode batch -source hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/system_project.tcl
vivado -mode batch -source hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/build_bitstream.tcl
```

The scripts create the project under `build/` and place the stable handoff artifacts here:

- bitstream: `build/course_bpsk_fmcomms2_zc702.runs/impl_1/system_top.bit`
- hardware handoff: `course_bpsk_fmcomms2_zc702.sdk/system_top.xsa`
- timing logs: `timing_synth.log` and `timing_impl.log`

The current clean build closes timing and exports `system_top.xsa` without the earlier `bad_timing` fallback.

## Runtime loading note

The current safe engineering assumption is:

- use this overlay as a boot-time PL image, not as a hot PL reload on top of a live Linux IIO stack;
- if you must reload it at runtime for debugging, re-validate both `iio_readdev` and `axi_gpreg` access afterwards before trusting any BER or RF result.

That guidance is based on the live `2026-06-21` probe:

- removing the gpreg clock monitor cleared the earlier `0x79040004` external-abort / `Bus error` symptom;
- reloading the new PL image through `fpga_manager` while Linux was already running left `gpreg` readable again, but standalone `iio_readdev` capture no longer refilled cleanly;
- manually booting Linux after a real U-Boot `fpga load` of the course bitstream showed that deleting the DAC DMA path from the PL shell causes a kernel panic in `axi_dmac_probe()`;
- attempting to recover the RX DMA path with Linux `unbind` / `bind` triggered a kernel oops in `dma_channel_rebalance()`.

## Intended first RF run

1. Keep AD9361 TX attenuation at the minimum output power setting available on the board.
2. Keep RX gain low and manual. Do not enable AGC for the first burst.
3. Use short frames only.
4. Confirm both the `axi_gpreg` ID and the bridge signature before transmitting.
5. If RX never reconstructs the full frame, the BER core exits through the sticky timeout bit instead of hanging forever.
6. Treat this overlay as discovery-only until the first live BER capture is documented.
