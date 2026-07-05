# AD9363 Gain / Overload Measurement Log

Use this template for hardware task #29. Do not fill it with guessed values. Every promoted row must come from a real board session.

## Session metadata

| Field | Value |
|---|---|
| Date | TBD |
| Operator | TBD |
| Board | Zynq-7020 + AD936x-compatible SDR |
| RF frontend | AD9363 / compatible |
| Software image | TBD |
| libiio / driver version | TBD |
| Reference receiver | RTL-SDR / spectrum analyzer / other |
| RF path | cabled / attenuated / OTA |
| Attenuation | TBD |
| Center frequency | TBD |
| Sample rate | TBD |
| RF bandwidth | TBD |
| Notes | TBD |

## Safety pre-check

- [ ] TX power path is understood.
- [ ] External attenuation is inserted for cabled tests.
- [ ] Receiver gain starts from conservative values.
- [ ] No unknown direct high-power path is connected to RTL-SDR or AD9363 input.
- [ ] Local regulations and lab RF rules are respected.

## Measurement table

| Test ID | RX/TX path | TX gain / attenuation setting | RX gain setting | External attenuation | Observed peak | SNR / EVM / BER | Clipping / overload sign | Recommended? | Notes |
|---|---|---:|---:|---:|---:|---|---|---|---|
| GAIN-001 | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| GAIN-002 | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| GAIN-003 | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

## Required plots or screenshots

Attach or link:

- spectrum before overload;
- spectrum near overload;
- time-domain or IQ amplitude view if clipping is suspected;
- constellation and EVM/BER plot when a digital waveform is used;
- gain setting screenshot or command log.

## Acceptance rule

A row is accepted only when it includes:

1. exact RF path;
2. gain settings;
3. attenuation assumptions;
4. observed clipping or overload status;
5. at least one quality metric or diagnostic plot;
6. short conclusion about safe starting values.

## Conclusion

```text
TBD: summarize safe starting gain, overload warning signs, and what should be avoided in student labs.
```
