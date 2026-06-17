# Contents — Block 2. Signals, Spectrum, Sampling, and I/Q

## Theory track
1. continuous and discrete signals
2. frequency-domain view and bandwidth
3. sampling rate and aliasing
4. complex envelope and I/Q
5. relation between tone, spectrum, and recorded data
6. basic parameter-selection mistakes

## Practical track
1. Lab 2.1: comparing correct and incorrect sampling-rate interpretation
2. Lab 2.2: visualizing aliasing and validating foldback predictions
3. Lab 2.3: comparing correct I/Q, swapped I/Q and real-only capture
4. matching a model with a recorded signal and its metadata

## Executable lab map

| Lab | Script | Main outputs |
|---|---|---|
| 2.1 | `python/sampling_analysis.py` | time plot, FFT-axis comparison, metrics JSON |
| 2.2 | `python/aliasing_sweep.py` | alias map, example spectra, metrics JSON |
| 2.3 | `python/iq_visualization.py` | I/Q time plot, mirrored-spectrum comparison, metrics JSON |

## Review and discussion questions
1. Which limitations or tradeoffs are central to this block?
2. How should the model, experiment, and analysis tools be linked in this block?
3. Which parameters must be documented for reproducible results?

## Expected block outputs
- time-domain and spectrum plots;
- sampling-parameter table;
- comparison of aliasing scenarios;
- block laboratory report.
