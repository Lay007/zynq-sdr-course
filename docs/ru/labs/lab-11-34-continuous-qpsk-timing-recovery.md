# Лабораторная 11.34 — непрерывное восстановление тактовой фазы QPSK

## Цель

Заменить одноразовый выбор целочисленной фазы непрерывным timing-контуром, способным
компенсировать рассогласование sample clocks, и сохранить baseline в том же bitstream для
честного runtime A/B. Стенд сейчас отключён, поэтому результат пока ограничен моделью, RTL и
физической реализацией; улучшение живого RF-линка ещё не заявляется.

## Что реализовано

Новый `qpsk_symbol_timing_recovery.v` содержит комплексный sign-Gardner:

1. Q16 NCO создаёт два интерполяционных строба на символ.
2. Линейный интерполятор вычисляет sample на дробной фазе между соседними выходами matched
   filter.
3. Чётные стробы выдают символ, нечётные сохраняют середину символа.
4. TED объединяет обе квадратуры:

   `e = sign(sign(I_mid) * sign(I_now - I_prev) + sign(Q_mid) * sign(Q_now - Q_prev))`

5. PI-фильтр обновляет `omega` с ограничением вокруг номинального шага `2/SPS`.

Python-модель точно повторяет fixed-point арифметику и семантику nonblocking assignments.
Общего делителя в RTL нет: при `SPS=8` вычисление `mu/omega` сводится к ограниченной
фиксированной операции.

## Runtime-интерфейс

В bridge обе реализации собраны одновременно:

| `gp_ctrl[14]` | Режим |
|---:|---|
| 0 | прежний fixed-phase sampler |
| 1 | непрерывный Gardner, phase picker принудительно bypass |

При включённом bit 14 в `gp_adc_input_debug` доступны `{omega[15:0], mu[15:0]}`, а capture
debug показывает знаковую трёхуровневую ошибку TED. После runtime mux добавлен один регистр
`valid/I/Q`: он даёт одинаковую задержку данным и разрывает путь от синхронизированного
control bit через mux и два DSP coarse-CFO за один 8-нс такт.

Принятый boot image Lab 11.33 не заменяется до завершения живого A/B.

## Модель

```powershell
python blocks/block_05_fpga_hdl_flow/python/qpsk_timing_recovery_model.py
```

| Samples/symbol | Float Gardner | Fixed Gardner | Fixed phase |
|---:|---:|---:|---:|
| 8.000 | 0 | 0 | 0 |
| 8.030 | 0 | 0 | 0 |
| 8.060 | 0 | 0 | 14 |
| 7.970 | 0 | 0 | 0 |
| 7.940 | 0 | 0 | 12 |

На длинной последовательности из 12 000 символов при реалистичных ±100 ppm fixed-point
Gardner даёт 0 ошибок. Лучший постоянный offset даёт 1790 ошибок при +100 ppm и 1789 при
−100 ppm: начальная удачная фаза не компенсирует накопленный уход часов.

## RTL-регрессии

```powershell
python tools/run_block5_hdl_smoke.py `
  --test tb_qpsk_symbol_timing_recovery `
  --test tb_qpsk_timing_recovery_chain `
  --test tb_qpsk_timing_recovery_mux `
  --test tb_qpsk_timing_recovery_retained
```

Проверено:

- standalone RTL bit-exact совпадает с integer-моделью на 140 символах при `SPS=8.06`;
- полная drifted chain даёт 0/280 ошибок против 15/280 у fixed sampler;
- runtime mux сохраняет тот же результат;
- на сохранённом двухплатном захвате +30 кГц чистыми остаются offsets 3, 4 и 7;
- прежние QPSK top и bridge loopback сохраняют BER=0.

## Физическая реализация

Первый route обнаружил ошибку покрытия XDC: multicycle для timing recovery совпадал только с
BPSK hierarchy. QPSK recurrence длиной 24,836 нс анализировался как одноклоковый и дал
`WNS=-17.340 ns`. После применения корректного setup/hold 4/3 route достиг
`WNS=-0.188 ns`, `TNS=-6.084 ns`, hold `+0.033 ns`.

Худший путь уже шёл не внутри Gardner, а от `gp_ctrl[14]` через runtime mux в coarse-CFO DSP.
Post-route physopt улучшил лишь 0,002 нс, поэтому вместо ослабления constraints добавлена
регистровая граница.

Свежая реализация с этой границей закрыла physical gate:

- `WNS=+0,049 нс`, `TNS=0,000 нс`;
- `WHS=+0,031 нс`, `THS=0,000 нс`;
- разведены все 77 346 routable nets, routing errors отсутствуют;
- использованы 34 314 LUT (64,50%), 40 641 register (38,20%), 8 BRAM tile (5,71%) и
  192 DSP48E1 (87,27%);
- bitgen завершился без errors и critical warnings.

Кандидат сохранён отдельно в
`tmp/snapshot_impl_sweep/lab1134_registered_netdelay/system_top.bit` и не заменяет
board-qualified канонический образ. SHA-256:
`b7086465dba213544c5a4c558c6deeafb93cca3b8cefa9e41bb3e494b2984b9c`.
Timing closure допускает образ к живому A/B, но ещё не доказывает пользу на RF.

## Живой A/B после подключения стенда

1. Board A: проверенный vendor cyclic-DMA TX. Board B: candidate course RX. Кабельный тракт
   915 МГц, 30 dB attenuator, TX −30 dB, RX +50 dB.
2. При +30 кГц выполнить по 10 попыток для offsets 0…7 сначала с `gp_ctrl[14]=0`, затем с
   bit 14. No-lock всегда остаётся в знаменателе.
3. Повторить sweep 0…55 кГц по три попытки на каждый offset и режим.
4. Сохранить все попытки, `mu/omega`, TED, SHA-256 bitstream, commit и RF-настройки.
5. Принимать Gardner только при улучшении confidence interval clean-attempt rate без падения
   full-frame lock rate; затем выполнить длинный BER-run и проверить cycle slips.

Runner Lab 11.32 теперь поддерживает `--timing-recovery`, поэтому обе кампании используют
один код измерения и отличаются только `gp_ctrl[14]`. Результаты собирает post-processor
Lab 11.34:

```powershell
python blocks/block_11_integrated_sdr_project/python/lab_11_32_two_board_fabric_coarse_cfo.py `
  --json-out tmp/lab1134_fixed.json
python blocks/block_11_integrated_sdr_project/python/lab_11_32_two_board_fabric_coarse_cfo.py `
  --timing-recovery --json-out tmp/lab1134_gardner.json
python blocks/block_11_integrated_sdr_project/python/lab_11_34_continuous_qpsk_timing_recovery.py `
  --baseline tmp/lab1134_fixed.json --gardner tmp/lab1134_gardner.json
```

Post-processor отвергает несовпадающие CFO grids, offsets или budgets и оставляет все попытки
в знаменателях lock/clean rate.

Текущий честный вывод: **непрерывный QPSK timing recovery реализован, прошёл модель/RTL и
закрыл timing; польза на живом RF ещё не измерена.**
