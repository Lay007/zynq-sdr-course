# Hints: FIR → Q15

Try the first hint, rerun the selected stage, and only then read the next.

## Stage 1

1. Output at time zero must not depend on future inputs.
2. Draw a 3-sample impulse response and check whether `h[0]` multiplies the current sample or the oldest one.
3. For output `n`, sum over `k <= n` and `k < len(taps)`. Assume earlier samples are zero.

## Stage 2

1. Signed Q1.15 represents `[-1, 1)`; positive 1.0 is not representable exactly.
2. Round before clipping. Python's `round` uses ties-to-even.
3. Clamp the rounded integer to `-32768..32767`, including when the input magnitude is above 1.

## Stage 3

1. Do not saturate each product or each addition; retain a wide integer accumulator.
2. A product of two Q1.15 integers has 30 fractional bits; after summing products, divide by `2**15` to return to Q1.15.
3. Handle negative halfway cases symmetrically, then saturate once at the output. Compare against Stage 1 for low-amplitude vectors.
