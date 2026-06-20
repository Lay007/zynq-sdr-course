# RF loopback safety checklist

Use this checklist before any cabled SDR experiment where one device output is connected to another device input.

The checklist is intentionally conservative. It protects equipment, keeps measurements reproducible and makes the experiment reviewable.

## Experiment identity

| Field | Value |
|---|---|
| Date / operator |  |
| Board / device A |  |
| Board / device B |  |
| Experiment name |  |
| Course block / lab |  |
| Manifest path |  |

## Connection plan

```text
source output -> attenuator(s) -> cable -> receiver input
```

Record the actual chain:

| Item | Value |
|---|---|
| Source connector |  |
| Receiver connector |  |
| Cable type / length |  |
| Attenuator value |  |
| Extra DC block present? | yes / no / not required |
| Observation receiver present? | yes / no |

## Pre-power checks

- [ ] The expected signal level at the receiver input is estimated.
- [ ] An attenuator is installed before enabling the source path.
- [ ] Source gain starts from the lowest practical value.
- [ ] Receiver gain starts from a conservative value.
- [ ] Sample rate and bandwidth are written down before capture.
- [ ] DC presence on the RF path is understood or blocked.
- [ ] The setup can be disconnected quickly if the observed level is wrong.

## First capture checks

- [ ] Capture duration is short.
- [ ] Time-domain waveform is inspected before increasing gain.
- [ ] Spectrum is inspected for clipping, unexpected tones or strong DC component.
- [ ] The useful signal is not hidden by the center artifact.
- [ ] Metadata is saved next to the capture.
- [ ] Any warning from the driver, IIO tool or host script is copied into the report.

## Metadata fields

Minimum fields for the manifest:

```yaml
sample_rate_hz:
center_frequency_hz:
rf_bandwidth_hz:
source_gain_db:
receiver_gain_db:
attenuation_db:
capture_format:
capture_command:
analysis_command:
notes:
```

## Stop conditions

Stop the experiment and return to safe settings if:

- the receiver spectrum is clipped;
- the time-domain waveform is saturated;
- the observed signal level is much higher than expected;
- the driver reports repeated buffer problems;
- the board, cable or attenuator becomes warm unexpectedly;
- the result cannot be explained from the recorded settings.

## Report snippet

Use this short conclusion format:

```text
The conducted loopback was configured with <attenuation> dB attenuation,
<sample_rate> sample rate and <bandwidth> RF bandwidth. The first capture
showed <main observation>. No/yes clipping was observed. The main limitation
is <limitation>. The next action is <next measurement or setting change>.
```
