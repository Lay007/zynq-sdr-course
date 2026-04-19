# 10. Analysis of the Recorded Signal in C++

## Purpose of the section
To show how offline analysis of an IQ file can be implemented in C++ and why this approach matters for high-performance DSP applications.

## 1. Why C++ is needed in the course
Although MATLAB and Python are more convenient for the first analysis, C++ remains an important engineering tool because it allows the student to:
- process large files;
- create fast utilities;
- prepare code for integration into real projects;
- build high-performance analysis and control tools.

Later, C++ may become the basis of service applications, backend components, and DSP utilities.

## 2. Goals of this stage
Within the first block C++ is used in a lightweight mode. The student should:
- read an IQ file;
- form a complex array;
- perform basic spectral analysis;
- estimate the frequency of the main tone;
- understand the architecture of a simple console DSP utility.

## 3. What the program should do
A minimum program should:
1. Open the file.
2. Read interleaved I/Q data.
3. Convert it to a complex array.
4. Perform FFT or equivalent spectral analysis.
5. Find the maximum of the spectrum.
6. Print an estimated peak frequency.

## 4. What can be used
At the first stage two approaches are possible:

### Option 1. Educational
Implement a simple DFT/FFT manually or in a simplified form.

### Option 2. Practical
Use an external library:
- FFTW
- Intel IPP
- KissFFT
- another suitable FFT library

For the first block, a simplified demonstration variant is acceptable.

## 5. Example general program structure
```cpp
#include <iostream>
#include <fstream>
#include <vector>
#include <complex>
#include <cstdint>

int main() {
    const char* filename = "tone_capture_iq.bin";
    std::ifstream file(filename, std::ios::binary);

    if (!file) {
        std::cerr << "Cannot open file\n";
        return 1;
    }

    std::vector<int16_t> raw;
    int16_t value;
    while (file.read(reinterpret_cast<char*>(&value), sizeof(value))) {
        raw.push_back(value);
    }

    if (raw.size() < 2) {
        std::cerr << "Not enough data\n";
        return 1;
    }

    std::vector<std::complex<double>> x;
    x.reserve(raw.size() / 2);

    for (size_t k = 0; k + 1 < raw.size(); k += 2) {
        double i = static_cast<double>(raw[k]);
        double q = static_cast<double>(raw[k + 1]);
        x.emplace_back(i, q);
    }

    std::cout << "Loaded complex samples: " << x.size() << "\n";

    // FFT and peak search can be added here

    return 0;
}
```

## 6. What the student should understand
At this stage it is important not so much to write a perfect DSP library, but to understand:
- how the IQ storage format is organized;
- how a processing pipeline is built in C++;
- how complex data is represented in memory;
- why C++ is useful for performance-oriented tasks;
- how offline analysis can be packaged as a standalone utility.

## 7. What results are needed in the first block
It is enough to obtain:
- successful file reading;
- formation of a complex signal;
- basic spectrum calculation;
- an estimate of the main peak frequency;
- console output of the parameters.

## 8. Practical value of this stage
Even a simple C++ program is important because it shows the student the transition from educational analysis to applied development.

This is how, in real projects, the following appear:
- recording analyzers;
- service utilities;
- autonomous DSP modules;
- backend components of SDR systems.

## 9. What to include in the report
It is recommended to include:
- a short description of the program structure;
- a code fragment for reading the IQ file;
- the method of spectrum calculation;
- the estimated peak frequency;
- a conclusion about applicability of C++ to signal processing.

## 10. Conclusions
After this stage the student should:
- understand how to read IQ data in C++;
- see the role of C++ in high-performance signal processing;
- understand how a real engineering utility grows out of an educational analysis.
