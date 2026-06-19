# Lab 1.0 RTL-SDR Observation Recordings

This folder documents two short WAV IQ captures recorded during the first RTL-SDR bring-up session in `SDR++`.

The raw files are stored in this dataset package through `Git LFS`, while the manifests keep the checksums, capture settings and analysis commands.

## Files

| File | Role |
|---|---|
| `manifest_fm_103119454.yaml` | Short FM-band observation capture |
| `manifest_narrowband_220860000.yaml` | Short narrowband capture near 220.86 MHz |
| `raw/*.wav` | Curated short WAV IQ recordings stored through Git LFS |

## Offline analysis

Run from the repository root:

```bash
python blocks/block_09_recording_and_analysis_tools/python/lab_9_4_read_wav_iq_and_analyze.py \
  --manifest datasets/lab1_0_rtl_sdr_observation/manifest_fm_103119454.yaml

python blocks/block_09_recording_and_analysis_tools/python/lab_9_4_read_wav_iq_and_analyze.py \
  --manifest datasets/lab1_0_rtl_sdr_observation/manifest_narrowband_220860000.yaml
```

The script resolves the WAV file from the dataset manifest, then writes spectrum, time preview and metrics JSON to `docs/assets/`.

## Notes

- The original source files still remain in the local `SDR++ recordings` folder on this workstation.
- Each manifest includes SHA256, duration, center frequency, sample rate and access notes.
- These captures are intended as first-course artifacts for `Lab 1.0` and future Block 9 metadata exercises.
- Review the legal/publication status of each real capture before pushing to a public remote.
