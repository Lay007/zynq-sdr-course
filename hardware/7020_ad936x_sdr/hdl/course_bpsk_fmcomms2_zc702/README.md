# Course BPSK FMCOMMS2 Overlay for ZC702

This directory is the course-specific Vivado overlay for the imported AD9361/FMCOMMS2 reference. It keeps the vendor HDL baseline intact and adds one deterministic BPSK burst path suitable for the first over-the-air discovery experiment.

## What this overlay changes

- reuses the imported ZC702 + AD9361 block-design baseline from `../adi_fmcomms2_reference/`;
- adds an `axi_gpreg` control/status plane at `0x79040000`;
- inserts `bpsk_zynq_ber_gpreg_bridge.v`, which clocks the modem from `util_ad9361_divclk/clk_out`;
- routes `RX1 I/Q` samples from `util_ad9361_adc_fifo` into the BPSK BER core;
- bypasses the normal TX DMA to drive the DAC FIFO directly from the BPSK burst generator.

That last point is intentional: this overlay is for the first short discovery burst, not for general IIO TX streaming.

## Control-plane contract

Base address: `0x79040000`

| Offset | Meaning |
|---|---|
| `0x000` | `axi_gpreg` version register |
| `0x004` | `axi_gpreg` ID, configured to `0x4250534B` |
| `0x404` | GPREG0 output: control word, bit `0` = start edge, bit `1` = clear sticky done |
| `0x408` | GPREG0 input: status word, bit `0` = synchronized start level, bit `1` = busy, bit `2` = sticky done |
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

Use Vivado `2021.1`:

```bash
cd hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702
vivado -mode batch -source system_project.tcl
```

The script creates the project under `build/`. After that, continue with bitstream export and XSA handoff in Vivado or Vitis.

## Intended first RF run

1. Keep AD9361 TX attenuation at the minimum output power setting available on the board.
2. Keep RX gain low and manual. Do not enable AGC for the first burst.
3. Use short frames only.
4. Confirm both the `axi_gpreg` ID and the bridge signature before transmitting.
5. Treat this overlay as discovery-only until the first live BER capture is documented.
