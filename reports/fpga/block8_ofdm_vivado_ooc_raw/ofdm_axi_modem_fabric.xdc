create_clock -name clk -period 10.000 [get_ports aclk]
set_property HD.CLK_SRC BUFGCTRL_X0Y0 [get_ports aclk]
set_input_delay -clock clk 0.000 [get_ports -filter {DIRECTION == IN && NAME != aclk}]
set_output_delay -clock clk 0.000 [get_ports -filter {DIRECTION == OUT}]
