#include <cmath>
#include <complex>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>
namespace fs = std::filesystem;
int main() {
    const double Fs = 1.0e6, f0 = 100.0e3, A = 0.9, phi = M_PI/6.0;
    const std::size_t N = 4096;
    std::vector<std::complex<double>> x(N);
    for (std::size_t i = 0; i < N; ++i) {
        double p = 2.0 * M_PI * f0 * static_cast<double>(i) / Fs + phi;
        x[i] = A * std::exp(std::complex<double>(0.0, p));
    }
    fs::create_directories("results");
    std::ofstream os("results/iq_tone_basic_iq.txt");
    for (const auto& s : x) os << s.real() << ' ' << s.imag() << '
';
    std::cout << "Generated IQ tone and saved results/iq_tone_basic_iq.txt
";
}
