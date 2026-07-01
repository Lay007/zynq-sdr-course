// Lab 5.10b - deterministic QPSK BER counter
//
// Compares the recovered Gray dibits against the same ROM image the dibit source
// used (bpsk_frame_bits.mem, two bits per symbol) and counts BIT errors. Fixed
// alignment: the caller sets start_offset so the RX sampler emits symbol 0 first
// (adequate for the ideal loopback simulation; the hardware bridge adds the
// preamble frame-sync of bpsk_ber_counter).

`timescale 1ns/1ps

module qpsk_ber_counter #(
    parameter integer INDEX_W = 16,
    parameter integer MAX_FRAME_BITS = 512,
    parameter MEM_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem"
) (
    input  wire                     clk,
    input  wire                     rst,
    input  wire                     start,
    input  wire                     abort,
    input  wire [INDEX_W-1:0]       symbol_count,   // QPSK symbols
    input  wire                     in_valid,
    input  wire [1:0]               in_dibit,
    output reg                      busy,
    output reg                      done,
    output reg [INDEX_W-1:0]        received_symbols,
    output reg [INDEX_W-1:0]        total_bit_errors
);

reg [0:0] frame_bits [0:MAX_FRAME_BITS-1];
reg [INDEX_W-1:0] frame_limit_reg = {INDEX_W{1'b0}};
integer idx;

wire [1:0] expected_dibit = {frame_bits[{received_symbols, 1'b1}],
                             frame_bits[{received_symbols, 1'b0}]};
wire [1:0] err_bits = in_dibit ^ expected_dibit;
wire [1:0] err_count = {1'b0, err_bits[0]} + {1'b0, err_bits[1]};

initial begin
    for (idx = 0; idx < MAX_FRAME_BITS; idx = idx + 1) begin
        frame_bits[idx] = 1'b0;
    end
    $readmemh(MEM_FILE, frame_bits);
end

always @(posedge clk) begin
    if (rst) begin
        busy <= 1'b0;
        done <= 1'b0;
        received_symbols <= {INDEX_W{1'b0}};
        total_bit_errors <= {INDEX_W{1'b0}};
        frame_limit_reg <= {INDEX_W{1'b0}};
    end else begin
        done <= 1'b0;

        if (start && !busy && (symbol_count != 0)) begin
            busy <= 1'b1;
            received_symbols <= {INDEX_W{1'b0}};
            total_bit_errors <= {INDEX_W{1'b0}};
            frame_limit_reg <= symbol_count;
        end else if (busy && abort) begin
            busy <= 1'b0;
            done <= 1'b1;
        end else if (busy && in_valid) begin
            total_bit_errors <= total_bit_errors + {{(INDEX_W-2){1'b0}}, err_count};
            if (received_symbols == frame_limit_reg - 1'b1) begin
                received_symbols <= frame_limit_reg;
                busy <= 1'b0;
                done <= 1'b1;
            end else begin
                received_symbols <= received_symbols + 1'b1;
            end
        end
    end
end

endmodule
