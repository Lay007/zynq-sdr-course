# Hardware checklist

This page is the short top-level hardware go/no-go guide for the course.

Use it as the single entry point before any board-level, RF, RTL-SDR, or IQ-capture lab. The detailed procedures remain in the linked pages; this checklist tells you what to open next and what evidence must exist before the lab is considered reproducible.

## 1. Pre-lab route

| Stage | Main question | Open this page |
|---|---|---|
| Host readiness | Can the local workstation run docs, labs and HDL smoke checks? | [Hardware bring-up checklist](hardware-bringup-checklist.md) |
| RF safety | Is the TX/RX path safe and attenuation assumptions documented? | [RF safety guide](rf-safety.md) |
| Measurement discipline | Are uncertainty, gain and capture assumptions recorded? | [Measurement uncertainty guide](measurement-uncertainty-guide.md) |
| IQ metadata | Can the capture be replayed and interpreted later? | [IQ recording metadata guide](iq-recording-metadata.md) |
| Final reporting | Is there a standard structure for conclusions and evidence? | [SDR measurement report template](sdr-measurement-report-template.md) |

## 2. Minimum go/no-go before touching hardware

Do not start the experiment until these conditions are true:

1. The frequency plan is written down.
2. The TX gain or expected signal level is documented.
3. The RX path and attenuation chain are explicitly described.
4. The receiver input protection assumption is clear.
5. The sample rate, bandwidth and center frequency are recorded.
6. The expected output artifact is known in advance: FFT, constellation, BER/EVM, or measurement report.

## 3. Minimal reproducible hardware pack

For a hardware-backed lab, the repository or report should contain:

- setup description;
- board and receiver configuration;
- IQ metadata;
- one generated figure or report;
- one short engineering conclusion.

If any of these are missing, the lab may still be educational, but it is not yet portfolio-ready.

## 4. Fast role-based entry points

| Role | What to open first |
|---|---|
| Student | [Student path](student-path.md) |
| Reviewer | [Reviewer path](reviewer-path.md) |
| Instructor | [Instructor guide](instructor-guide.md) |

## 5. Recommended sequence for first real RF lab

1. Review [RF safety guide](rf-safety.md).
2. Check the board and receiver setup in [Hardware bring-up checklist](hardware-bringup-checklist.md).
3. Prepare capture fields from [IQ recording metadata guide](iq-recording-metadata.md).
4. Run the experiment and save one reproducible artifact.
5. Write the result using [SDR measurement report template](sdr-measurement-report-template.md).
