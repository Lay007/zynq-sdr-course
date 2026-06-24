# 06. IQ recording metadata

## Why this is critical

An IQ file without metadata is nearly useless: without `Fs` and `Fc` it is
impossible to interpret the frequency axis correctly.

## Minimum required fields

| Parameter | Meaning |
|---|---|
| `Fs` | sample rate |
| `Fc` | center (LO) frequency |
| `format` | sample data type (`int16`, `float32`, `uint8`, …) |
| `IQ order` | which channel comes first in the interleaved stream |
| `gain` | receiver gain setting |
| `duration` | recording duration |

## Common mistakes

| Mistake | Symptom |
|---|---|
| Wrong `Fs` | incorrect frequency scale |
| Missing `Fc` | cannot map to RF frequency |
| Wrong format | distorted waveform |
| Missing gain | impossible to assess signal level |

## Checklist

Before analyzing any IQ file, always record:

- `Fs`
- `Fc`
- sample format
- I/Q interleaving order
- signal source description
- gain settings

## Example metadata JSON

```json
{
  "sample_rate_hz": 2400000,
  "center_frequency_hz": 915000000,
  "iq_format": "ci16",
  "endianness": "little",
  "i_first": true,
  "sample_count": 1048576,
  "gain_settings": {
    "rx_hardwaregain_db": 35,
    "gain_control_mode": "manual"
  }
}
```
