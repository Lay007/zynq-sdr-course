# Блок 4 — workflow float → fixed-point → HDL

Блок 4 нужен для того, чтобы студент перестал воспринимать DSP-алгоритм как бесконечно точную математическую формулу и начал видеть аппаратные ограничения: разрядность, масштабирование, переполнение, задержку и стоимость реализации.

## Главная инженерная цепочка

```mermaid
flowchart LR
    FLOAT[Float reference model] --> RANGE[Range analysis]
    RANGE --> SCALE[Scaling plan]
    SCALE --> FIXED[Fixed-point model]
    FIXED --> ERROR[Error analysis]
    ERROR --> HDL[HDL-ready architecture]
    HDL --> REPORT[Readiness report]
```

## Что фиксируем перед fixed-point

Перед переводом модели в fixed-point нужно зафиксировать:

| Параметр | Почему важен |
|---|---|
| Sample rate | определяет частотный план и latency в отсчётах |
| Полоса сигнала | влияет на фильтры и допустимое снижение Fs |
| Максимальная амплитуда | нужна для выбора integer bits |
| Crest factor / PAPR | важен для модулированных сигналов |
| Допустимая ошибка | определяет fractional bits |
| Требуемое подавление | влияет на коэффициенты FIR |
| Интерфейс потока | valid/ready, frame boundaries, latency |

## Базовый fixed-point формат

Используем обозначение:

```text
Q<I>.<F>
```

где:

- `I` — число integer bits вместе со знаком;
- `F` — число fractional bits;
- общая ширина слова `W = I + F`.

Пример:

```text
Q1.15 -> signed 16-bit value, range approximately [-1, 1)
Q2.14 -> signed 16-bit value, range approximately [-2, 2)
Q4.20 -> signed 24-bit value, wider dynamic range and better precision
```

## Таблица выбора форматов

| Узел | Рекомендуемый стартовый формат | Комментарий |
|---|---|---|
| Input IQ | Q1.15 или Q2.14 | зависит от нормировки ADC/IQ файла |
| NCO sin/cos | Q1.15 | обычно достаточно для первого mixer |
| FIR coefficients | Q1.15 или Q1.17 | влияет на stopband attenuation |
| FIR accumulator | Q4.28 или шире | должен выдержать сумму taps |
| Mixer product | Q2.30 до rounding | произведение двух Q1.15 |
| Output stream | Q1.15 | после scaling/saturation |

## Правило роста разрядности

### Сложение

При сложении двух чисел одинакового формата нужен дополнительный бит для защиты от переполнения.

```text
W_sum = W + 1
```

### Умножение

При умножении ширины складываются:

```text
W_product = W_a + W_b
F_product = F_a + F_b
```

### FIR accumulation

Для FIR с `N` taps нужно добавить запас:

```text
guard_bits = ceil(log2(N))
```

## Saturation vs wrap

| Режим | Поведение | Где допустим |
|---|---|---|
| Wrap | переполнение по модулю | почти никогда в финальном DSP-тракте |
| Saturation | ограничение на максимум/минимум | предпочтительно на внешних границах блока |
| Rounding | округление при снижении разрядности | лучше, чем простое truncation |
| Truncation | отбрасывание младших бит | дешевле, но добавляет bias |

## Анализ ошибки

Для каждого fixed-point блока нужно сравнить результат с float reference:

```text
error[n] = y_float[n] - y_fixed[n]
```

Рекомендуемые метрики:

| Метрика | Смысл |
|---|---|
| RMS error | средняя ошибка реализации |
| Max abs error | худший выброс |
| SQNR | отношение мощности сигнала к мощности ошибки |
| EVM | удобно для модулированных IQ-сигналов |
| Spur level | показывает артефакты NCO/mixer/quantization |

## Минимальная лаборатория блока 4

1. Взять FIR или digital mixer из блока 3.
2. Построить float reference.
3. Выбрать начальные Q-форматы.
4. Реализовать fixed-point модель в MATLAB/Python.
5. Построить ошибку `float - fixed`.
6. Сравнить спектры float/fixed.
7. Заполнить таблицу форматов.
8. Сделать вывод о готовности к HDL.

## HDL readiness checklist

- [ ] Заданы форматы всех входов и выходов.
- [ ] Заданы форматы коэффициентов.
- [ ] Посчитана ширина произведений.
- [ ] Посчитана ширина аккумуляторов.
- [ ] Определена стратегия rounding/saturation.
- [ ] Оценена latency.
- [ ] Указан streaming interface.
- [ ] Есть тестовые векторы float/fixed.
- [ ] Есть допустимая ошибка относительно reference.

## Инженерный вывод

Хороший fixed-point отчёт должен отвечать на вопрос:

> Какую минимальную разрядность можно использовать, чтобы ошибка была допустимой, а реализация оставалась экономичной для FPGA?
