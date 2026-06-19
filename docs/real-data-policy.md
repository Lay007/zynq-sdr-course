# Real Data Policy

Large IQ recordings are essential for SDR experiments, but they should not be committed directly to this repository.

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

Use `Git LFS` only when the recording is small enough to justify versioning and is legally safe to share.

## Required sidecar metadata

Every real capture must have a metadata file next to it:

```text
capture_name.ci16
capture_name.metadata.json
```

The metadata must include:

- sample rate;
- center frequency;
- IQ format;
- endian and I/Q order;
- sample count;
- receiver and gain settings;
- expected signal offset;
- capture date/time;
- hardware setup;
- safety/attenuation notes;
- license or access notes.

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

## What can be committed

Commit these files:

- metadata templates;
- small synthetic fixtures;
- analysis scripts;
- plots and metrics JSON;
- links to external datasets;
- README files describing how to obtain data.

Do not commit:

- multi-MB or multi-GB raw captures;
- undocumented IQ dumps;
- captures with unclear legal status;
- files containing sensitive or private communications.

## Minimal dataset README

Every external dataset folder should include:

```text
README.md
metadata.json
download_instructions.md
checksum.txt
```

## Reproducibility checklist

- [ ] External link is documented.
- [ ] Metadata JSON is included.
- [ ] SHA256 checksum is included.
- [ ] Capture format is described.
- [ ] Analysis command is provided.
- [ ] License/access conditions are stated.
- [ ] The dataset is not required for basic CI.
