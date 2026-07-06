# Final Project Example Report

This is a compact example structure for a portfolio-ready final SDR project report.

## Project title

QPSK SDR link: model, implementation notes, IQ replay and metrics.

## 1. Objective

Build and validate a QPSK signal-processing chain using a documented model, implementation assumptions and measurable output metrics.

## 2. System architecture

```text
bits -> mapper -> pulse shaping -> channel/replay -> synchronization -> demapper -> metrics
```

For hardware-backed work, extend the chain:

```text
model -> Zynq/AD9363 -> RF path -> receiver -> IQ capture -> offline analysis
```

## 3. Parameters

| Parameter | Value |
|---|---:|
| Sample rate | TBD |
| Symbol rate | TBD |
| Modulation | QPSK |
| Filter | RRC / TBD |
| Roll-off | TBD |
| Capture format | CI16 / CF32 / TBD |

## 4. Evidence package

| Evidence | Path |
|---|---|
| Reference model | TBD |
| Dataset manifest | `datasets/demo_qpsk_capture/manifest.yaml` |
| FPGA resource report | `reports/fpga/` |
| Measurement report | TBD |
| Final figures | `docs/assets/` |

## 5. Metrics

| Metric | Target | Measured | Status |
|---|---:|---:|---|
| SNR | TBD | TBD | TBD |
| EVM | TBD | TBD | TBD |
| BER | TBD | TBD | TBD |
| Frequency error | TBD | TBD | TBD |

## 6. Limitations

- Replace synthetic replay with hardware capture.
- Correlate the routed timing/resource result with repeatable board operation.
- Add uncertainty notes for measured RF results.

## 7. Conclusion

The project is complete when the report links model assumptions, implementation constraints, measured or replayed data, metric results and a reproducible command path.

See [Dual-modem Zynq SDR final implementation report](final-project-dual-modem-implementation-report.md) for the filled current example and its explicitly open hardware gates.
