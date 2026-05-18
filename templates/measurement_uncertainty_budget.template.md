# Measurement Uncertainty Budget Template

## Measurement context

- Metric:
- Nominal value:
- Unit:
- Test setup:
- Date/time:

## Type A contribution (repeatability)

- Number of repeats:
- Sample values:
- Standard deviation:
- Standard uncertainty `u_A = s/sqrt(N)`:

## Type B contributions

| Source | Distribution | Input value | Divisor | Standard contribution |
|---|---|---:|---:|---:|
| Instrument accuracy | rectangular/normal |  |  |  |
| Reference clock | rectangular/normal |  |  |  |
| Cable/connector effects | rectangular/normal |  |  |  |
| Temperature drift | rectangular/normal |  |  |  |
| Other | rectangular/normal |  |  |  |

## Combined and expanded uncertainty

```text
u_c = sqrt(sum(u_i^2))
U = k * u_c
```

- Coverage factor `k`:
- Combined standard uncertainty `u_c`:
- Expanded uncertainty `U`:

## Reported result

```text
metric = nominal +/- U (k=__)
```

- Lower interval:
- Upper interval:

## Engineering interpretation

- Does the uncertainty interval satisfy acceptance criteria?
- Dominant uncertainty source:
- Recommended next experiment to reduce uncertainty:

