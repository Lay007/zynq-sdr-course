// Read an interleaved int16 IQ file (.ci16) and find the strongest tone with a plain DFT.
//
//   g++ -std=c++17 -O2 -o iq_reader_example iq_reader_example.cpp
//   ./iq_reader_example capture.ci16 2400000
//
// The DFT is the educational O(N^2) form over N = 4096 samples; a real tool would use
// an FFT library (FFTW, KissFFT). The printed frequency is the offset from the
// receiver's tuning frequency.

#include <algorithm>
#include <cmath>
#include <complex>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

std::vector<std::complex<double>> load_iq_file(const std::string& filename) {
    std::ifstream file(filename, std::ios::binary);
    if (!file) {
        throw std::runtime_error("Cannot open file: " + filename);
    }

    std::vector<int16_t> raw;
    int16_t value = 0;
    while (file.read(reinterpret_cast<char*>(&value), sizeof(value))) {
        raw.push_back(value);
    }

    if (raw.size() < 2 || raw.size() % 2 != 0) {
        throw std::runtime_error("Invalid IQ file length");
    }

    std::vector<std::complex<double>> x;
    x.reserve(raw.size() / 2);

    for (size_t k = 0; k + 1 < raw.size(); k += 2) {
        x.emplace_back(static_cast<double>(raw[k]), static_cast<double>(raw[k + 1]));
    }

    return x;
}

int main(int argc, char** argv) {
    const std::string filename = (argc > 1) ? argv[1] : "tone_capture_iq.bin";
    const double fs = (argc > 2) ? std::stod(argv[2]) : 2.4e6;

    try {
        const auto x = load_iq_file(filename);
        std::cout << "Loaded complex samples: " << x.size() << "\n";

        const size_t n = std::min<size_t>(x.size(), 4096);
        const double pi = std::acos(-1.0);
        size_t best_bin = 0;
        double best_power = -1.0;
        for (size_t k = 0; k < n; ++k) {
            std::complex<double> sum(0.0, 0.0);
            for (size_t m = 0; m < n; ++m) {
                sum += x[m] * std::polar(1.0, -2.0 * pi * static_cast<double>(k * m % n) / static_cast<double>(n));
            }
            if (std::norm(sum) > best_power) {
                best_power = std::norm(sum);
                best_bin = k;
            }
        }

        // Bins above n/2 are negative frequencies.
        const long signed_bin = (best_bin < n / 2) ? static_cast<long>(best_bin)
                                                   : static_cast<long>(best_bin) - static_cast<long>(n);
        std::cout << "DFT length: " << n << ", bin width: " << fs / n << " Hz\n";
        std::cout << "Peak offset from the tuning frequency: " << signed_bin * fs / n << " Hz\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << ex.what() << "\n";
        return 1;
    }
}
