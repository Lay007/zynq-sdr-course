# Real Data Policy

Large IQ recordings are essential for SDR experiments, but they should not be committed directly to this repository by default.

## Why raw IQ files should stay outside Git

| Problem | Why it matters |
|---|---|
| Repository bloat | CI and clone times become slow |
| Binary diffs | Git cannot efficiently review raw signal changes |
| Reproducibility risk | files without metadata are ambiguous |
| Licensing/privacy | captures may contain restricted or sensitive signals |
| Storage limits | long captures can easily reach gigabytes |

## Recommended storage options

| Option | Best use |
|---|---|
| GitHub Releases | small curated demo datasets |
| Git LFS | small-to-medium binary fixtures, used carefully |
| Zenodo | citable research datasets with DOI |
| institutional storage | internal/private experimental data |
| cloud storage link | temporary collaboration datasets |

## Practical recommendation for this repository

Use this split by default:

| What | Recommended location |
|---|---|
| raw real IQ recordings | outside Git, in private/local storage |
| manifest, checksum, README | inside `datasets/<dataset_id>/` |
| report-ready plots and metrics JSON | inside `docs/assets/` |
| tiny synthetic fixtures for tests | inside the repository |

For personal bring-up or lab work, keep the raw file in the SDR tool's recording folder or in a dedicated external directory, then commit only:

- the manifest;
- SHA256;
- preview plots;
- metrics JSON;
- a short README with replay/analysis commands.

Use `Git LFS` only when the recording is small enough to justify versioning and is safe enough to share as a technical course artifact.

## Approved exception: Lab 1.0 RTL-SDR captures

`datasets/lab1_0_rtl_sdr_observation/` is an explicit exception to the default "raw real IQ outside Git" rule.

It contains two short passive RTL-SDR air captures recorded during the first SDR++ bring-up session:

| Dataset | Storage | Purpose |
|---|---|---|
| `lab1_0_rtl_sdr_fm_103119454` | Git LFS WAV IQ | First FM-band observation artifact for Lab 1.0 |
| `lab1_0_rtl_sdr_narrowband_220860000` | Git LFS WAV IQ | First narrowband observation artifact for Lab 1.0 and Block 9 replay work |

This exception is acceptable because the captures are short, have sidecar manifests, include SHA256 checksums, and are used as early-course evidence that the repository contains real RF observations, not only synthetic examples.

The exception does **not** mean that arbitrary off-air recordings may be added to Git LFS. Every future real capture still needs:

- a manifest with sample rate, center frequency, format, duration and hardware notes;
- a checksum;
- a clear `publication_status` field;
- a license/access note;
- a statement that decoded content is not published;
- a review of legal and redistribution status before public release.

## Required sidecar metadata

Every real capture must have a metadata file or manifest next to it:

```text
capture_name.ci16
capture_name.metadata.json
```

or:

```text
manifest_<capture_name>.yaml
```

The metadata must include:

- sample rate;
- center frequency;
- IQ format;
- endian and I/Q order;
- sample count or duration;
- receiver and gain settings;
- expected signal offset;
- capture date/time when available;
- hardware setup;
- safety/attenuation notes;
- license or access notes;
- publication status for real-air captures.

## File naming convention

Use descriptive names:

```text
YYYYMMDD_device_band_signal_samplerate_format.ci16
```

Example:

```text
20260511_ad9363_915mhz_qpsk_2p4msps_ci16.ci16
20260511_ad9363_915mhz_qpsk_2p4msps_ci16.metadata.json
```

For SDR++ WAV IQ captures, keep the original tool-generated filename when it helps traceability, but store the capture parameters in the manifest.

## What can be committed

Commit these files:

- metadata templates;
- small synthetic fixtures;
- analysis scripts;
- plots and metrics JSON;
- links to external datasets;
- README files describing how to obtain data;
- short Git LFS captures only after manifest and publication review.

Do not commit:

- multi-MB or multi-GB raw captures without a reasoned exception;
- undocumented IQ dumps;
- captures with unclear legal status;
- files containing sensitive or private communications;
- decoded content from services that should not be republished.

## Minimal dataset README

Every external or LFS-backed dataset folder should include:

```text
README.md
metadata.json or manifest_*.yaml
download_instructions.md when data is external
checksum.txt or manifest sha256
```

## Reproducibility checklist

- [ ] External link or Git LFS storage is documented.
- [ ] Metadata JSON or YAML manifest is included.
- [ ] SHA256 checksum is included when data is fixed.
- [ ] Capture format is described.
- [ ] Analysis command is provided.
- [ ] License/access conditions are stated.
- [ ] Real-air publication status is stated.
- [ ] The dataset is not required for basic CI unless it is tiny or LFS-safe.
- [ ] `python tools/check_dataset_manifests.py` passes for committed manifests.
