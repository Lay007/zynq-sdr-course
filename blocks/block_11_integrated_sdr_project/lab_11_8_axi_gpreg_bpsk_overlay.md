# Lab 11.8 - AD9361 gpreg BPSK overlay and first discovery burst

## Goal

Move from the placeholder AXI-Lite bring-up path to the first course-specific AD9361 hardware overlay that has a real control plane and a deterministic burst modem in the sample path:

```text
PS / software -> axi_gpreg @ 0x79040000 -> sample-domain BPSK core -> AD9361 TX/RX path
```

This lab is the first clean handoff from the executable Block 5 modem toward the imported vendor AD9361 shell that matches the real course board (`xc7z020clg400-2`).

## Engineering decision

For the first over-the-air discovery burst, the course overlay intentionally bypasses the normal TX DMA path and drives the DAC FIFO directly from the deterministic BPSK burst core.

That tradeoff is deliberate:

- it keeps the control path simple and inspectable;
- it preserves the RX DMA reference path for observation/debug;
- it reduces the number of moving parts before the first live burst.

General IIO TX streaming can be restored later, after the first live burst and BER evidence are captured.

## New hardware files

| File | Purpose |
|---|---|
| `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/system_project.tcl` | creates the clean course Vivado project for `xc7z020clg400-2` |
| `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/system_bd.tcl` | sources the imported AD9361 baseline and adds the course overlay |
| `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/vendor_system_bd_clg400.tcl` | frozen vendor block-design shell extracted from the working board image |
| `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/build_bitstream.tcl` | deterministic batch build that emits the course bitstream and XSA |
| `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/bpsk_zynq_ber_gpreg_bridge.v` | clock-domain bridge between `axi_gpreg` and the sample-domain BPSK BER core |
| `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/README.md` | build notes, register contract, and first-burst constraints |

## New software helper

| File | Purpose |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_8_axi_gpreg_bpsk_bringup.py` | programs the gpreg control words, launches one burst, polls `busy/done/timeout`, and reads BER counters |

## Register contract

Base address: `0x79040000`

| Offset | Meaning |
|---|---|
| `0x000` | `axi_gpreg` version register |
| `0x004` | `axi_gpreg` ID register, expected `0x4250534B` |
| `0x404` | GPREG0 output: control word, bit `0` = start edge, bit `1` = clear sticky done |
| `0x408` | GPREG0 input: status word, bit `0` = synchronized start level, bit `1` = busy, bit `2` = sticky done, bit `3` = sticky RX timeout/abort |
| `0x444` | GPREG1 output: `FRAME_BIT_COUNT` |
| `0x448` | GPREG1 input: `RECEIVED_BITS` |
| `0x484` | GPREG2 output: `PREAMBLE_COUNT` |
| `0x488` | GPREG2 input: `TOTAL_ERRORS` |
| `0x4C4` | GPREG3 output: `START_OFFSET` |
| `0x4C8` | GPREG3 input: `PAYLOAD_ERRORS` |
| `0x508` | GPREG4 input: bridge signature, expected `0x4250534B` |

## Build prerequisites

Generate the Block 5 memory files first:

```bash
python blocks/block_05_fpga_hdl_flow/python/generate_bpsk_rrc_tx_fir_vectors.py
python blocks/block_05_fpga_hdl_flow/python/generate_bpsk_framed_loopback_vectors.py
```

Then create the Vivado project and export the handoff:

```bash
vivado -mode batch -source hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/system_project.tcl
vivado -mode batch -source hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/build_bitstream.tcl
```

Expected outputs after a successful build:

1. bitstream at `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/build/course_bpsk_fmcomms2_zc702.runs/impl_1/system_top.bit`;
2. XSA at `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/course_bpsk_fmcomms2_zc702.sdk/system_top.xsa`;
3. timing logs at `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/timing_synth.log` and `timing_impl.log`;
4. confirm that the new XSA contains `axi_gpreg_bpsk` at `0x79040000`;
5. reuse the helper below on Linux or over SSH.

## Local mock run

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_8_axi_gpreg_bpsk_bringup.py \
  --backend mock \
  --json-out docs/assets/lab118_axi_gpreg_bringup_mock.json
```

Expected local behavior:

- both the `axi_gpreg` ID and the bridge signature read back as `0x4250534B`;
- `busy_observed` and `done_observed` are both `true`;
- `timed_out_observed` is `false`;
- `received_bits == frame_bit_count`;
- `total_errors == 0`;
- `payload_errors == 0`.

## Linux or SSH run

Direct Linux `/dev/mem` access on the board:

```bash
sudo python blocks/block_11_integrated_sdr_project/python/lab_11_8_axi_gpreg_bpsk_bringup.py \
  --backend mmap \
  --base-addr 0x79040000 \
  --frame-bit-count 281 \
  --preamble-count 25 \
  --start-offset 62 \
  --json-out reports/lab118_axi_gpreg_bringup.json
```

Host-side remote `devmem` access over Ethernet:

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_8_axi_gpreg_bpsk_bringup.py \
  --backend ssh-devmem \
  --ssh-host 192.168.40.1 \
  --ssh-user root \
  --ssh-password analog \
  --base-addr 0x79040000
```

## Current live evidence

The current hardware overlay has already been rebuilt, loaded through Linux `fpga_manager`, and probed from the host over Ethernet.

Live evidence paths:

- XSA: `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/course_bpsk_fmcomms2_zc702.sdk/system_top.xsa`;
- bitstream: `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/build/course_bpsk_fmcomms2_zc702.runs/impl_1/system_top.bit`;
- live helper report: `docs/assets/lab118_axi_gpreg_bringup_live.json`.

Observed live facts on the board:

- `devmem 0x79040000 32 -> 0x00040063`;
- `devmem 0x79040004 32 -> 0x4250534B`;
- `devmem 0x79040508 32 -> 0x4250534B`;
- helper result: `final_status = 0x0000080C`;
- `done_observed = true`;
- `timed_out_observed = true`;
- `received_bits = 0`;
- RF setup during the discovery run: TX attenuation `-60 dB`, RX gain manual `20 dB`, AGC disabled.

Interpretation:

- the PS-to-PL gpreg control plane is alive on real hardware;
- the bridge signature and address map are correct after runtime loading;
- the burst no longer hangs forever when RX does not recover the frame;
- the next task is RF/link tuning, because the current run exits cleanly but still reconstructs zero bits.

## First live-burst order

1. Confirm the clean image and board IP before transmitting.
2. Keep AD9361 TX attenuation at the minimum output power setting available on the board.
3. Keep RX gain low and manual.
4. Disable AGC for the first burst.
5. Read the `axi_gpreg` ID register and the bridge signature before writing the frame parameters.
6. Launch one short burst only.
7. Observe `busy` then either `done` or `done after timeout`.
8. Read `RECEIVED_BITS`, `TOTAL_ERRORS`, and `PAYLOAD_ERRORS`.
9. Keep AD9361 TX on the minimum practical power and RX gain low/manual for this first run.
10. Only then expand toward repeated bursts or BER campaigns.

## Report checklist

- [ ] Attach the regenerated XSA path and confirm `axi_gpreg_bpsk`.
- [ ] Attach the regenerated bitstream path.
- [ ] Show the `0x79040000` base address in the exported handoff.
- [ ] Record one successful ID readback and one successful signature readback.
- [ ] Show programmed `FRAME_BIT_COUNT`, `PREAMBLE_COUNT`, and `START_OFFSET`.
- [ ] State whether `busy`, `done`, and `timeout` were observed.
- [ ] Record `RECEIVED_BITS`, `TOTAL_ERRORS`, and `PAYLOAD_ERRORS`.
- [ ] List the AD9361 TX attenuation and RX gain used for the first burst.

## Engineering conclusion template

```text
The gpreg-based AD9361 BPSK overlay is ready / not ready.
The exported handoff contains / does not contain the expected control window.
The first discovery burst produced ______ and the next step is ______.
```
