# Lab 1.0 Example Report — First RTL-SDR Air Observation

## Goal

The goal of this report is to document the first practical SDR observation step: connect an RTL-SDR receiver, verify that the software chain works, record short IQ fragments, and preserve enough metadata for later replay and analysis.

This is not a communications-intelligence exercise. The report treats the captures only as technical RF observations: spectrum shape, sample rate, center frequency, IQ format and reproducibility metadata.

## Setup

| Item | Value |
|---|---|
| Receiver | RTL-SDR V3 Pro |
| Software | SDR++ |
| RF path | Passive over-the-air receive only |
| Sample rate | 2.4 MS/s |
| Recording format | WAV IQ, little-endian, I-first |
| Dataset folder | `datasets/lab1_0_rtl_sdr_observation/` |
| Analysis script | `blocks/block_09_recording_and_analysis_tools/python/lab_9_4_read_wav_iq_and_analyze.py` |

## Captures

| Capture | Center frequency | Duration | Manifest |
|---|---:|---:|---|
| FM-band observation | 103.119454 MHz | 5.422 s | `datasets/lab1_0_rtl_sdr_observation/manifest_fm_103119454.yaml` |
| Narrowband observation | 220.860000 MHz | 5.309 s | `datasets/lab1_0_rtl_sdr_observation/manifest_narrowband_220860000.yaml` |

Both raw files are stored through Git LFS. The manifests keep the SHA256 checksums, capture settings, and replay commands.

## Reproduction commands

Run from the repository root:

```bash
python blocks/block_09_recording_and_analysis_tools/python/lab_9_4_read_wav_iq_and_analyze.py \
  --manifest datasets/lab1_0_rtl_sdr_observation/manifest_fm_103119454.yaml

python blocks/block_09_recording_and_analysis_tools/python/lab_9_4_read_wav_iq_and_analyze.py \
  --manifest datasets/lab1_0_rtl_sdr_observation/manifest_narrowband_220860000.yaml
```

Optional manifest consistency check:

```bash
python tools/check_dataset_manifests.py
```

## Expected learning result

After this lab, a learner should be able to explain:

1. why an SDR recording is meaningless without center frequency, sample rate and IQ format;
2. how a spectrum/waterfall view relates to FFT-based signal analysis;
3. why gain and overload matter before any DSP algorithm is applied;
4. how a real IQ file becomes an input artifact for Python, MATLAB, C++, GNU Radio or later FPGA-facing verification;
5. why real-air datasets need publication and redistribution review before being treated as public course data.

## Engineering interpretation

The FM-band capture is a safe first observation because it produces a strong, easily visible signal in a familiar part of the spectrum. It is useful for teaching bandwidth, waterfall interpretation and the relationship between RF center frequency and complex baseband.

The narrowband capture is useful because it shows a different spectral shape. The course should treat it only as a technical observation unless its legal/publication status is reviewed. The manifest therefore marks the dataset as `publication_status: review-required` and does not publish decoded content.

## Limitations

- The receiver gain value was not fully captured in the current metadata.
- Clipping, overload and DC offset are marked as unknown or not fully checked.
- The narrowband signal type is intentionally not identified.
- The report does not claim demodulation or message interpretation.

## Next steps

- Add generated spectrum preview figures and metrics JSON to `docs/assets/`.
- Fill in gain and overload fields when the setup is repeated.
- Add a small synthetic QPSK dataset for CI-safe replay and constellation analysis.
- Keep the real-air captures as teaching evidence, not as unrestricted public RF content.
