// Lab 5.10 - framed BPSK bit source from a deterministic ROM image
//
// Generates one ready/valid/last BPSK bit stream per start pulse.

`timescale 1ns/1ps

module bpsk_frame_bit_source #(
    parameter integer INDEX_W = 16,
    parameter integer MAX_FRAME_BITS = 512,
    parameter MEM_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem"
) (
    input  wire                     clk,
    input  wire                     rst,
    input  wire                     start,
    input  wire [INDEX_W-1:0]       frame_bit_count,
    input  wire                     out_ready,
    output wire                     out_valid,
    output wire                     out_bit,
    output wire                     out_last,
    output reg                      busy,
    output reg                      done
);

reg [0:0] frame_bits [0:MAX_FRAME_BITS-1];
reg [INDEX_W-1:0] bit_index = {INDEX_W{1'b0}};
integer idx;

assign out_valid = busy;
assign out_bit = frame_bits[bit_index];
assign out_last = busy && (bit_index == frame_bit_count - 1'b1);

initial begin
    for (idx = 0; idx < MAX_FRAME_BITS; idx = idx + 1) begin
        frame_bits[idx] = 1'b0;
    end
    $readmemh(MEM_FILE, frame_bits);
end

always @(posedge clk) begin
    if (rst) begin
        bit_index <= {INDEX_W{1'b0}};
        busy <= 1'b0;
        done <= 1'b0;
    end else begin
        done <= 1'b0;

        if (start && !busy && (frame_bit_count != 0)) begin
            bit_index <= {INDEX_W{1'b0}};
            busy <= 1'b1;
        end else if (busy && out_ready) begin
            if (bit_index == frame_bit_count - 1'b1) begin
                bit_index <= {INDEX_W{1'b0}};
                busy <= 1'b0;
                done <= 1'b1;
            end else begin
                bit_index <= bit_index + 1'b1;
            end
        end
    end
end

endmodule
