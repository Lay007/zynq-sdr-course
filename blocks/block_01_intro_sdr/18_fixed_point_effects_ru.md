# 18. Fixed-point эффекты в DSP и FPGA

## Цель
Понять, как ограниченная разрядность влияет на сигнал.

## Основные эффекты

### Квантование
- ошибка округления;
- добавляет шум.

### Переполнение
- wrap-around;
- saturation.

### Масштабирование
- выбор коэффициентов влияет на динамический диапазон.

## Диаграмма

```mermaid
flowchart TB
    classDef dsp fill:#DCFCE7,color:#0F172A,stroke:#16A34A;

    FLOAT["Floating-point model"]:::dsp
    FIXED["Fixed-point"]:::dsp
    ERR["Quantization error"]:::dsp

    FLOAT --> FIXED --> ERR
```

## Практический вывод

Fixed-point — главный источник ошибок при переходе от модели к FPGA.
