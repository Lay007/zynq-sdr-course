Fs = 1e6;
N = 4096;

t = (0:N-1)/Fs;

f_sig = 50e3;
f_int = 250e3;

x = exp(1j*2*pi*f_sig*t) + 0.5*exp(1j*2*pi*f_int*t);

cutoff = 100e3;
num_taps = 101;

h = fir1(num_taps-1, cutoff/(Fs/2));

y = filter(h,1,x);

figure;

subplot(3,1,1);
X = fftshift(fft(x));
f = fftshift(linspace(-Fs/2, Fs/2, N));
plot(f/1e3,20*log10(abs(X)+1e-12));
title('Before filtering');

subplot(3,1,2);
[H,w] = freqz(h,1,1024,Fs);
plot(w/1e3,20*log10(abs(H)+1e-12));
title('FIR response');

subplot(3,1,3);
Y = fftshift(fft(y));
plot(f/1e3,20*log10(abs(Y)+1e-12));
title('After filtering');
