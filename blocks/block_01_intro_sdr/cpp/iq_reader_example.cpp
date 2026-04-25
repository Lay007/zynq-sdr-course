#include <algorithm>
#include <complex>
#include <cstdint>
#include <fstream>
#include <iostream>
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

    try {
        const auto x = load_iq_file(filename);
        std::cout << "Loaded complex samples: " << x.size() << "\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << ex.what() << "\n";
        return 1;
    }
}
