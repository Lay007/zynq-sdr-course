# Блок 12 — трек финальных проектов

Блок 12 превращает курс в набор итоговых инженерных заданий. Каждый проект должен иметь архитектуру, воспроизводимый запуск, данные/metadata, метрики и отчёт.

## Логика финального трека

```mermaid
flowchart LR
    REQ[Project requirements] --> DESIGN[Architecture]
    DESIGN --> IMPL[Implementation]
    IMPL --> TEST[Verification]
    TEST --> DATA[Capture / dataset]
    DATA --> METRICS[Metrics]
    METRICS --> REPORT[Final report]
```

## Варианты проектов

| Проект | Основной фокус | Минимальный результат |
|---|---|---|
| Финальный проект QPSK-модема | DSP + синхронизация | BER/EVM после синхронизации |
| Анализ RF-записи | реальный IQ + метаданные | отчёт FFT/SNR/DC/clipping |
| DSP-блок на FPGA | Verilog + fixed-point | PASS testbench + анализ ошибки |
| Полный отчёт об SDR-измерениях | весь тракт | итоговый отчёт с таблицей pass/fail |

## Общие требования

Каждый финальный проект должен содержать:

- цель и критерии успеха;
- block diagram;
- reproducibility commands;
- metadata или dataset registry entry;
- figures;
- metrics JSON или таблицу;
- limitations;
- next steps.
