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
| [`hdl/adi_fmcomms2_reference/projects/common/zc702/zc702_system_bd.tcl`](hdl/adi_fmcomms2_reference/projects/common/zc702/zc702_system_bd.tcl) | common Zynq-7020 board TCL baseline |
| [`hdl/adi_fmcomms2_reference/projects/scripts/adi_project_xilinx.tcl`](hdl/adi_fmcomms2_reference/projects/scripts/adi_project_xilinx.tcl) | ADI Xilinx project-generation helper |
| [`hdl/adi_fmcomms2_reference/projects/fmcomms2/zc702/zc702.xpr`](hdl/adi_fmcomms2_reference/projects/fmcomms2/zc702/zc702.xpr) | generated Vivado project snapshot |
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
4. If you need the first clean boot-time BPSK overlay, place the generated `system.bit.bin` on the FAT partition root and copy `boot/course_clean/uEnv_course_bpsk_overlay.txt` there as `uEnv.txt`.
5. If the rebuilt Vivado `system.bit.bin` still breaks AD9361 calibration, regenerate the known-good stock PL partition instead:

```bash
python hardware/7020_ad936x_sdr/boot/extract_stock_system_top_partition.py
```

This emits `hardware/7020_ad936x_sdr/stock_system_top_from_BOOT.bin`, which was validated on `2026-06-21` as a working `system.bit.bin` payload for the clean boot overlay.
6. Inspect the AD936x no-OS app in `ps/ad936x_no_os_reference/` and compare its parameters with your board target.
7. Use `ps/bringup_tests/` for board sanity checks before SDR-specific debugging.
8. Use the HDL reference under `hdl/adi_fmcomms2_reference/` as the baseline when mapping course HDL work toward a Zynq/AD936x platform.
9. Use `hdl/course_bpsk_fmcomms2_zc702/` when you need the first clean course-owned modem overlay instead of the untouched vendor baseline.

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
