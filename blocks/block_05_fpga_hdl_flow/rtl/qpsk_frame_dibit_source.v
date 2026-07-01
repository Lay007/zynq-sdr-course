// Lab 5.10b - framed QPSK dibit source from a deterministic ROM image
//
// QPSK carries 2 bits/symbol, so this reads the SAME bit ROM as the BPSK source
// (bpsk_frame_bits.mem) but two bits at a time: dibit k = {bit[2k+1], bit[2k]},
// i.e. bit[2k] -> I axis (dibit[0]), bit[2k+1] -> Q axis (dibit[1]). One
// ready/valid/last dibit stream per start pulse.

`timescale 1ns/1ps

module qpsk_frame_dibit_source #(
    parameter integer INDEX_W = 16,
    parameter integer MAX_FRAME_BITS = 512,
    parameter MEM_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem"
) (
    input  wire                     clk,
    input  wire                     rst,
    input  wire                     start,
    input  wire [INDEX_W-1:0]       symbol_count,   // number of QPSK symbols (dibits)
    input  wire                     out_ready,
    output wire                     out_valid,
    output wire [1:0]               out_dibit,
    output wire                     out_last,
    output reg                      busy,
    output reg                      done
);

reg [0:0] frame_bits [0:MAX_FRAME_BITS-1];
reg [INDEX_W-1:0] sym_index = {INDEX_W{1'b0}};
integer idx;

assign out_valid = busy;
assign out_dibit = {frame_bits[{sym_index, 1'b1}], frame_bits[{sym_index, 1'b0}]};
assign out_last  = busy && (sym_index == symbol_count - 1'b1);

initial begin
    for (idx = 0; idx < MAX_FRAME_BITS; idx = idx + 1) begin
        frame_bits[idx] = 1'b0;
    end
    $readmemh(MEM_FILE, frame_bits);
end

always @(posedge clk) begin
    if (rst) begin
        sym_index <= {INDEX_W{1'b0}};
        busy <= 1'b0;
        done <= 1'b0;
    end else begin
        done <= 1'b0;

        if (start && !busy && (symbol_count != 0)) begin
            sym_index <= {INDEX_W{1'b0}};
            busy <= 1'b1;
        end else if (busy && out_ready) begin
            if (sym_index == symbol_count - 1'b1) begin
                sym_index <= {INDEX_W{1'b0}};
                busy <= 1'b0;
                done <= 1'b1;
            end else begin
                sym_index <= sym_index + 1'b1;
            end
        end
    end
end

endmodule
