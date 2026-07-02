// Lab 5.10b - deterministic QPSK BER counter WITH preamble frame-sync.
//
// QPSK is two independent BPSK axes: dibit[0] rides the I axis (frame bit 2s),
// dibit[1] the Q axis (frame bit 2s+1). Flattening each recovered dibit into the
// bit pair {dibit[0], dibit[1]} reproduces the frame ROM bit order, so we feed it
// straight into the proven `bpsk_ber_counter`, which brings a sliding preamble
// correlator (frame-sync, offset/loopback-latency independent) and 180-degree
// (invert) ambiguity handling. On a COHERENT link (shared LO ⇒ no CFO, small
// static phase kept near 0/180 since the BPSK I-axis decodes) that framesync +
// 180-degree resolve are exactly what QPSK was missing versus BPSK. A residual
// 90/270-degree rotation (I<->Q swap) is NOT covered here — if the hardware shows
// no lock, that is the tell to add a 4-rotation trial.
//
// Interface matches the original fixed-alignment counter plus a preamble length,
// with received_symbols/total_bit_errors derived from the underlying bit counts.

`timescale 1ns/1ps

module qpsk_ber_counter #(
    parameter integer INDEX_W = 16,
    parameter integer MAX_FRAME_BITS = 512,
    parameter integer LOCK_PREAMBLE_BITS = 8,
    parameter MEM_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem"
) (
    input  wire                     clk,
    input  wire                     rst,
    input  wire                     start,
    input  wire                     abort,
    input  wire [INDEX_W-1:0]       symbol_count,     // QPSK symbols
    input  wire [INDEX_W-1:0]       preamble_count,   // preamble length in BITS
    input  wire                     in_valid,
    input  wire [1:0]               in_dibit,
    output wire                     busy,
    output wire                     done,
    output reg  [INDEX_W-1:0]       received_symbols,
    output reg  [INDEX_W-1:0]       total_bit_errors
);

localparam [1:0] S_IDLE  = 2'd0;
localparam [1:0] S_EMIT0 = 2'd1;
localparam [1:0] S_EMIT1 = 2'd2;

// dibit -> serial bit flattener: emit {dibit[0], dibit[1]} so the stream matches
// the frame ROM (bit 2s = I = dibit[0], bit 2s+1 = Q = dibit[1]). Recovered
// symbols are >= SPS cycles apart, so the 2-cycle emit never overruns.
reg [1:0] flat_state = S_IDLE;
reg [1:0] dibit_lat = 2'd0;
reg       bit_valid = 1'b0;
reg       bit_in = 1'b0;

always @(posedge clk) begin
    if (rst || start) begin
        flat_state <= S_IDLE;
        bit_valid  <= 1'b0;
        bit_in     <= 1'b0;
    end else begin
        bit_valid <= 1'b0;
        case (flat_state)
            S_IDLE: begin
                if (in_valid) begin
                    dibit_lat <= in_dibit;
                    bit_in    <= in_dibit[0];
                    bit_valid <= 1'b1;
                    flat_state <= S_EMIT1;
                end
            end
            S_EMIT1: begin
                bit_in    <= dibit_lat[1];
                bit_valid <= 1'b1;
                flat_state <= S_IDLE;
            end
            default: flat_state <= S_IDLE;
        endcase
    end
end

wire [INDEX_W-1:0] frame_bit_count = symbol_count << 1;   // 2 bits per QPSK symbol
wire [INDEX_W-1:0] bpsk_received_bits;
wire [INDEX_W-1:0] bpsk_total_errors;
wire [INDEX_W-1:0] bpsk_payload_errors;

bpsk_ber_counter #(
    .INDEX_W(INDEX_W),
    .MAX_FRAME_BITS(MAX_FRAME_BITS),
    .LOCK_PREAMBLE_BITS(LOCK_PREAMBLE_BITS),
    .MEM_FILE(MEM_FILE)
) bit_ber_i (
    .clk(clk),
    .rst(rst),
    .start(start),
    .abort(abort),
    .frame_bit_count(frame_bit_count),
    .preamble_count(preamble_count),
    .in_valid(bit_valid),
    .in_bit(bit_in),
    .busy(busy),
    .done(done),
    .received_bits(bpsk_received_bits),
    .total_errors(bpsk_total_errors),
    .payload_errors(bpsk_payload_errors)
);

always @(*) begin
    received_symbols = bpsk_received_bits >> 1;   // 2 bits/symbol
    total_bit_errors = bpsk_total_errors;
end

endmodule
