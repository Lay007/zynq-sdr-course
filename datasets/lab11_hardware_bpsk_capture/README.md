# Board PL RX BPSK capture (AD9361 digital loopback)

`board_pl_rx_loopback_capture.npz` — real samples the Zynq-7020 PL BPSK receiver saw during
one burst, read back from the in-fabric debug tap (Block 11) in AD9361 digital loopback.

- `i`, `q` — `capture_in_i/q`, signed ADC counts, sample rate 3.84 MHz, SPS = 8 (BPSK, so
  `q ≈ 0`). 2400 samples covering the 281-symbol frame plus RRC tails.
- `tx_i`, `tx_q` — the core's recovered decision sample (`symbol_i_debug`) captured in the
  same run; not used by the figure script.

Used by [Lab 8.7](../../blocks/block_08_modulation_and_synchronization/lab_8_7_real_hardware_bpsk_metrics.md)
to plot the real spectrum + constellation and measure SNR/EVM (≈ 36 dB / 1.6 %). Regenerate
the figure:

```bash
python blocks/block_08_modulation_and_synchronization/python/hardware_bpsk_spectrum_constellation.py \
    --board datasets/lab11_hardware_bpsk_capture/board_pl_rx_loopback_capture.npz
```
