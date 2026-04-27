# 19. Лабораторная работа 6. Полный SDR-тракт (end-to-end)

## Цель
Объединить все элементы курса в один эксперимент.

## Полная цепочка

```text
TX → Channel → RX → Sync → Demod → Metrics
```

## Диаграмма

```mermaid
flowchart TB
    classDef dsp fill:#DCFCE7,color:#0F172A,stroke:#16A34A;
    classDef rf fill:#FFE4E6,color:#0F172A,stroke:#E11D48;
    classDef metric fill:#F1F5F9,color:#0F172A,stroke:#64748B;

    TX["TX signal"]:::rf
    CH["Channel"]:::rf
    RX["Receiver"]:::rf
    SYNC["Synchronization"]:::dsp
    DEMOD["Demodulation"]:::dsp
    METRICS["Metrics"]:::metric

    TX --> CH --> RX --> SYNC --> DEMOD --> METRICS
```

## Задачи

1. Сформировать сигнал (QPSK).
2. Передать через тракт.
3. Принять сигнал.
4. Выполнить синхронизацию.
5. Демодулировать.
6. Оценить BER и EVM.

## Результат

Студент получает полное понимание SDR-системы.
