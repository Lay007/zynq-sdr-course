# 08. Analysis of the Recorded Signal in Simulink

## Purpose of the section
To learn how to use Simulink to read a recorded IQ signal and visually analyze its time-domain and spectral characteristics.

## 1. Why analyze the recording in Simulink
In this block, Simulink is needed not only as a modeling environment, but also as a tool for building the engineering chain:

**recorded real signal → block-based analysis model → confirmation of signal behavior**

This is important because in later blocks the course will rely on Simulink as a bridge between:
- theory;
- model;
- fixed-point;
- hardware implementation.

## 2. What the student should do
In this work, the student should:
- load the IQ file into a Simulink model;
- represent it as a complex signal;
- display the time waveform;
- display the spectrum;
- compare the result with MATLAB and HDSDR;
- prepare the model for reuse in later work.

## 3. General logic of the model
The simplest analysis model should include:
1. A file data source.
2. Formation of I and Q channels.
3. Combination into a complex signal.
4. Time-domain analysis.
5. Spectral analysis.
6. Display of the results.

## 4. Recommended model structure
An approximate block structure:
- **File Reader / From Multimedia File / similar source**
- **Data Type Conversion**
- **Demux / Selector**
- **Real-Imag to Complex**
- **Time Scope**
- **Spectrum Analyzer**

If the file format is not supported directly, one can:
- first load it into the MATLAB workspace;
- then use a block that feeds the signal into Simulink.

## 5. What must be configured
Before running the analysis, define:
- sampling frequency;
- data type;
- length of the analyzed fragment;
- I/Q format;
- spectral display scale.

## 6. Minimum task for the first block
The student should build a model that allows:
- taking an IQ recording;
- forming a complex stream;
- showing the time waveform;
- showing the spectral peak of the test tone.

This is already enough for Simulink to become part of the practical route of the course.

## 7. What should be observed
### In the time domain
- regular signal structure;
- stable amplitude;
- no gross distortions.

### In the spectrum
- a pronounced peak;
- stable frequency position;
- noise floor;
- possible side components.

## 8. Comparison with other tools
After analysis in Simulink, it is useful to compare the result with:
- observation in HDSDR;
- the MATLAB spectrum;
- analysis in Python.

The student should make sure that the same signal:
- is recognizable in different environments;
- gives consistent results;
- confirms the correctness of the experiment.

## 9. Practical value of this stage
This stage is especially important because later Simulink will be used not only for analysis, but also for:
- signal synthesis;
- fixed-point preparation;
- structural description of the chain;
- transition to hardware implementation.

So even in the first block Simulink should become a “working tool” for the student, not just a theoretical environment.

## 10. What to include in the report
It is recommended to include:
- an image of the Simulink model;
- the time-domain analysis window;
- the spectral analysis window;
- a short description of model parameters;
- a comparison with MATLAB or HDSDR.

## 11. Conclusions
After completing this section, the student should:
- be able to use Simulink to analyze a recorded IQ signal;
- understand how a real recording is inserted into a block model;
- see the link between offline analysis and future hardware implementation.
