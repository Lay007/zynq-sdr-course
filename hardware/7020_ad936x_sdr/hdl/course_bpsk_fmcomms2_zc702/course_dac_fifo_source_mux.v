module course_dac_fifo_source_mux (
    input  wire        select_bpsk,
    input  wire [15:0] vendor_data_0,
    input  wire [15:0] vendor_data_1,
    input  wire [15:0] vendor_data_2,
    input  wire [15:0] vendor_data_3,
    input  wire        vendor_valid,
    input  wire        vendor_unf,
    input  wire [15:0] bpsk_data_0,
    input  wire [15:0] bpsk_data_1,
    input  wire [15:0] bpsk_data_2,
    input  wire [15:0] bpsk_data_3,
    input  wire        bpsk_valid,
    input  wire        bpsk_unf,
    output wire [15:0] fifo_data_0,
    output wire [15:0] fifo_data_1,
    output wire [15:0] fifo_data_2,
    output wire [15:0] fifo_data_3,
    output wire        fifo_valid,
    output wire        fifo_unf
);

assign fifo_data_0 = select_bpsk ? bpsk_data_0 : vendor_data_0;
assign fifo_data_1 = select_bpsk ? bpsk_data_1 : vendor_data_1;
assign fifo_data_2 = select_bpsk ? bpsk_data_2 : vendor_data_2;
assign fifo_data_3 = select_bpsk ? bpsk_data_3 : vendor_data_3;
assign fifo_valid  = select_bpsk ? bpsk_valid  : vendor_valid;
assign fifo_unf    = select_bpsk ? bpsk_unf    : vendor_unf;

endmodule
