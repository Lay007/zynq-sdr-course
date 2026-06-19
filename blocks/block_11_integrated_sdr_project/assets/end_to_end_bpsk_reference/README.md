# End-to-end BPSK reference package

This folder is the shared handoff point for the first modem implementation route:

```text
MATLAB reference -> fixed-point exports -> Simulink/HDL -> Zynq TX/RX
```

## Primary generator

Run from the repository root:

```bash
python blocks/block_11_integrated_sdr_project/python/end_to_end_bpsk_reference.py
```

## Key files

| File | Purpose |
|---|---|
| `config.json` | Common configuration for the reference chain. |
| `tx_bits.txt` | Deterministic BPSK frame bits, including preamble and payload. |
| `tx_symbols_float.txt` | Floating-point symbol sequence as `I Q` pairs. |
| `tx_symbols_q15.txt` | Q1.15 symbol export for HDL and Simulink import. |
| `rrc_taps_float.txt` | Floating-point RRC taps. |
| `rrc_taps_q15.txt` | Q1.15 RRC taps for fixed-point and HDL planning. |
| `sample_plan.json` | Symbol-sampling indices after matched filtering. |
| `handoff_files.json` | Machine-readable list of the main package artifacts. |
| `manifest.yml` | Dataset-style metadata and intended hardware route. |
| `end_to_end_bpsk_reference_v1_tx_reference.ci16` | Synthetic TX burst before channel impairments. |
| `end_to_end_bpsk_reference_v1.ci16` | Synthetic captured burst after impairments. |

## Intended hardware route

- Use the Zynq SDR board as the main transmitter and receiver for BER.
- Use RTL-SDR only as an independent monitor receiver for spectrum checks.
- Promote this synthetic package to real hardware by replacing the generated CI16 capture with a measured file and updating the manifest fields.
