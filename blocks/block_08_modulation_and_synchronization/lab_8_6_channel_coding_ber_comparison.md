# Lab 8.6 - Channel coding BER comparison with interleaving

## Goal

Compare BER performance for several link variants at the same SNR:

- uncoded baseline;
- convolutional code (hard Viterbi);
- sparse parity-check (LDPC-like) block code;
- with and without interleaving under bursty disturbances.

## Executable file

| File | Purpose |
|---|---|
| `blocks/block_08_modulation_and_synchronization/python/lab_8_6_channel_coding_ber_comparison.py` | BER curves across SNR points |

Run from the repository root:

```bash
python blocks/block_08_modulation_and_synchronization/python/lab_8_6_channel_coding_ber_comparison.py
```

## Generated artifacts

```text
docs/assets/lab86_channel_coding_ber.png
docs/assets/lab86_channel_coding_metrics.json
```

## What this lab demonstrates

1. Coding gain relative to uncoded transmission.
2. Impact of burst disturbances on hard-decision decoders.
3. Why interleaving helps under bursty, not purely memoryless, error processes.

## Report checklist

- [ ] Include BER curves for all variants.
- [ ] Highlight SNR points where coding gain is most visible.
- [ ] Compare interleaved vs non-interleaved performance.
- [ ] Explain limits of compact LDPC-like and hard-decision decoding model.

