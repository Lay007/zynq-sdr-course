# Lab 11.8 - AD9361 gpreg BPSK overlay and first discovery burst

## Goal

Move from the placeholder AXI-Lite bring-up path to the first course-specific AD9361 hardware overlay that preserves a PS-visible control plane while the exact board-matched boot shell is re-established:

```text
PS / software -> axi_gpreg @ 0x79040000 -> staged sample-domain bridge -> AD9361 TX/RX path
```

This lab is the first clean handoff from the executable Block 5 modem toward the imported vendor AD9361 shell that matches the real course board (`xc7z020clg400-2`).

## Engineering decision

As of `2026-06-21`, the checked-in overlay mode is intentionally reduced to `gpreg_only`.

That rollback is deliberate:

- it keeps the control path simple and inspectable;
- it preserves the Linux-visible RX and TX DMA shell so the stock device tree still probes cleanly;
- it separates `axi_gpreg` address-map validation from the harder AD9361 clean-boot problem;
- it avoids treating a rebuilt but not yet boot-safe PL image as a valid RF measurement baseline.

The earlier burst-enabled TX experiments remain useful as historical evidence, but they are not the current safe checked-in baseline. The next gated step is to splice the sample-domain bridge back into the exact stock shell and rerun clean-boot validation before more RF discovery work.

## New hardware files

| File | Purpose |
|---|---|
| `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/system_project.tcl` | creates the clean course Vivado project for `xc7z020clg400-2` |
| `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/system_bd.tcl` | sources the imported AD9361 baseline and adds the course overlay |
| `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/vendor_system_bd_clg400.tcl` | frozen vendor block-design shell extracted from the working board image |
| `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/build_bitstream.tcl` | deterministic batch build that emits the course bitstream and XSA |
| `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/bpsk_zynq_ber_gpreg_bridge.v` | staged clock-domain bridge for the next sample-path reintegration step |
| `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/course_dac_fifo_source_mux.v` | staged TX-path mux kept for the later DAC reintegration step, not enabled in the current `gpreg_only` mode |
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

There are two evidence layers and they should not be conflated.

Historical burst-enabled overlay evidence:

The earlier hardware overlay was rebuilt, loaded through Linux `fpga_manager`, and probed from the host over Ethernet.

Historical evidence paths:

- XSA: `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/course_bpsk_fmcomms2_zc702.sdk/system_top.xsa`;
- bitstream: `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/build/course_bpsk_fmcomms2_zc702.runs/impl_1/system_top.bit`;
- live helper report: `docs/assets/lab118_axi_gpreg_bringup_live.json`.

Observed historical facts on the board:

- `devmem 0x79040000 32 -> 0x00040063`;
- `devmem 0x79040004 32 -> 0x4250534B`;
- `devmem 0x79040508 32 -> 0x4250534B`;
- helper result: `final_status = 0x0000080C`;
- `done_observed = true`;
- `timed_out_observed = true`;
- `received_bits = 0`;
- RF setup during the discovery run: TX attenuation `-60 dB`, RX gain manual `20 dB`, AGC disabled.

Current checked-in safety baseline:

- the boot-time PL reference is `hardware/7020_ad936x_sdr/stock_system_top_from_BOOT.bin`;
- `hardware/7020_ad936x_sdr/boot/validate_clean_boot_overlay.py` passes against that extracted stock image with AD9361 initialized and `4` IIO devices alive;
- regenerated boot-time candidates from both `AD936X_PL.zip` and `AD936X_only_PL.zip` were rejected and summarized in `docs/assets/lab112_clean_boot_pl_validation.json`.

Interpretation:

- the PS-to-PL gpreg control plane was validated on real hardware at least once in the earlier burst-enabled overlay;
- the current checked-in HDL intentionally steps back to a smaller boot-safe scope;
- the immediate next task is not BER tuning but restoring the sample-domain bridge around the exact stock shell, then rerunning this helper under clean boot.

## Next gated re-enable order

1. Confirm that the custom boot-time PL image still passes the clean-boot validator.
2. Confirm the board IP, `axi_gpreg` ID register, and bridge signature before writing frame parameters.
3. Re-enable the sample-domain bridge while keeping the Linux-visible DMA shell intact.
4. Keep AD9361 TX attenuation at the minimum output power setting available on the board.
5. Keep RX gain low and manual. Do not enable AGC for the first renewed burst.
6. Launch one short burst only.
7. Observe `busy` and then `done` or `done after timeout`.
8. Read `RECEIVED_BITS`, `TOTAL_ERRORS`, and `PAYLOAD_ERRORS`.
9. Only then resume repeated sweeps or BER campaigns.

## Report checklist

- [ ] Attach the regenerated XSA path and confirm `axi_gpreg_bpsk`.
- [ ] Attach the regenerated bitstream path.
- [ ] Show the `0x79040000` base address in the exported handoff.
- [ ] Record one successful ID readback and one successful signature readback.
- [ ] Show programmed `FRAME_BIT_COUNT`, `PREAMBLE_COUNT`, and `START_OFFSET`.
- [ ] State whether `busy`, `done`, and `timeout` were observed.
- [ ] Record `RECEIVED_BITS`, `TOTAL_ERRORS`, and `PAYLOAD_ERRORS`.
- [ ] List the AD9361 TX attenuation and RX gain used for the first renewed burst.

## Engineering conclusion template

```text
The gpreg-based AD9361 overlay is ready / not ready as a clean-boot baseline.
The exported handoff contains / does not contain the expected control window.
The next gated reintegration step is ______ and its success criterion is ______.
```
