# Course Clean Boot Overlay

This folder defines the minimal course overlay for the external Zynq-7020 +
AD9361/AD9363 board.

## Goal

Boot the stock Pluto-like Linux image from `../sd_image/` while avoiding the
older custom `vivado_lcd` + `modem` stack.

The overlay keeps only the parts that are useful for course bring-up:

- deterministic management IP on the wired `eth0` link;
- DHCP on that management link so the host receives an address automatically;
- safe TX defaults for receive-first work when no attenuator is installed yet.

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

- `autorun.sh` - persistent post-boot override for the stock Pluto-like image, executed from `/mnt/jffs2/autorun.sh`
- `rc.user` - compatibility overlay for the older custom rootfs that executes `/cfg/rc.user`

## What the overlay changes

1. Forces `eth0` to `192.168.40.1/24`.
2. Restarts `udhcpd` on `eth0` and serves `192.168.40.200-220`.
3. Powers down the TX LO by default.
4. Sets TX attenuation to the minimum output level (`-89.75 dB`) on both TX channels.

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
- receive-only observation with external antennas;
- early metadata and measurement workflow validation.

It is not the final configuration for transmitted measurements. Before any TX
experiment, review `docs/rf-safety.md`, restore an intentional TX setup, and
add external attenuation for any conducted loopback.
