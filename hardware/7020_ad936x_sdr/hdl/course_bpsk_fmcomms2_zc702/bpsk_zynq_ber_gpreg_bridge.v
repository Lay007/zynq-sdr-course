// Course-specific AD9361 sample-domain bridge for the deterministic BPSK core.
//
// Control words arrive from the PS-side axi_gpreg block on sys_cpu_clk.
// The modem itself runs on the divided AD9361 sample clock, so this bridge
// captures quasi-static configuration words, generates a one-shot start pulse,
// and returns stable status/counter snapshots back to the PS clock domain.

`timescale 1ns/1ps

module bpsk_zynq_ber_gpreg_bridge #(
    parameter integer W = 16,
    parameter integer SPS = 8,
    parameter integer INDEX_W = 16,
    parameter integer MAX_FRAME_BITS = 512,
    parameter integer PHASE_W = 3,
    parameter integer FLUSH_SYMBOLS = 16,
    parameter MEM_FILE = "bpsk_frame_bits.mem",
    parameter COEF_FILE = "bpsk_rrc_tx_fir_taps.mem"
) (
    input  wire                     ctrl_clk,
    input  wire                     ctrl_resetn,
    input  wire                     sample_clk,
    input  wire                     sample_resetn,
    input  wire [31:0]              gp_ctrl,
    input  wire [31:0]              gp_frame_bit_count,
    input  wire [31:0]              gp_preamble_count,
    input  wire [31:0]              gp_start_offset,
    output wire [31:0]              gp_status,
    output wire [31:0]              gp_received_bits,
    output wire [31:0]              gp_total_errors,
    output wire [31:0]              gp_payload_errors,
    output wire [31:0]              gp_signature,
    output wire                     tx_valid,
    output wire signed [W-1:0]      tx_i,
    output wire signed [W-1:0]      tx_q,
    input  wire                     rx_valid,
    input  wire signed [W-1:0]      rx_i,
    input  wire signed [W-1:0]      rx_q
);

localparam [31:0] SIGNATURE = 32'h4250534B; // "BPSK"

wire sample_rst = ~sample_resetn;
wire core_busy;
wire core_done;
wire [INDEX_W-1:0] received_bits;
wire [INDEX_W-1:0] total_errors;
wire [INDEX_W-1:0] payload_errors;

reg [31:0] control_meta = 32'd0;
reg [31:0] control_sync = 32'd0;
reg [31:0] control_sync_d = 32'd0;
reg [31:0] frame_meta = 32'd0;
reg [31:0] frame_sync = 32'd0;
reg [31:0] preamble_meta = 32'd0;
reg [31:0] preamble_sync = 32'd0;
reg [31:0] offset_meta = 32'd0;
reg [31:0] offset_sync = 32'd0;

reg [INDEX_W-1:0] frame_bit_count_cfg = {INDEX_W{1'b0}};
reg [INDEX_W-1:0] preamble_count_cfg = {INDEX_W{1'b0}};
reg [INDEX_W-1:0] start_offset_cfg = {INDEX_W{1'b0}};
reg done_sticky_sample = 1'b0;
reg [INDEX_W-1:0] received_bits_sample = {INDEX_W{1'b0}};
reg [INDEX_W-1:0] total_errors_sample = {INDEX_W{1'b0}};
reg [INDEX_W-1:0] payload_errors_sample = {INDEX_W{1'b0}};

reg [31:0] status_meta_ctrl = 32'd0;
reg [31:0] status_sync_ctrl = 32'd0;
reg [31:0] received_meta_ctrl = 32'd0;
reg [31:0] received_sync_ctrl = 32'd0;
reg [31:0] total_meta_ctrl = 32'd0;
reg [31:0] total_sync_ctrl = 32'd0;
reg [31:0] payload_meta_ctrl = 32'd0;
reg [31:0] payload_sync_ctrl = 32'd0;

wire start_edge = control_sync[0] && !control_sync_d[0];
wire clear_done_edge = control_sync[1] && !control_sync_d[1];

bpsk_zynq_ber_top #(
    .W(W),
    .SPS(SPS),
    .INDEX_W(INDEX_W),
    .MAX_FRAME_BITS(MAX_FRAME_BITS),
    .PHASE_W(PHASE_W),
    .FLUSH_SYMBOLS(FLUSH_SYMBOLS),
    .MEM_FILE(MEM_FILE),
    .COEF_FILE(COEF_FILE)
) core_i (
    .clk(sample_clk),
    .rst(sample_rst),
    .start(start_edge),
    .frame_bit_count(frame_bit_count_cfg),
    .preamble_count(preamble_count_cfg),
    .start_offset(start_offset_cfg),
    .busy(core_busy),
    .done(core_done),
    .tx_valid(tx_valid),
    .tx_i(tx_i),
    .tx_q(tx_q),
    .rx_valid(rx_valid),
    .rx_i(rx_i),
    .rx_q(rx_q),
    .received_bits(received_bits),
    .total_errors(total_errors),
    .payload_errors(payload_errors)
);

always @(posedge sample_clk) begin
    if (!sample_resetn) begin
        control_meta <= 32'd0;
        control_sync <= 32'd0;
        control_sync_d <= 32'd0;
        frame_meta <= 32'd0;
        frame_sync <= 32'd0;
        preamble_meta <= 32'd0;
        preamble_sync <= 32'd0;
        offset_meta <= 32'd0;
        offset_sync <= 32'd0;
        frame_bit_count_cfg <= {INDEX_W{1'b0}};
        preamble_count_cfg <= {INDEX_W{1'b0}};
        start_offset_cfg <= {INDEX_W{1'b0}};
        done_sticky_sample <= 1'b0;
        received_bits_sample <= {INDEX_W{1'b0}};
        total_errors_sample <= {INDEX_W{1'b0}};
        payload_errors_sample <= {INDEX_W{1'b0}};
    end else begin
        control_meta <= gp_ctrl;
        control_sync <= control_meta;
        control_sync_d <= control_sync;
        frame_meta <= gp_frame_bit_count;
        frame_sync <= frame_meta;
        preamble_meta <= gp_preamble_count;
        preamble_sync <= preamble_meta;
        offset_meta <= gp_start_offset;
        offset_sync <= offset_meta;

        if (start_edge) begin
            frame_bit_count_cfg <= frame_sync[INDEX_W-1:0];
            preamble_count_cfg <= preamble_sync[INDEX_W-1:0];
            start_offset_cfg <= offset_sync[INDEX_W-1:0];
            done_sticky_sample <= 1'b0;
            received_bits_sample <= {INDEX_W{1'b0}};
            total_errors_sample <= {INDEX_W{1'b0}};
            payload_errors_sample <= {INDEX_W{1'b0}};
        end else if (clear_done_edge) begin
            done_sticky_sample <= 1'b0;
        end

        if (core_done) begin
            done_sticky_sample <= 1'b1;
            received_bits_sample <= received_bits;
            total_errors_sample <= total_errors;
            payload_errors_sample <= payload_errors;
        end
    end
end

always @(posedge ctrl_clk) begin
    if (!ctrl_resetn) begin
        status_meta_ctrl <= 32'd0;
        status_sync_ctrl <= 32'd0;
        received_meta_ctrl <= 32'd0;
        received_sync_ctrl <= 32'd0;
        total_meta_ctrl <= 32'd0;
        total_sync_ctrl <= 32'd0;
        payload_meta_ctrl <= 32'd0;
        payload_sync_ctrl <= 32'd0;
    end else begin
        status_meta_ctrl <= {16'd0, SPS[7:0], 5'd0, done_sticky_sample, core_busy, control_sync[0]};
        status_sync_ctrl <= status_meta_ctrl;
        received_meta_ctrl <= {{(32-INDEX_W){1'b0}}, received_bits_sample};
        received_sync_ctrl <= received_meta_ctrl;
        total_meta_ctrl <= {{(32-INDEX_W){1'b0}}, total_errors_sample};
        total_sync_ctrl <= total_meta_ctrl;
        payload_meta_ctrl <= {{(32-INDEX_W){1'b0}}, payload_errors_sample};
        payload_sync_ctrl <= payload_meta_ctrl;
    end
end

assign gp_status = status_sync_ctrl;
assign gp_received_bits = received_sync_ctrl;
assign gp_total_errors = total_sync_ctrl;
assign gp_payload_errors = payload_sync_ctrl;
assign gp_signature = SIGNATURE;

endmodule
