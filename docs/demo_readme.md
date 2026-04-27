# SDR Course Demo (GitHub)

This page demonstrates how the course content translates into real engineering artifacts.

## Demo structure

Each lab should provide:

- input IQ data;
- processing script (Python / MATLAB);
- output plots;
- short explanation.

## Example: Lab 1 (tone)

### Input
- IQ recording (WAV / RAW)

### Processing
- FFT computation

### Output
- spectrum plot;
- peak frequency;

### Result

```text
Expected tone: 100 kHz offset
Measured tone: 99.8 kHz
Error: 0.2 kHz
```

## Example: Lab 3 (QPSK)

### Input
- recorded IQ signal

### Output
- constellation diagram
- BER estimate

## Demo philosophy

The demo should:

- be reproducible;
- be minimal;
- clearly show the engineering result;
- match IEEE-style figures.

## Future improvements

- automated plot generation (CI);
- dataset versioning;
- interactive notebooks;
- web visualization.
