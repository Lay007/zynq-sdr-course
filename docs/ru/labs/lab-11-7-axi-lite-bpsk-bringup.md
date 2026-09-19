# Лабораторная 11.7 — Запуск BPSK через AXI-Lite со стороны PS

## Цель

Выполнить наименьшую воспроизводимую последовательность управления Processing System для детерминированного ядра пакета BPSK:

```text
PS / ПО -> регистры AXI-Lite -> кадровое BPSK BER-ядро -> разведочный пакет AD9363
```

Работа соединяет:

- Lab 5.11, определившую и проверившую контракт регистров AXI-Lite;
- Lab 6.3, зафиксировавшую дисциплину усиления и частоты AD9363 для первого RF-прогона;
- аппаратный handoff Блока 11, где один короткий пакет необходимо запустить безопасно и воспроизводимо.

## Инженерный вопрос

> Какая минимальная последовательность на стороне PS должна пройти успешно, прежде чем пробовать более длинные RF-измерения или кампании BER?

## Исполняемый файл

| Файл | Назначение |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_7_axi_lite_bpsk_bringup.py` | считывает `ID` AXI-Lite, программирует регистры пакета, запускает один прогон, опрашивает `busy/done`, читает счётчики BER |

## Локальный прогон с имитацией

Запуск из корня репозитория:

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_7_axi_lite_bpsk_bringup.py \
  --backend mock \
  --max-total-errors 0 \
  --max-payload-errors 0 \
  --json-out docs/assets/lab117_axi_lite_bringup_mock.json
```

Ожидаемое локальное поведение:

- скрипт завершается с кодом `0`;
- `busy_observed` и `done_observed` оба `true`;
- `received_bits == frame_bit_count`;
- `total_errors == 0`;
- `payload_errors == 0`.

## Прогон на настоящей плате

В образе Linux на Zynq запускайте от `root` или через `sudo`. Используйте реальный базовый адрес AXI-Lite из Vivado Address Editor, экспортированных заголовков или заметок по handoff платы.

Экспортированный файл handoff Vivado можно осмотреть прямо из этого репозитория:

```bash
python tools/inspect_xsa_memmap.py hardware/7020_ad936x_sdr/ps/ad936x_no_os_reference/system_top.xsa
python tools/inspect_xsa_memmap.py path/to/your_regenerated_design.xsa --find bpsk --require-match
```

Помощник также понимает ZIP-пакеты вендора, содержащие вложенный `system_top.xsa`, например:

```bash
python tools/inspect_xsa_memmap.py E:\7020\7020_AD936X_SDR\Vivado2021.1\Driver_PL_PS\AD936X_PS.zip --find axi_ad9361
```

Текущий экспорт `ad936x_no_os_reference/system_top.xsa` содержит `axi_ad9361` и два окна DMA, но **пока не** содержит `bpsk_zynq_ber_axi_lite`. Пока пользовательский IP модема не вставлен в block design и XSA не пересоздан, любое значение `--base-addr` ниже — лишь пример-заглушка.

Замечание о пакете вендора из `E:\7020`:

- пакет прошивки Pluto-подобный и использует `root` / `analog`;
- рекомендация по последовательной консоли — `115200` бод;
- входящий в пакет `uEnv.txt` задаёт `ipaddr=192.168.2.1` и `ipaddr_host=192.168.2.10`;
- сопутствующие README из того же пакета также упоминают `192.168.1.10`.

Именно это несовпадение и есть причина, по которой рабочий процесс курса должен сначала опросить активный образ, а не предполагать IP вендора по умолчанию.

Прямое отображение `/dev/mem`:

```bash
sudo python blocks/block_11_integrated_sdr_project/python/lab_11_7_axi_lite_bpsk_bringup.py \
  --backend mmap \
  --base-addr 0x43C00000 \
  --frame-bit-count 281 \
  --preamble-count 25 \
  --start-offset 62 \
  --json-out reports/lab117_axi_lite_bringup.json
```

Запасной вариант через утилиту `devmem`:

```bash
sudo python blocks/block_11_integrated_sdr_project/python/lab_11_7_axi_lite_bpsk_bringup.py \
  --backend devmem \
  --base-addr 0x43C00000 \
  --frame-bit-count 281 \
  --preamble-count 25 \
  --start-offset 62 \
  --json-out reports/lab117_axi_lite_bringup.json
```

Удалённая проверка со стороны хоста по Ethernet без копирования скрипта на плату:

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_7_axi_lite_bpsk_bringup.py \
  --backend ssh-devmem \
  --ssh-host 192.168.40.1 \
  --ssh-user root \
  --ssh-password analog \
  --base-addr 0x43C00000 \
  --frame-bit-count 281 \
  --preamble-count 25 \
  --start-offset 62
```

Живая заметка о плате от **2026-06-19**:

- стоковый course-clean образ отвечал по IIO по адресу `192.168.40.1`;
- живое дерево устройств объявляло `mwipcore@43c00000` с `compatible = "mathworks,mwipcore-axi4lite-v1.00"`;
- прямые чтения регистров по `0x43C00000 + {0x00..0x1C}` возвращали `Bus error`, тогда как окна ADI-эталона по `0x79020000`, `0x79024000`, `0x7C400000` и `0x7C420000` читались.

Это означает, что текущий образ платы **ещё не** готов к запуску Lab 11.7: адрес объявлен, но загруженный проект PL не предоставляет работающего slave в этом окне.

## Бэкенды

| Бэкенд | Назначение |
|---|---|
| `mock` | локальная самопроверка, удобная для CI, без железа |
| `mmap` | прямой доступ Linux `/dev/mem` на плате |
| `devmem` | запасной вариант, когда отображение `/dev/mem` неудобно, но `devmem` есть |
| `ssh-devmem` | удалённый доступ `devmem` со стороны хоста по SSH к живой плате Linux |

## Контракт регистров

Эта работа использует ту же карту, что и Lab 5.11:

| Смещение | Имя | Смысл |
|---|---|---|
| `0x00` | `CONTROL_STATUS` | запись бита `0` запускает, чтение бита `1` — `busy`, чтение/запись бита `2` — залипающий `done` |
| `0x04` | `FRAME_BIT_COUNT` | общее число передаваемых и сравниваемых бит |
| `0x08` | `PREAMBLE_COUNT` | биты преамбулы, исключаемые из payload BER |
| `0x0C` | `START_OFFSET` | детерминированный индекс отсчёта для решений |
| `0x10` | `RECEIVED_BITS` | восстановленные биты после пакета |
| `0x14` | `TOTAL_ERRORS` | все битовые ошибки |
| `0x18` | `PAYLOAD_ERRORS` | битовые ошибки только payload |
| `0x1C` | `ID` | ожидаемое идентификационное слово `0x4250534B` |

## Порядок первого разведочного пакета

1. Опросите контекст AD9363 по Lab 6.3 или `iio_attr`.
2. Держите мощность TX на минимуме, а усиление RX низким/ручным.
3. Отключите AGC для первого пакета.
4. Сначала прочитайте `ID` через AXI-Lite.
5. Запрограммируйте `FRAME_BIT_COUNT`, `PREAMBLE_COUNT` и `START_OFFSET`.
6. Запустите один короткий пакет.
7. Опрашивайте `busy` и `done`.
8. Прочитайте счётчики BER и сбросьте залипающий `done`.

## Сгенерированный артефакт

Прогон с имитацией записывает:

```text
docs/assets/lab117_axi_lite_bringup_mock.json
```

JSON-отчёт содержит запрограммированную конфигурацию, наблюдаемые биты статуса, счётчики BER и итоговый снимок регистров.

## Чек-лист отчёта

- [ ] Записан реальный базовый адрес AXI-Lite, использованный на железе.
- [ ] Показано одно успешное считывание `ID`.
- [ ] Показаны запрограммированные `FRAME_BIT_COUNT`, `PREAMBLE_COUNT` и `START_OFFSET`.
- [ ] Указано, наблюдались ли и `busy`, и `done`.
- [ ] Записаны `RECEIVED_BITS`, `TOTAL_ERRORS` и `PAYLOAD_ERRORS`.
- [ ] Указано, является ли первый прогон только разведочным или уже уровня BER.
- [ ] Прогон связан с таблицей настроек AD9363 из Lab 6.3.

## Шаблон инженерного вывода

```text
Путь запуска AXI-Lite со стороны PS готов / не готов.
Считывание ID ядра — ______, последовательность статусов пакета — ______, счётчики BER — ______.
Следующий шаг — ______.
```
