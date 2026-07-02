module course_dac_fifo_source_mux #(
    parameter integer W = 16
) (
    input  wire               select_bpsk,
    input  wire [15:0]        vendor_data_0,
    input  wire [15:0]        vendor_data_1,
    input  wire [15:0]        vendor_data_2,
    input  wire [15:0]        vendor_data_3,
    input  wire               vendor_valid,
    input  wire               vendor_unf,
    input  wire [(2*W):0]     bpsk_tx_sample_bus,
    output wire [15:0]        fifo_data_0,
    output wire [15:0]        fifo_data_1,
    output wire [15:0]        fifo_data_2,
    output wire [15:0]        fifo_data_3,
    output wire               fifo_valid,
    output wire               fifo_unf
);

wire               bpsk_valid;
wire signed [W-1:0] bpsk_i;
wire signed [W-1:0] bpsk_q;

assign bpsk_valid = bpsk_tx_sample_bus[2*W];
assign bpsk_i = bpsk_tx_sample_bus[(2*W)-1:W];
assign bpsk_q = bpsk_tx_sample_bus[W-1:0];

// Broadcast the modem burst on BOTH TX channels (TX1 = data_0/1, TX2 = data_2/3)
// so the frame is available on the TX2 SMA too — lets the host test a TX2->RX2
// cable path (in case the TX1/RX1 channel/balun is degraded) without a re-route.
assign fifo_data_0 = select_bpsk ? bpsk_i[15:0] : vendor_data_0;
assign fifo_data_1 = select_bpsk ? bpsk_q[15:0] : vendor_data_1;
assign fifo_data_2 = select_bpsk ? bpsk_i[15:0] : vendor_data_2;
assign fifo_data_3 = select_bpsk ? bpsk_q[15:0] : vendor_data_3;
assign fifo_valid  = select_bpsk ? bpsk_valid   : vendor_valid;
assign fifo_unf    = select_bpsk ? 1'b0         : vendor_unf;

endmodule
