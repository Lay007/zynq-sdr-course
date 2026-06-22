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

The earlier burst-enabled TX experiments remain useful as historical evidence, but they are not the current safe checked-in baseline. The next gated step is to treat the extracted stock BOOT-partition payload as the only externally loaded boot-safe anchor for now, then explain why the source-correlated editable shells still lose AD9361 before more RF discovery work.

## New hardware files

| File | Purpose |
|---|---|
| `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/system_project.tcl` | creates the clean course Vivado project for `xc7z020clg400-2` |
| `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/system_bd.tcl` | sources the imported AD9361 baseline and adds the course overlay |
| `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/vendor_system_bd_clg400.tcl` | frozen vendor block-design shell extracted from the working board image |
| `hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/build_bitstream.tcl` | deterministic batch build that emits the course bitstream and XSA |
| `hardware/7020_ad936x_sdr/rebuild_vendor_xpr_snapshot_mio_patch.tcl` | disposable Vivado flow that rebuilds the saved vendor `zc702.xpr` snapshot after patching only `sys_ps7` MIO14/15 |
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

- the stock-safe recovery path is still `hardware/7020_ad936x_sdr/stock_system_top_from_BOOT.bin`; under the old `uEnv.txt` `loadb`-on-`.bit.bin` fallback it was not proof of arbitrary external PL replacement, but under the new manual UART `fpga load` path it is now the only externally loaded boot-safe candidate demonstrated so far;
- the extracted stock BOOT partition is also the only externally loaded PL payload that now passes manual UART `fpga load` with AD9361 still alive; see `docs/assets/lab112_clean_boot_pl_validation.json`;
- the standalone vendor reference `hardware/7020_ad936x_sdr/ps/ad936x_no_os_reference/platform/hw/system_top.bit` remains the source-correlated raw control candidate, but it still fails AD9361 both as raw `fpga loadb` and as manual `.bit.bin` `fpga load`;
- `hardware/7020_ad936x_sdr/boot/validate_clean_boot_overlay.py` captures the decisive UART evidence for raw `fpga loadb`, while `hardware/7020_ad936x_sdr/boot/validate_manual_uart_fpga_load.py` now covers the manual `.bit.bin` `fpga load` path;
- the rebuilt `vendor_only` shell now also passes Vivado project creation, implementation, bitstream generation, and XSA export, but still fails clean boot with the same AD9361 calibration timeout;
- the new `bridge_rx_only` mode now passes Vivado project creation, implementation, bitstream generation, and XSA export;
- the saved vendor `zc702.xpr` snapshot, rebuilt through `hardware/7020_ad936x_sdr/rebuild_vendor_xpr_snapshot_mio_patch.tcl`, still exports an XSA with zero module/memrange/parameter drift against the vendor reference, but its direct raw `system.bit` load still fails AD9361 clean boot with the same calibration timeout;
- the newer `bridge_txrx_mux` raw-clean-boot candidate now proves that the course-owned overlay really reaches PL and exposes `axi_gpreg` on the board after reboot; see `docs/assets/lab118_axi_gpreg_bringup_cleanboot_raw.json`;
- the Bootgen-converted `bridge_txrx_mux.bit.bin` candidate is currently rejected by U-Boot `fpga load` with `zynq_validate_bitstream: Bitstream is not validated yet (diff 1700)`, so the later healthy AD9361 state in that path comes from the untouched stock PL shell;
- regenerated boot-time candidates from both `AD936X_PL.zip` and `AD936X_only_PL.zip` were rejected and summarized in `docs/assets/lab112_clean_boot_pl_validation.json`.

Interpretation:

- the PS-to-PL gpreg control plane was validated on real hardware at least once in the earlier burst-enabled overlay;
- the same gpreg control plane is now also readable after a direct raw clean boot of the `bridge_txrx_mux` candidate, with both ID and signature equal to `0x4250534B`, `tx_valid_count > 0`, and `rx_valid_count == 0`;
- the normalized pure-Tcl `vendor_only` flow now eliminates the earlier `MIO14/15` drift, but it is still blocked by four read-only or disabled derived parameters: `sys_ps7.PCW_S_AXI_HP0_FREQMHZ`, `axi_ad9361_adc_dma.DMA_AXI_PROTOCOL_SRC`, `axi_ad9361_dac_dma.DMA_AXI_PROTOCOL_DEST`, and `axi_ad9361.SPEED_GRADE`; see `docs/assets/vendor_reference_vs_vendor_only_handoff_diff.json`;
- the saved vendor `zc702.xpr` snapshot is still the preferred editable source witness once rebuilt through the MIO14/15 patch flow, but it is not yet a boot-safe RF baseline; see `docs/assets/vendor_reference_vs_vendor_xpr_mio14_15_patch_handoff_diff.json`;
- the current checked-in HDL now also includes an intermediate `bridge_rx_only` reintegration mode that is validated in Vivado but not yet in clean boot;
- the extracted stock partition from `BOOT.bin` is now the only externally loaded boot-safe reintegration anchor, but it is not yet editable or source-correlated enough for the final course overlay;
- the immediate next task is to explain why that stock payload survives manual `fpga load` while the source-correlated and course-owned candidates do not, not to assume that zero XSA drift alone makes the patched snapshot boot-safe.

## Next gated re-enable order

1. Confirm that the candidate custom boot-time PL image is accepted by the relevant validator path: raw `.bit` through `validate_clean_boot_overlay.py` or `.bit.bin` through `validate_manual_uart_fpga_load.py`.
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
