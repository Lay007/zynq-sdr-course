# 11. Analysis of the Recorded Signal in GNU Radio

## Purpose of the section
To become familiar with GNU Radio as an environment for visually assembling SDR chains and to use it for analysis of a recorded IQ signal.

## 1. Why GNU Radio is needed
GNU Radio is useful because it allows the student to quickly build a working SDR chain from ready-made blocks and visually observe the signal path.

For an educational course this is especially valuable because the student gets another view of the same experiment:
- without writing a large amount of code;
- in an intuitive block-based form;
- with quick structural changes during analysis.

## 2. Task of the section
Within the first block the student should:
- open a recorded IQ file;
- feed it into a GNU Radio flowgraph;
- display the signal spectrum;
- optionally display the time-domain waveform;
- compare the picture with HDSDR, MATLAB, and Python.

## 3. Minimum flowgraph structure
The simplest scheme may include:
- **File Source**
- **Throttle**
- **QT GUI Frequency Sink**
- **QT GUI Time Sink**

If the file already contains complex samples in a suitable format, this is enough for the first demonstration.

## 4. What must be configured
It is necessary to set correctly:
- file data type;
- complex signal format;
- sampling frequency;
- FFT size;
- display window length.

If these parameters are wrong, the spectrum will be interpreted incorrectly.

## 5. What the student should see
As a result of building the flowgraph, the student should observe:
- a stable spectral peak of the test tone;
- the time-domain structure of the signal;
- agreement with the results obtained in other environments.

## 6. Why GNU Radio is useful in this course
GNU Radio complements the other tools well:

- **HDSDR** — fast observation of a real signal;
- **MATLAB / Simulink** — modeling and system-level analysis;
- **Python** — automation;
- **C++** — high-performance implementation;
- **GNU Radio** — quick assembly and visual debugging of SDR chains.

Thus the student gets used immediately to the fact that the same signal can be studied with different engineering tools.

## 7. Minimum practical task
It is enough to assemble a flowgraph that:
- reads an IQ file;
- shows the spectrum;
- shows the time-domain waveform;
- allows display parameters to be changed;
- confirms the presence of the test tone.

## 8. What can be extended later
In later stages the student can use GNU Radio for:
- digital frequency translation;
- filtering;
- decoding;
- analysis of multiple signals;
- playback and modeling of SDR chains.

So already in the first block GNU Radio acts as a convenient educational platform that can later be expanded.

## 9. What to include in the report
It is recommended to include:
- a screenshot of the flowgraph;
- the spectrum display window;
- the time-domain display window;
- sampling-frequency settings;
- a short comparison with other tools.

## 10. Conclusions
After completing this stage, the student should:
- be able to assemble a simple flowgraph for recording analysis;
- understand the role of GNU Radio in SDR development;
- see how the same signal is analyzed in several engineering environments.
