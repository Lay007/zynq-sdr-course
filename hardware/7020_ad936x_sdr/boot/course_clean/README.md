# Course Clean Boot Overlay

This folder defines the minimal course overlay for the external Zynq-7020 +
AD9361/AD9363 board.

## Goal

Boot the stock Pluto-like Linux image from `../sd_image/` while avoiding the
older custom `vivado_lcd` + `modem` stack.

The overlay keeps only the parts that are useful for course bring-up:

- deterministic management IP on the wired `eth0` link;
- DHCP on that management link so the host receives an address automatically;
- boot-time loading of the course-owned raw `system.bit` PL image;
- removal of stale `i2c@41600000` and `mwipcore@43c00000` PL nodes from the
  stock Linux device tree before boot;
- safe TX defaults for receive-first work when no attenuator is installed yet.

## Known-good PL baselines

On `2026-06-21`, the rebuilt Vivado `system.bit.bin` images from
`hdl/course_bpsk_fmcomms2_zc702/` still caused
`ad9361 spi0.0: Calibration TIMEOUT (0x244, 0x80)` during clean boot.

There are now two different external PL validation paths and they should not be
mixed:

- raw `.bit` plus `fpga loadb`: use
  `../ps/ad936x_no_os_reference/platform/hw/system_top.bit` when you need the
  strongest proof that U-Boot really replaced the PL shell, because U-Boot
  prints the Xilinx bitstream header fields (`design filename`, `part number`,
  `date`, `time`) before Linux starts;
- manual UART `fpga load` plus `.bit.bin`: use this when you need to validate
  the BOOT-partition-style payload path that the stock board image actually
  accepts.

The raw vendor-reference `.bit` is therefore still useful as a source-correlated
control candidate, but it is not a boot-safe radio baseline: on `2026-06-22`,
both the raw `fpga loadb` path and the manual `.bit.bin` `fpga load` path still
ended with `ad9361 spi0.0: Calibration TIMEOUT (0x244, 0x80)`.

The only externally loaded boot-safe baseline proven so far is the stock PL
partition extracted from the vendor `BOOT.bin`:

```bash
python hardware/7020_ad936x_sdr/boot/extract_stock_system_top_partition.py
```

This writes:

```text
hardware/7020_ad936x_sdr/stock_system_top_from_BOOT.bin
```

That extracted payload survives manual UART `fpga load` and returns Linux plus
all `4` expected IIO devices with a healthy AD9361.

Persistent validation summary:

```text
docs/assets/lab112_clean_boot_pl_validation.json
```

To rerun that check from the host, use:

```bash
python hardware/7020_ad936x_sdr/boot/validate_clean_boot_overlay.py
```

This validates the raw `.bit` direct-load path through `fpga loadb`.

To validate the stock BOOT-partition payload through the correct manual UART
`fpga load` path, use:

```bash
python hardware/7020_ad936x_sdr/boot/validate_manual_uart_fpga_load.py \
  --candidate hardware/7020_ad936x_sdr/stock_system_top_from_BOOT.bin
```

To validate the source-correlated vendor reference through the same manual
`.bit.bin` path, use:

```bash
python hardware/7020_ad936x_sdr/boot/validate_manual_uart_fpga_load.py \
  --candidate hardware/7020_ad936x_sdr/ps/ad936x_no_os_reference/platform/hw/system_top.bit.bin
```

## Rejected reconstructed boot shells

The two regenerated vendor candidates checked on `2026-06-21` are not
equivalent to the stock boot-time shell:

- `AD936X_PL.zip::projects/fmcomms2/zc702/.../system_top.bit` still reaches
  Linux, but `ad9361 spi0.0` fails with `Calibration TIMEOUT (0x244, 0x80)`;
- `AD936X_only_PL.zip::AD936X_only_PL.runs/impl_1/system_top.bit` is worse:
  after U-Boot `fpga load`, the board can no longer read the Linux partition
  and drops to a `Pluto>` prompt with `bad MBR sector signature 0xb23e`.
- the course-built `bridge_rx_only` candidate also now builds cleanly in Vivado
  and exports an XSA, but it still fails the same AD9361 clean-boot
  calibration check as soon as Linux probes `spi0.0`.
- the MIO14/15-patched editable vendor snapshot and the newer
  `bridge_txrx_mux` course overlay both now prove raw `system.bit` direct load
  through U-Boot `fpga loadb`, but they still fail AD9361 clean boot with the
  same calibration timeout once Linux probes `spi0.0`;
- the Bootgen-converted `bridge_txrx_mux.bit.bin` candidate is rejected even
  earlier by U-Boot `fpga load` with
  `zynq_validate_bitstream: Bitstream is not validated yet (diff 1700)`, so
  Linux then comes up on the untouched stock PL shell.

Practical consequence: the course now has one source-correlated raw proof
candidate and one externally loaded boot-safe baseline:

- the source-correlated vendor reference raw `system_top.bit` for proving that
  the external raw PL image really replaced the stock shell;
- the extracted stock `BOOT.bin` partition payload as the only externally
  loaded boot-safe baseline demonstrated so far.

The patched vendor snapshot and the course bridge candidates remain the best
structural/debug shells, but they are not yet AD9361-safe RF baselines.

## Manual recovery from a bad `system.bit` or `system.bit.bin`

If a test external PL image breaks Linux boot after `fpga loadb`, recover from
the UART console by interrupting U-Boot before `Loading course PL image
system.bit...` or `system.bit.bin...`, then manually booting the stock SD
payload:

```text
load mmc 0 0x2080000 uImage
load mmc 0 0x2000000 devicetree.dtb
load mmc 0 0x4000000 uramdisk.image.gz
run course_fixup_pl_dtb
bootm 0x2080000 0x4000000 0x2000000
```

After Linux is back, immediately restore the known-good stock PL file on the
FAT partition and rerun the validator above.

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

- `uEnv_course_bpsk_overlay.txt` - minimal U-Boot environment override that loads raw `system.bit` and strips stale PL nodes from the stock device tree before Linux boots
- `autorun.sh` - persistent post-boot override for the stock Pluto-like image, executed from `/mnt/jffs2/autorun.sh`
- `rc.user` - compatibility overlay for the older custom rootfs that executes `/cfg/rc.user`
- `../validate_manual_uart_fpga_load.py` - reproducible helper for the manual `fpga load` path used by `.bit.bin` payload experiments

## What the overlay changes

1. Loads raw `system.bit` into PL from U-Boot before Linux starts, using
   `fpga loadb` because this board's U-Boot expects a Xilinx `.bit` buffer on
   the direct PL-load path.
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

- the course-generated raw `system.bit` built from `hdl/course_bpsk_fmcomms2_zc702/`;
- or, while the rebuilt course bitstream is still being debugged, the
  source-correlated raw `system_top.bit` from
  `hardware/7020_ad936x_sdr/ps/ad936x_no_os_reference/platform/hw/system_top.bit`
  copied to the FAT root as `system.bit`;
- `hardware/7020_ad936x_sdr/boot/course_clean/uEnv_course_bpsk_overlay.txt`
  copied to the FAT root as `uEnv.txt`.

If U-Boot prints `zynq_validate_bitstream: Bitstream is not validated yet` and
then falls through to the generic `fpga` usage text while attempting to load a
`.bit.bin` payload with `fpga load`, Linux may still come up with AD9361/IIO
alive because the stock PL from `BOOT.bin` is still active. Do not treat that
as proof that the external course image actually reached the fabric.

If U-Boot prints the Xilinx header fields for `system.bit`, then `fpga loadb`
has accepted the raw bitstream buffer and the PL image really did load.

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
