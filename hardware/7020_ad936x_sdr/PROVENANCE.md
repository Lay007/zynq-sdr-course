# Provenance

Imported on `2026-06-17` from the local vendor bundle:

```text
D:\7020\7020_AD936X_SDR
```

This is a curated local import, not a claim that the imported tree is the canonical upstream source.

## Imported subsets

| Original location | Imported destination | Notes |
|---|---|---|
| `Descriptions/7020_936x_SDR.pdf` | `docs/7020_936x_SDR.pdf` | board description PDF |
| `Fish_Ball_SDR_ru.pdf` | `docs/Fish_Ball_SDR_ru.pdf` | Russian board guide |
| `Pluto/SD_image/*` | `boot/sd_image/` | extracted SD boot payload |
| `Pluto/pluto-fw-v0.38*/ReadMe.txt` | `boot/notes/pluto_sd_boot_readme.txt` | SD boot note from the Ethernet+USB firmware folder |
| `Pluto/ZC706-FMCOMMS2-3(Ethernet)/Readme_1.txt` | `boot/notes/ethernet_sd_partition_readme.txt` | FAT + EXT partition note |
| `Pluto/ZC706-FMCOMMS2-3(Ethernet)/Readme_2.txt` | `boot/notes/ethernet_imageusb_readme.txt` | raw image write note |
| `Pluto/ZC706-FMCOMMS2-3(Ethernet)/pic/*` | `boot/notes/pic/` | small screenshots |
| `Vivado2021.1/Driver_PL_PS/AD936X_PL.zip` | `hdl/adi_fmcomms2_reference/` | curated subset: HDL library, common project scripts, FMCOMMS2 project scaffolding, regmap docs |
| `Vivado2021.1/Test_interface/Test_PL.zip` | `hdl/test_pl_reference/` | minimal test PL block design |
| `Vivado2021.1/Driver_PL_PS/AD936X_PS.zip` | `ps/ad936x_no_os_reference/` | curated subset: no-OS app sources, platform handoff, FSBL and reference bit/xsa |
| `Vivado2021.1/Test_interface/Test_PS.zip` | `ps/bringup_tests/` | curated subset: DDR/eMMC/Ethernet/LED/USB test apps and exported hardware handoff |

## Intentionally excluded

| Excluded material | Reason |
|---|---|
| `Drivers/*` | host-side installers and bundled tools are not a stable repo baseline |
| `Drivers/SecureCRT5.5/*` | contains activation-related files and is not suitable for import |
| `Pluto/ZC706-FMCOMMS2-3(Ethernet)/xk_ZYNQ7020_AD9361.img` | very large raw image; extracted SD payload is already present |
| duplicate firmware zip packages | extracted or smaller equivalents were preferred |
| `3D/*`, `SDR_3D_STEP/*` | useful for mechanics, but not required for boot/PS/HDL bring-up |

## Practical interpretation

Treat this directory as:

- a local board bootstrap package;
- a source of reference HDL/PS files to compare against the course materials;
- a bring-up aid before creating cleaner course-specific hardware flows.

Do not treat it as:

- a clean upstream mirror;
- a complete vendor release;
- a substitute for explicit course-facing board documentation that should eventually live under `docs/`.
