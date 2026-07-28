# Сравнение цифровых сигналов

| Семейство | Спектральная эффективность | Огибающая / PAPR | Сложность синхронизации | Относительная FPGA-стоимость | Типичное применение |
|---|---|---|---|---|---|
| QPSK | 2 бита/символ | Постоянная огибающая символа; shaping даёт умеренные пики | Несущая, фаза, timing и quadrant resolution | Низкая–средняя | Универсальные устойчивые каналы |
| 16-QAM | 4 бита/символ | Непостоянная; чувствительна к back-off и линейности | Требования QPSK плюс точность gain/phase | Средняя | Высокая скорость и OFDM payload |
| OFDM | Много параллельных поднесущих | Высокий PAPR, нужен контроль clipping/back-off | Packet timing, CFO, pilots и channel estimate | Высокая: FFT, buffers, equalizer | Широкополосные частотно-селективные каналы |
| GFSK | 1 бит/символ в модели | Constant envelope, PAPR около 0 dB | Symbol timing; discriminator не требует абсолютной фазы | Низкая | Low-power telemetry и нелинейный передатчик |
| CSS | `SF` бит на длинный chirp-символ | Constant envelope | Preamble, dechirp/FFT, CFO и sample-rate tracking | Средняя–высокая | Дальняя связь с низкой скоростью |
| DSSS | Скорость уменьшается во столько раз, какова длина spreading code | BPSK-like constant envelope | Захват и tracking PN-кода | Средняя: LFSR и высокоскоростной correlator | Устойчивость к помехам и code-domain links |

Сравнение относится к учебным моделям и не является утверждением совместимости со стандартами.
