# Course Clean Boot Overlay

This folder defines the minimal course overlay for the external Zynq-7020 +
AD9361/AD9363 board.

## Goal

Boot the stock Pluto-like Linux image from `../sd_image/` while avoiding the
older custom `vivado_lcd` + `modem` stack.

The overlay keeps only the parts that are useful for course bring-up:

- deterministic management IP on the wired `eth0` link;
- DHCP on that management link so the host receives an address automatically;
- boot-time loading of the course-owned `system.bit.bin` PL image;
- removal of stale `i2c@41600000` and `mwipcore@43c00000` PL nodes from the
  stock Linux device tree before boot;
- safe TX defaults for receive-first work when no attenuator is installed yet.

## Known-good PL baseline

On `2026-06-21`, the rebuilt Vivado `system.bit.bin` images from
`hdl/course_bpsk_fmcomms2_zc702/` still caused
`ad9361 spi0.0: Calibration TIMEOUT (0x244, 0x80)` during clean boot.

The validated fallback is the stock PL partition extracted from the vendor
`BOOT.bin`:

```bash
python hardware/7020_ad936x_sdr/boot/extract_stock_system_top_partition.py
```

This writes:

```text
hardware/7020_ad936x_sdr/stock_system_top_from_BOOT.bin
```

That extracted blob was verified as a working replacement for FAT-root
`system.bit.bin` under this clean boot overlay.

## Expected boot files

Use the stock root boot set from:

```text
hardware/7020_ad936x_sdr/boot/sd_image/
```

Expected files on the FAT partition root:

- `BOOT.bin`
- `uImage`
- `devicetree.dtb`
- `uramdisk.image.gz`
- `uEnv.txt`

## Overlay files

- `uEnv_course_bpsk_overlay.txt` - minimal U-Boot environment override that loads `system.bit.bin` and strips stale PL nodes from the stock device tree before Linux boots
- `autorun.sh` - persistent post-boot override for the stock Pluto-like image, executed from `/mnt/jffs2/autorun.sh`
- `rc.user` - compatibility overlay for the older custom rootfs that executes `/cfg/rc.user`

## What the overlay changes

1. Loads `system.bit.bin` into PL from U-Boot before Linux starts.
2. Removes stale `/fpga-axi/i2c@41600000` and `/fpga-axi/mwipcore@43c00000`
   nodes from the stock Linux device tree so the course PL shell matches the
   kernel probe contract.
3. Forces `eth0` to `192.168.40.1/24`.
4. Restarts `udhcpd` on `eth0` and serves `192.168.40.200-220`.
5. Powers down the TX LO by default.
6. Sets TX attenuation to the minimum output level (`-89.75 dB`) on both TX channels.

## Recommended FAT boot-partition contents for the course BPSK overlay

Copy the stock files from:

```text
hardware/7020_ad936x_sdr/boot/sd_image/
```

Then add:

- the course-generated `system.bit.bin` built from `hdl/course_bpsk_fmcomms2_zc702/`;
- or, while the rebuilt course bitstream is still being debugged, the known-good
  `hardware/7020_ad936x_sdr/stock_system_top_from_BOOT.bin` copied to the FAT
  root as `system.bit.bin`;
- `hardware/7020_ad936x_sdr/boot/course_clean/uEnv_course_bpsk_overlay.txt`
  copied to the FAT root as `uEnv.txt`.

## Recommended persistence path

For the stock Pluto-like image used by the course-clean profile, copy:

```text
hardware/7020_ad936x_sdr/boot/course_clean/autorun.sh
```

to:

```text
/mnt/jffs2/autorun.sh
```

This is the hook executed by `/etc/init.d/S98autostart` during boot.

This is intentionally conservative. It is suitable for:

- serial console bring-up;
- host-side `SSH`/`IIO` checks;
- clean-boot validation of the course BPSK overlay against the stock Linux image;
- receive-only observation with external antennas;
- early metadata and measurement workflow validation.

It is not the final configuration for transmitted measurements. Before any TX
experiment, review `docs/rf-safety.md`, restore an intentional TX setup, and
add external attenuation for any conducted loopback.
