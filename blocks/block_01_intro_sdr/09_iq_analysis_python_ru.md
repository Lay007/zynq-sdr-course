# 09. Анализ записанного сигнала в Python

## Цель раздела
Научиться анализировать записанный IQ-сигнал в Python и использовать скриптовый подход для автоматизации измерений.

## Задачи анализа
- считать файл IQ-данных;
- преобразовать данные в комплексный сигнал;
- построить временную форму;
- построить спектр;
- найти основную частоту тона;
- сохранить результаты.

## Пример Python-скрипта
```python
import numpy as np
import matplotlib.pyplot as plt

filename = "tone_capture_iq.bin"
fs = 2.4e6

raw = np.fromfile(filename, dtype=np.int16)
i_data = raw[0::2]
q_data = raw[1::2]
x = i_data.astype(np.float64) + 1j * q_data.astype(np.float64)

nfft = 4096
X = np.fft.fftshift(np.fft.fft(x[:nfft], nfft))
f = np.fft.fftshift(np.fft.fftfreq(nfft, d=1/fs))

plt.plot(f, 20 * np.log10(np.abs(X) + 1e-12))
plt.grid(True)
plt.show()
```
