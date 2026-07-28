# Лабораторная 8.22 — Пакетная CSS-синхронизация и PER

## Цель

Расширить CSS-детектор из Labs 8.20/8.21 до детерминированного пакетного приёмника:

- обнаружить преамбулу из повторяющихся upchirp и оценить начало пакета;
- проверить sync word из двух символов и два downchirp;
- оценить целую и дробную составляющие CFO;
- скорректировать CFO перед решением payload-символов;
- измерить SER, PER, пропуски обнаружения и ложные срабатывания;
- проверить чувствительность к sample-rate offset.

Сигнал по-прежнему называется **CSS/LoRa-like**, а не LoRa-compatible: модель намеренно не реализует LoRa header, whitening, coding, interleaving и CRC.

## Структура пакета

```text
шумовой префикс | 8 upchirp | sync 18,52 | 2 downchirp |
16 payload-символов | шумовой суффикс
```

Timing metric выполняет dechirp каждого кандидата преамбулы, суммирует мощность FFT-bin по повторяющимся chirp и сравнивает сильнейший bin со средней мощностью. Sync word и downchirp подтверждают, что высокий metric относится к ожидаемой структуре пакета.

## Оценка CFO

FFT-пик преамбулы даёт целое смещение в bin, а поворот фазы этого пика между соседними upchirp — дробную часть:

```text
CFO = целое смещение FFT-bin + phase_step / (2π)
```

По умолчанию вносится CFO `1,25` bin. Без коррекции все payload-пакеты ошибочны; после синхронизации и коррекции контрольная точка `-6 dB` имеет нулевой PER для фиксированного seed.

## Запуск

```bash
python blocks/block_08_modulation_and_synchronization/python/lab_8_22_css_packet_sync_per.py
```

## Артефакты

```text
docs/assets/lab822_css_timing_metric.png
docs/assets/lab822_css_per_vs_snr.png
docs/assets/lab822_css_sro_sensitivity.png
docs/assets/lab822_css_packet_metrics.json
```

## Статистический объём

- 1000 пакетов на каждую точку SNR;
- 16 000 payload-символов на точку;
- 1000 независимых noise-only испытаний false alarm;
- 200 пакетов на каждую точку sample-rate offset.

Нулевой результат — конечный тест, а не доказательство сколь угодно малого PER. Для 1000 пакетов без ошибок приближённая верхняя 95%-граница равна `3/1000`.

## Критерии приёмки

- начало примера, sync word и downchirp восстановлены;
- ошибка CFO меньше `0,05` bin;
- corrected PER ниже uncorrected PER в контрольной точке;
- присутствуют missed-detection и false-alarm statistics;
- SRO sweep показывает деградацию и предел коррекции пересэмплированием.
