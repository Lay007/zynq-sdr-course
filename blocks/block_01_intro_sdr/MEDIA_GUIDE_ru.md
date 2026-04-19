# MEDIA GUIDE — как добавлять фото, схемы и анимацию

## Рекомендуемая структура папок
```text
images/
├── photos/
├── screenshots/
├── diagrams/
├── schematics/
└── animations/
```

## Что хранить в `photos/`
Реальные фотографии оборудования и стенда.
Примеры:
- `board_zynq7020_top.jpg`
- `rtl_sdr_receiver.jpg`
- `lab_setup_overview.jpg`

## Что хранить в `screenshots/`
Скриншоты HDSDR, MATLAB, Simulink, GNU Radio, KiCad.
Использовать **PNG**.

## Что хранить в `diagrams/`
Блок-схемы и архитектурные иллюстрации.
Основной формат — **SVG**.

## Что хранить в `schematics/`
Экспортированные изображения схем для документации. Исходники KiCad следует хранить в `kicad/`.

## Что хранить в `animations/`
Короткие GIF:
- `tone_frequency_change.gif`
- `tone_level_change.gif`

## Что стоит добавить уже в первый блок
### Фото
- SDR-плата;
- RTL-SDR;
- общий вид стенда;
- кабельное соединение.

### Скриншоты
- HDSDR с тестовым тоном;
- MATLAB FFT;
- Simulink-модель;
- GNU Radio flowgraph;
- KiCad со схемой.

### Диаграммы
- архитектура SDR-тракта;
- маршрут первого эксперимента;
- структура стенда.
