# FPGA Resource Report Template

Use this template to document resource, timing, and verification evidence for HDL blocks in the course.

## Block summary

| Field | Value |
|---|---|
| Block name | TBD |
| Course block / lab | TBD |
| Source module | `blocks/...` |
| Testbench | `blocks/...` |
| Target device | TBD |
| Tool version | TBD |
| Clock target | TBD MHz |
| Interface style | streaming / memory-mapped / simple parallel |
| Data format | TBD |

## Function

Describe what the block does in engineering terms.

```text
input samples -> processing -> output samples
```

## Verification evidence

| Evidence | Path / command | Status |
|---|---|---|
| Reference model | TBD | draft / pass / fail |
| Test vector source | TBD | draft / pass / fail |
| RTL simulation | TBD | draft / pass / fail |
| Latency check | TBD | draft / pass / fail |
| Numeric agreement | TBD | draft / pass / fail |

Recommended local command:

```bash
python tools/tasks.py hdl
```

## Resource utilization

| Resource | Used | Available | Utilization |
|---|---:|---:|---:|
| LUT | TBD | TBD | TBD |
| FF | TBD | TBD | TBD |
| DSP | TBD | TBD | TBD |
| BRAM | TBD | TBD | TBD |
| URAM | TBD | TBD | TBD |

## Timing summary

| Metric | Value |
|---|---:|
| Target period | TBD ns |
| Achieved WNS | TBD ns |
| Achieved TNS | TBD ns |
| Fmax estimate | TBD MHz |
| Timing status | pass / fail / not checked |

## Latency and throughput

| Property | Value |
|---|---:|
| Pipeline latency | TBD cycles |
| Initiation interval | TBD cycles |
| Samples per clock | TBD |
| Sustained sample rate | TBD samples/s |

## Numeric format

Record fixed-point assumptions:

- input width;
- output width;
- coefficient width;
- rounding rule;
- saturation or wrap rule;
- scaling convention;
- acceptable error tolerance.

## Known limitations

- TBD

## Engineering decision

Choose one:

- **Draft** - block exists but is not fully verified.
- **Simulation-ready** - testbench passes deterministic checks.
- **Synthesis-ready** - resource and timing data are recorded.
- **Hardware-ready** - measured behavior is linked to a report.

## Next steps

1. TBD
2. TBD
3. TBD
