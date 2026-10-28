# Hardware

This page is a navigation and readiness checklist. Board wiring, experiment procedures and measured limits belong to the linked course documents.

## Equipment used in the course

| Component | Role | Where to read more |
| --- | --- | --- |
| Zynq-7020-class board | Processing system (PS), programmable logic (PL), streaming data and control | [PS/PL architecture](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/zynq-ps-pl-architecture.md) |
| AD9361 / AD9363-class RF frontend | Conversion, mixing, filtering, gains and local oscillators | [Hardware bring-up checklist](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/hardware-bringup-checklist.md) |
| RTL-SDR | Independent receive-only observation of transmitted waveforms | [Hardware evidence index](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/hardware-evidence-index.md) |
| Attenuators, suitable cables and optional instruments | Protected conducted paths, level checks and repeatability | [RF safety guide](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/rf-safety.md) |

The repository also includes a [curated local board starting point](https://github.com/Lay007/zynq-sdr-course/blob/main/hardware/7020_ad936x_sdr/README.md). **Do not assume that a bitstream, clock setting or RF port mapping from one board revision is valid for another.**

## Safe bring-up order

1. **Host:** confirm Python, Git LFS and the simulation tools required by your lab.
2. **Board:** verify stable boot, the expected software image, device enumeration and documented reference clocks.
3. **Control:** verify a PS/PL or peripheral-control operation before enabling an RF waveform.
4. **RF path:** document TX/RX ports, attenuation, expected levels and receiver input ratings.
5. **Observation:** begin with a controlled low-level signal; use an independent receiver where possible.
6. **Evidence:** capture IQ with metadata, then calculate plots and metrics offline.

A useful early Zynq exercise is the [PS/PL mailbox and bring-up procedure](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/zynq-ps-pl-mailbox-vivado-bringup.md).

## RF protection is not optional

**Do not connect a transmitter directly to an SDR receiver without checking the expected level, attenuation and receiver maximum input rating.** Use conducted, attenuated paths where possible, or legal low-power setups. If the input level is unknown, do not transmit into that receiver.

A measured absence of digital clipping does not establish the absence of analog front-end compression. Record gain settings and note whether AGC was enabled.

See [RF safety](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/rf-safety.md) and [Measurement uncertainty](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/measurement-uncertainty-guide.md).

## Minimum hardware experiment record

```text
Board and firmware/bitstream versions:
TX/RX ports and RF path:
Center frequency / sample rate / RF bandwidth:
Gain and attenuation settings:
IQ format, sample count and metadata:
Expected result and observed result:
Evidence path and known limitations:
```

Use the [IQ metadata guide](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/iq-recording-metadata.md) and the [Hardware evidence index](https://github.com/Lay007/zynq-sdr-course/blob/main/docs/hardware-evidence-index.md) to compare your output against measured or explicitly synthetic results.

[Getting Started](Getting-Started) · [Troubleshooting](Troubleshooting)
