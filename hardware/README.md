# Hardware Bundles

This directory stores curated board-level starting points that are useful in the local engineering workspace but are not part of the MkDocs course site by default.

## Available bundles

| Bundle | Purpose | Main contents |
|---|---|---|
| [`7020_ad936x_sdr`](7020_ad936x_sdr/README.md) | Starting point for the external Zynq-7020 + AD936x SDR board materials | board PDFs, SD boot files, ADI-based HDL reference, AD936x no-OS PS app, PS bring-up tests |

## Curation rules

- keep source, boot and board-level reference materials that help bring the platform up;
- keep small known-good reference outputs such as `BOOT.bin`, `system_top.bit`, `system_top.xsa` or `fsbl.elf` when they shorten first bring-up;
- avoid duplicating large raw images when lighter extracted equivalents are already present;
- do not import host-tool installers, bundled SDR desktop apps, or suspicious activation/crack packages.
