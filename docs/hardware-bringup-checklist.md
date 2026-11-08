# Hardware Bring-up Checklist

This checklist turns the course hardware path into a repeatable engineering procedure.

## 1. Host workstation

| Check | Expected result |
|---|---|
| Python environment installed | tools and lab scripts can run |
| MkDocs dependencies installed | documentation builds locally |
| Icarus Verilog installed | HDL smoke tests can run |
| Git LFS policy reviewed | large captures are not committed accidentally |

## 2. SDR board preparation

| Check | Expected result |
|---|---|
| Zynq board powers up reliably | no brownout or thermal issue |
| AD936x frontend is detected (AD9361 on the ZynqSDR course boards) | RF frontend is visible to control software |
| Reference clock is documented | frequency calculations are reproducible |
| Gain defaults are known | repeatable RF experiments |

Before changing FPGA images or boot media, identify the installed firmware profile and
its board-specific recovery method. See [ADR 0004: ZynqSDR Pluto-compatible
and FPGA firmware profiles](adr/0004-zynqsdr-firmware-profiles.md) and
[validation issue #81](https://github.com/Lay007/zynq-sdr-course/issues/81).
A historical boot set is not proof of a currently bootable recovery image;
perform read-only identity checks before any image change.
Use the [firmware profile validation procedure](en/firmware-profile-validation.md)
([RU](ru/firmware-profile-validation.md)) for the offline inventory and staged bench gates.

## 3. RF safety and signal path

| Check | Expected result |
|---|---|
| Attenuation is installed when needed | receiver input is protected |
| Coax path is documented | reproducible setup geometry |
| Over-the-air tests are controlled | legal and safe operation |
| Frequency plan is written down | no accidental out-of-band transmission |

## 4. External receiver

| Check | Expected result |
|---|---|
| RTL-SDR is detected | independent observation path available |
| HDSDR or equivalent tool is configured | spectrum and waterfall are visible |
| Sample rate is recorded | IQ files can be interpreted later |
| Center frequency is recorded | replay and analysis are traceable |

## 5. IQ capture metadata

Every capture should include:

- sample rate;
- center frequency;
- RF bandwidth;
- gain settings;
- capture duration;
- file format;
- hardware setup notes.

## 6. Minimum acceptance criteria

A hardware experiment is ready for documentation when:

1. the signal is visible on the external receiver;
2. the IQ file can be replayed offline;
3. FFT and constellation plots can be generated;
4. the report includes configuration, assumptions and limitations.
