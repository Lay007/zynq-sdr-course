#include <cmath>
#include <complex>
#include <fstream>
#include <iostream>
#include <vector>

int main() {
    constexpr double Fs = 1.0e6;
    constexpr int N = 4096;
    constexpr double f_sig = 50.0e3;
    constexpr double f_shift = 100.0e3;
    constexpr double pi = 3.14159265358979323846;

    std::vector<std::complex<double>> x(N);
    std::vector<std::complex<double>> y(N);

    for (int n = 0; n < N; ++n) {
        const double t = static_cast<double>(n) / Fs;
        const std::complex<double> sig = std::exp(std::complex<double>(0.0, 2.0 * pi * f_sig * t));
        const std::complex<double> nco = std::exp(std::complex<double>(0.0, 2.0 * pi * f_shift * t));
        x[n] = sig;
        y[n] = sig * nco;
    }

    std::ofstream out("lab3_digital_mixing_iq.csv");
    out << "n,x_i,x_q,y_i,y_q\n";
    for (int n = 0; n < N; ++n) {
        out << n << "," << x[n].real() << "," << x[n].imag()
            << "," << y[n].real() << "," << y[n].imag() << "\n";
    }

    std::cout << "Generated lab3_digital_mixing_iq.csv\n";
    std::cout << "Expected frequency shift: " << f_shift << " Hz\n";
    std::cout << "Expected output tone: " << (f_sig + f_shift) << " Hz\n";

    return 0;
}
