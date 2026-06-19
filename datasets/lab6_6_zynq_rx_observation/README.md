# Lab 6.6 Zynq RX-only Observation

This folder stores the first short receive-only `CI16` IQ capture recorded from
the clean stock Pluto-like image on the `Zynq-7020 + AD9361` board.

The raw file is stored through `Git LFS`, while the manifest keeps the checksum,
capture parameters and replay command.

## Files

| File | Role |
|---|---|
| `manifest_fm_103119454.yaml` | Curated FM-band receive-only manifest |
| `raw/*.ci16` | Short interleaved signed-int16 I/Q recording stored through Git LFS |

## Offline analysis

Run from the repository root:

```bash
python blocks/block_09_recording_and_analysis_tools/python/lab_9_2_read_ci16_iq_and_analyze.py \
  --manifest datasets/lab6_6_zynq_rx_observation/manifest_fm_103119454.yaml
```

For the cross-receiver overlay:

```bash
python blocks/block_06_rf_frontend_and_ad9363/python/lab_6_6_compare_receivers.py \
  --zynq-manifest datasets/lab6_6_zynq_rx_observation/manifest_fm_103119454.yaml \
  --rtl-manifest datasets/lab1_0_rtl_sdr_observation/manifest_fm_103119454.yaml
```

## Notes

- This is a receive-only artifact. No TX path was used for this dataset.
- The capture is intended as the first clean-image hardware evidence for Block 6.
- Review the legal/publication status of the real RF capture before pushing to a public remote.
