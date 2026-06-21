# Lab 11.9 - AD9361 RF discovery sweep for the gpreg BPSK overlay

## Goal

Prepare the reproducible RF search procedure that should be rerun once the sample-domain burst path is restored around the validated stock boot shell.

## Engineering question

> If the control plane is already alive, which small set of RF and timing parameters should be swept first to recover the first burst bits?

## Current gate

Do not interpret all-zero `RECEIVED_BITS` from the current checked-in `gpreg_only`
overlay as an RF result.

Before using this sweep as a meaningful hardware experiment, all of the
following must be true:

1. the custom boot-time PL image passes `validate_clean_boot_overlay.py` with
   AD9361 initialized and all expected IIO devices alive;
2. the `lab_11_8` helper sees a live sample-domain status path again, not only
   the reduced safety baseline;
3. RX capture still works after that clean boot.

## Script

| File | Purpose |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_9_rf_discovery_sweep.py` | sweeps `START_OFFSET`, RX manual gain and TX attenuation over SSH, runs the gpreg burst helper, and writes one JSON report |

## Current sweep strategy

Once the bridge is back, the first over-the-air search should vary only the
parameters that are most likely to block deterministic recovery while still
keeping the experiment safe:

1. keep AGC disabled;
2. keep TX LO enabled and TX attenuation conservative;
3. sweep RX gain in manual mode;
4. sweep `START_OFFSET` around the current synthetic reference value;
5. record the best tuple by `RECEIVED_BITS` first, then by timeout/error behavior.

That keeps the sweep explainable and avoids turning the first search into a blind optimization problem.

## Example run

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_9_rf_discovery_sweep.py \
  --ssh-host 192.168.40.1 \
  --ssh-user root \
  --ssh-password analog \
  --start-offsets 48,54,58,62,66,70,74 \
  --rx-gains-db 10,20,30 \
  --tx-attenuations-db -80,-70,-60 \
  --json-out docs/assets/lab119_rf_discovery_sweep_live.json
```

Run that sweep only after the three preconditions above are satisfied.

## Report contract

The JSON report should capture:

- board RF state before the sweep;
- board RF state after the sweep;
- every attempted parameter tuple;
- `busy/done/timeout` behavior for each attempt;
- `RECEIVED_BITS`, `TOTAL_ERRORS` and `PAYLOAD_ERRORS`;
- the best attempt chosen by the script.

## Interpretation

The first good outcome is not necessarily zero BER. The first success criterion is smaller:

- `RECEIVED_BITS > 0`, even if partial;
- a repeatable best tuple across repeated runs;
- no obvious overload or unsafe gain settings.

Only after that should the course move to BER-oriented tuning and longer campaigns.

## Engineering conclusion template

```text
The discovery sweep tested ______ parameter combinations.
The best tuple was START_OFFSET = ______, RX gain = ______ dB, TX attenuation = ______ dB.
The burst recovered ______ bits, and the next step is ______.
```
