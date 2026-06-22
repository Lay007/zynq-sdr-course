# 7020 AD936x SDR Start Bundle

This bundle is the local starting point for the external `D:\7020\7020_AD936X_SDR` board materials. It is curated for bring-up and integration work inside `zynq-sdr-course`.

## Why this bundle exists

The original vendor folder mixes useful board assets with heavy archives, Windows installers, duplicated firmware packages and unrelated host-side tools. This bundle keeps the parts that are useful for:

- understanding the board and its boot flow;
- reusing an AD936x HDL reference as a baseline;
- reusing a no-OS PS application for AD936x control;
- running simple PS bring-up tests before deeper SDR work.

## Included structure

| Path | Purpose |
|---|---|
| `docs/` | board PDFs copied from the vendor bundle |
| `boot/sd_image/` | extracted SD boot files: `BOOT.bin`, `uImage`, `devicetree.dtb`, `uramdisk.image.gz`, `uEnv.txt` |
| `boot/course_clean/` | course-owned boot overlay: deterministic `eth0`, DHCP, safe TX defaults via `autorun.sh`, plus a U-Boot `uEnv` override for the clean BPSK PL image |
| `boot/notes/` | vendor boot notes and small screenshots for FAT/EXT/IIO setup |
| `hdl/adi_fmcomms2_reference/` | curated HDL reference extracted from `AD936X_PL.zip` |
| `hdl/course_bpsk_fmcomms2_zc702/` | course-specific Vivado overlay that inserts the deterministic BPSK modem into the imported AD9361 baseline |
| `hdl/test_pl_reference/` | small test PL block-design project extracted from `Test_PL.zip` |
| `ps/ad936x_no_os_reference/` | AD936x no-OS PS application and exported hardware platform |
| `ps/bringup_tests/` | DDR, eMMC, Ethernet, LED and USB PS test applications plus the matching exported hardware handoff |

## Key files

| Item | Why open it |
|---|---|
| [`docs/7020_936x_SDR.pdf`](docs/7020_936x_SDR.pdf) | board description PDF from the vendor package |
| [`docs/Fish_Ball_SDR_ru.pdf`](docs/Fish_Ball_SDR_ru.pdf) | Russian board guide PDF |
| [`boot/notes/pluto_sd_boot_readme.txt`](boot/notes/pluto_sd_boot_readme.txt) | shortest path for SD-card boot |
| [`boot/extract_stock_system_top_partition.py`](boot/extract_stock_system_top_partition.py) | extracts the known-good PL partition from `boot/sd_image/BOOT.bin` when a rebuilt Vivado bitstream is still being debugged |
| [`boot/build_system_bit_bin.py`](boot/build_system_bit_bin.py) | converts a raw `.bit` into a Bootgen `.bit.bin` payload for runtime Linux loading or for manual U-Boot `fpga load` experiments |
| [`boot/validate_clean_boot_overlay.py`](boot/validate_clean_boot_overlay.py) | uploads a candidate raw `system.bit`, syncs the matching `uEnv.txt`, reboots the board, captures UART, and verifies whether AD9361/IIO survive the direct `fpga loadb` path |
| [`boot/validate_manual_uart_fpga_load.py`](boot/validate_manual_uart_fpga_load.py) | stops autoboot over UART, runs `load mmc` + `fpga load` manually for a `.bit.bin` payload, boots Linux, and verifies whether AD9361/IIO survived the externally loaded partition |
| [`rebuild_vendor_xpr_snapshot_mio_patch.tcl`](rebuild_vendor_xpr_snapshot_mio_patch.tcl) | disposable Vivado flow that patches only `sys_ps7` MIO14/15 on the saved vendor `zc702.xpr` snapshot before synth/impl/export |
| [`compare_xsa_handoffs.py`](compare_xsa_handoffs.py) | compares two XSA handoffs down to `ps7_init`, `system.hwh` modules, parameter drift, and memranges |
| [`../../docs/assets/lab112_clean_boot_pl_validation.json`](../../docs/assets/lab112_clean_boot_pl_validation.json) | persistent summary of which candidate boot-time PL images clean-booted successfully and which ones failed |
| [`../../docs/assets/vendor_reference_vs_vendor_only_handoff_diff.json`](../../docs/assets/vendor_reference_vs_vendor_only_handoff_diff.json) | source-level diff between the vendor reference XSA and the rebuilt `vendor_only` shell |
| [`../../docs/assets/vendor_reference_vs_vendor_xpr_snapshot_handoff_diff.json`](../../docs/assets/vendor_reference_vs_vendor_xpr_snapshot_handoff_diff.json) | source-level diff showing the historical unpatched `zc702.xpr` snapshot drift against the vendor reference XSA |
| [`../../docs/assets/vendor_reference_vs_vendor_xpr_mio14_15_patch_handoff_diff.json`](../../docs/assets/vendor_reference_vs_vendor_xpr_mio14_15_patch_handoff_diff.json) | source-level diff showing that the MIO14/15-patched vendor snapshot rebuild reaches zero structural drift against the vendor reference XSA |
| [`ps/ad936x_no_os_reference/platform/hw/system_top.bit`](ps/ad936x_no_os_reference/platform/hw/system_top.bit) | standalone vendor reference raw bitstream used to confirm that U-Boot `fpga loadb` really reaches the fabric on this board, even though that source-correlated payload still breaks AD9361 clean boot |
| [`hdl/adi_fmcomms2_reference/projects/common/zc702/zc702_system_bd.tcl`](hdl/adi_fmcomms2_reference/projects/common/zc702/zc702_system_bd.tcl) | common Zynq-7020 board TCL baseline |
| [`hdl/adi_fmcomms2_reference/projects/scripts/adi_project_xilinx.tcl`](hdl/adi_fmcomms2_reference/projects/scripts/adi_project_xilinx.tcl) | ADI Xilinx project-generation helper |
| [`hdl/adi_fmcomms2_reference/projects/fmcomms2/zc702/zc702.xpr`](hdl/adi_fmcomms2_reference/projects/fmcomms2/zc702/zc702.xpr) | generated Vivado project snapshot that now serves as the closest editable structural baseline when rebuilt through the MIO patch flow |
| [`hdl/course_bpsk_fmcomms2_zc702/system_project.tcl`](hdl/course_bpsk_fmcomms2_zc702/system_project.tcl) | clean course build entrypoint for the first BPSK discovery-burst overlay |
| [`ps/ad936x_no_os_reference/AD936X/src/main.c`](ps/ad936x_no_os_reference/AD936X/src/main.c) | main AD936x no-OS application |
| [`ps/ad936x_no_os_reference/platform/hw/system_top.xsa`](ps/ad936x_no_os_reference/platform/hw/system_top.xsa) | exported hardware platform for Vitis |
| [`ps/bringup_tests/design_1_wrapper/ps7_summary.html`](ps/bringup_tests/design_1_wrapper/ps7_summary.html) | captured PS7 clock, DDR and peripheral summary used as board clock provenance |
| [`ps/bringup_tests/DDR_Test/src/test01.c`](ps/bringup_tests/DDR_Test/src/test01.c) | DDR diagnostic and eye-measurement test |
| [`ps/bringup_tests/EMMC_Test/src/main.c`](ps/bringup_tests/EMMC_Test/src/main.c) | minimal eMMC/FAT read-write test |
| [`ps/bringup_tests/ETH_FreeRTOS/src/main.c`](ps/bringup_tests/ETH_FreeRTOS/src/main.c) | Ethernet/FreeRTOS TCP server bring-up |
| [`ps/bringup_tests/LED/src/main.c`](ps/bringup_tests/LED/src/main.c) | minimal PS GPIO blink sanity test |

## Suggested first use

1. Read the board PDFs in `docs/`.
2. Prepare the SD card using `boot/sd_image/` and the notes in `boot/notes/`.
3. If you need the course-clean management profile on the stock Pluto-like image, apply `boot/course_clean/autorun.sh` as `/mnt/jffs2/autorun.sh`.
4. If you need the first clean boot-time BPSK overlay, place the generated raw `system.bit` on the FAT partition root and copy `boot/course_clean/uEnv_course_bpsk_overlay.txt` there as `uEnv.txt`. That U-Boot overlay must use `fpga loadb` for raw `.bit`; trying to feed a Bootgen `system.bit.bin` to the same path leaves the stock `BOOT.bin` PL image in place even though Linux still comes up.
5. If the rebuilt Vivado raw `system.bit` still breaks AD9361 calibration, regenerate the stock BOOT-partition payload instead:

```bash
python hardware/7020_ad936x_sdr/boot/extract_stock_system_top_partition.py
```

This emits `hardware/7020_ad936x_sdr/stock_system_top_from_BOOT.bin`, which is currently the only externally loaded boot-safe baseline proven to keep AD9361 alive on this board.
6. To prove that an arbitrary raw `.bit` candidate really reaches PL through `fpga loadb`, run:

```bash
python hardware/7020_ad936x_sdr/boot/validate_clean_boot_overlay.py
```

7. To validate a `.bit.bin` payload through the correct manual UART `fpga load` path, run:

```bash
python hardware/7020_ad936x_sdr/boot/validate_manual_uart_fpga_load.py \
  --candidate hardware/7020_ad936x_sdr/stock_system_top_from_BOOT.bin
```

That helper uploads the file to the FAT boot partition if needed, stops autoboot over UART, executes `load mmc` plus `fpga load`, boots Linux, and then checks whether AD9361 plus the expected IIO devices came back cleanly.
8. Treat the standalone `ps/ad936x_no_os_reference/platform/hw/system_top.bit` only as the source-correlated control candidate for the raw-bit path. On `2026-06-22`, it was accepted by raw `fpga loadb` and by manual `.bit.bin` `fpga load`, but both routes still ended with `ad9361 spi0.0: Calibration TIMEOUT (0x244, 0x80)`. That file still matches both `AD936X_PS.zip::platform/hw/system_top.bit` and `AD936X_PS.zip::AD936X/_ide/bitstream/system_top.bit`.
9. Rebuild a Bootgen payload reproducibly with:

```bash
python hardware/7020_ad936x_sdr/boot/build_system_bit_bin.py \
  hardware/7020_ad936x_sdr/ps/ad936x_no_os_reference/platform/hw/system_top.bit
```

The manual UART validator can consume that generated `.bit.bin` directly:

```bash
python hardware/7020_ad936x_sdr/boot/validate_manual_uart_fpga_load.py \
  --candidate hardware/7020_ad936x_sdr/ps/ad936x_no_os_reference/platform/hw/system_top.bit.bin
```

10. The current matrix is now sharper: the extracted stock BOOT.bin partition passes manual `fpga load`, the source-correlated vendor-reference `.bit.bin` is accepted but still fails AD9361, and the Bootgen-converted `bridge_txrx_mux.bit.bin` is rejected by U-Boot validation (`diff 1700`) before Linux starts. See `../../docs/assets/lab112_clean_boot_pl_validation.json` for the persistent summary.
11. The saved vendor `hdl/adi_fmcomms2_reference/projects/fmcomms2/zc702/zc702.xpr` snapshot is still the preferred editable rebuild witness when driven through `rebuild_vendor_xpr_snapshot_mio_patch.tcl`. On `2026-06-22`, that flow patched only `sys_ps7` MIO14/15 directions and exported an XSA with zero module/memrange/parameter drift against the vendor reference handoff, but the resulting raw `system.bit` still reproduced the same AD9361 calibration timeout on the direct `fpga loadb` path.
12. Run that editable snapshot rebuild with:

```bash
vivado -mode batch -source hardware/7020_ad936x_sdr/rebuild_vendor_xpr_snapshot_mio_patch.tcl
```

13. If you need to debug why another rebuilt source shell still diverges, compare its exported XSA directly against the vendor reference handoff:

```bash
python hardware/7020_ad936x_sdr/compare_xsa_handoffs.py \
  hardware/7020_ad936x_sdr/ps/ad936x_no_os_reference/platform/hw/system_top.xsa \
  hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/course_bpsk_fmcomms2_zc702.sdk/system_top.xsa \
  --lhs-label vendor_reference_xsa \
  --rhs-label candidate_rebuild_xsa
```

14. Inspect the AD936x no-OS app in `ps/ad936x_no_os_reference/` and compare its parameters with your board target.
15. Use `ps/bringup_tests/` for board sanity checks before SDR-specific debugging.
16. Use the HDL reference under `hdl/adi_fmcomms2_reference/` as the baseline when mapping course HDL work toward a Zynq/AD936x platform.
17. Use `hdl/course_bpsk_fmcomms2_zc702/` when you need the next course-owned overlay, but treat the extracted stock partition as the only currently proven boot-safe external PL baseline. The patched vendor snapshot remains the structural anchor, not yet a radio-safe one.

## Deliberately omitted

- Windows driver installers and bundled SDR desktop tools;
- `SecureCRT5.5` and its activation-related files;
- the large raw SD-card image `xk_ZYNQ7020_AD9361.img`;
- duplicate zip archives whose extracted payload is already present here;
- 3D CAD payloads that do not help software, boot or FPGA bring-up.

## Related course pages

- [`docs/hardware-checklist.md`](../../docs/hardware-checklist.md)
- [`docs/hardware-bringup-checklist.md`](../../docs/hardware-bringup-checklist.md)
- [`docs/hardware-experiment-roadmap.md`](../../docs/hardware-experiment-roadmap.md)
- [`docs/hardware-validation-backlog.md`](../../docs/hardware-validation-backlog.md)
