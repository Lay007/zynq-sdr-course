# Lab 5.1 HDL simulation package

This package contains the first executable HDL example for Block 5.

## Files

| File | Purpose |
|---|---|
| `rtl/iq_passthrough.v` | valid-only IQ streaming pass-through block |
| `tb/tb_iq_passthrough.v` | self-checking Verilog testbench |
| `tb/iq_passthrough_vectors.txt` | documented input vector format |

## Local simulation

Install Icarus Verilog:

```bash
sudo apt-get update
sudo apt-get install -y iverilog
```

Run simulation from repository root:

```bash
iverilog -g2012 \
  -o blocks/block_05_fpga_hdl_flow/tb/tb_iq_passthrough.out \
  blocks/block_05_fpga_hdl_flow/rtl/iq_passthrough.v \
  blocks/block_05_fpga_hdl_flow/tb/tb_iq_passthrough.v

vvp blocks/block_05_fpga_hdl_flow/tb/tb_iq_passthrough.out
```

Expected output:

```text
PASS: iq_passthrough test completed without errors
```

The simulation also produces:

```text
tb_iq_passthrough.vcd
```

You can inspect it with GTKWave:

```bash
gtkwave tb_iq_passthrough.vcd
```

## Engineering meaning

This lab validates the basic HDL contract used later for FIR, mixer and decimator blocks:

- reset drives outputs to a known state;
- `in_valid` is propagated to `out_valid`;
- I/Q samples preserve signed values;
- the block has deterministic one-clock latency;
- the testbench fails automatically if alignment is wrong.

## Next extension

Replace the pass-through datapath with:

1. a one-tap gain block;
2. a two-tap FIR;
3. the fixed-point FIR from Block 4;
4. a complex mixer with NCO.
