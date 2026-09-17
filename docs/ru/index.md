<div class="hero" markdown="1">

# Обзор курса

**Двуязычный курс SDR: от теории к реализации на плате.**

Это русский учебный маршрут: тот же сквозной пайплайн курса, что и на [главной странице](../index.md), но с навигацией по блокам.

<div class="hero-actions">
<a class="hero-button" href="../model-to-measurement/">Начать со сквозного пайплайна</a>
<a class="hero-button secondary" href="status.md">Статус курса</a>
<a class="hero-button secondary" href="../en/">English version</a>
</div>

<div class="badge-line">
<span class="badge-soft">MATLAB / Simulink</span>
<span class="badge-soft">Fixed-point DSP</span>
<span class="badge-soft">FPGA / HDL</span>
<span class="badge-soft">Zynq-7020</span>
<span class="badge-soft">AD9363</span>
<span class="badge-soft">RTL-SDR</span>
</div>

</div>

## Быстрая навигация

<div class="card-grid">

<div class="course-card">
<h3>Структура курса</h3>
<p>Как связаны двенадцать блоков курса между собой.</p>
<a href="course-structure.md">Открыть →</a>
</div>

<div class="course-card">
<h3>Лабораторный трек</h3>
<p>Рекомендованный порядок прохождения лабораторных.</p>
<a href="lab-track.md">Открыть →</a>
</div>

<div class="course-card">
<h3>Медиа-гайд</h3>
<p>Соглашения по графикам, фигурам и записям во всём курсе.</p>
<a href="media-guide.md">Открыть →</a>
</div>

<div class="course-card">
<h3>Статус курса</h3>
<p>Матрица готовности: что измерено, исполняемо или ждёт железа.</p>
<a href="status.md">Открыть →</a>
</div>

<div class="course-card">
<h3>Отладка железа как часть модели</h3>
<p>Почему отладочная инструментация должна быть частью дизайна, а не довеском.</p>
<a href="hardware-debug-by-design.md">Открыть →</a>
</div>

<div class="course-card">
<h3>Проектирование отладочного сигнала</h3>
<p>Как проектировать наблюдаемые тестовые сигналы для bring-up SDR-стенда.</p>
<a href="debug-waveform-design.md">Открыть →</a>
</div>

</div>

## Блоки курса

| Блок | Тема |
|---:|---|
| 1 | [Введение в SDR](blocks/01-intro.md) — инструменты, сигналы и первые приёмные эксперименты |
| 2 | [Сигналы и дискретизация](blocks/02-signals-and-sampling.md) — спектр, aliasing, complex baseband и IQ |
| 3 | [Основы DSP](blocks/03-dsp-basics.md) — FFT, FIR, окна, цифровое смешение и decimation |
| 4 | [Simulink и fixed-point](blocks/04-simulink-and-fixed-point.md) — числовые форматы, масштабирование и квантование |
| 5 | [FPGA / HDL Flow](blocks/05-fpga-hdl-flow.md) — потоковые интерфейсы, Verilog и testbench |
| 6 | [Радиотракт и AD9363](blocks/06-rf-frontend-and-ad9363.md) — частотный план, усиления и настройки AD9363 |
| 7 | [Тракты TX/RX](blocks/07-tx-rx-chains.md) — DUC, DDC, loopback и packet-level метрики |
| 8 | [Модуляция и синхронизация](blocks/08-modulation-and-synchronization.md) — CFO, фаза, тайминг, EVM и BER |
| 9 | [Инструменты записи и анализа](blocks/09-recording-and-analysis-tools.md) — metadata, форматы, replay и контроль качества |
| 10 | [KiCad и базовая электроника](blocks/10-kicad-and-basic-electronics.md) — аттенюаторы, фильтры и RF safety |
| 11 | [Интегрированный SDR-проект](blocks/11-integrated-sdr-project.md) — модель, реализация, запись и отчёт |
| 12 | [Итоговые проекты](blocks/12-final-projects.md) — portfolio-ready инженерные результаты |
