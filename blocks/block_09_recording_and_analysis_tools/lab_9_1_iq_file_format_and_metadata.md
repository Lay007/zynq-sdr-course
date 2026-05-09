# Lab 9.1 — IQ File Format and Metadata

## Goal

Define a reproducible IQ recording package: a binary IQ file plus a metadata JSON file that fully describes how to read and interpret the capture.

## Engineering question

> What information must be stored next to an IQ file so that another engineer can reproduce the analysis?

## Minimal recording package

```text
capture_name.ci16
capture_name.metadata.json
```

## Required metadata fields

| Field | Example | Meaning |
|---|---:|---|
| `sample_rate_hz` | 2400000 | IQ sample rate |
| `center_frequency_hz` | 915000000 | receiver RF center frequency |
| `iq_format` | `ci16` | binary sample format |
| `endianness` | `little` | byte order |
| `i_first` | `true` | interleaving order |
| `sample_count` | 1048576 | number of complex samples |
| `expected_signal_offset_hz` | 100000 | expected baseband signal location |
| `gain_settings` | object | receiver gain configuration |

## Format examples

### CI16

```text
I0 int16, Q0 int16, I1 int16, Q1 int16, ...
```

Convert to normalized float:

```text
I_float = I_int16 / 32768
Q_float = Q_int16 / 32768
```

### CU8

```text
I0 uint8, Q0 uint8, I1 uint8, Q1 uint8, ...
```

Convert to normalized float:

```text
I_float = (I_uint8 - 127.5) / 127.5
Q_float = (Q_uint8 - 127.5) / 127.5
```

### CF32

```text
I0 float32, Q0 float32, I1 float32, Q1 float32, ...
```

Usually no additional scaling is required, but amplitude convention must still be documented.

## Metadata checklist

- [ ] Recording ID is unique.
- [ ] Sample rate is known.
- [ ] Center frequency is known.
- [ ] IQ format is specified.
- [ ] I/Q order is specified.
- [ ] Endianness is specified.
- [ ] Gain settings are recorded.
- [ ] Expected signal offset is recorded.
- [ ] File size matches expected sample count.

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| wrong sample rate | FFT peak appears at wrong frequency | read metadata, not memory |
| I/Q swapped | spectrum mirrored or rotated | specify `i_first` |
| wrong endian | noise-like broken waveform | specify byte order |
| missing gain | level cannot be reproduced | save gain settings |
| no expected offset | cannot validate frequency plan | add expected signal offset |

## Report checklist

- [ ] Attach metadata JSON.
- [ ] State IQ binary format.
- [ ] Explain scaling to normalized complex samples.
- [ ] Check file size.
- [ ] State expected signal offset.
- [ ] Explain whether the recording is reproducible.

## Engineering conclusion template

```text
The IQ recording uses format ____ with sample rate ____ MS/s and center frequency ____ MHz.
The expected signal offset is ____ kHz. The metadata contains / does not contain enough
information to reproduce the analysis because ______.
```
