// Lab 5.10 - deterministic BER counter against the shared Block 11 frame bits
//
// Reuses the same ROM image as the bit source and counts total/payload errors.

`timescale 1ns/1ps

module bpsk_ber_counter #(
    parameter integer INDEX_W = 16,
    parameter integer MAX_FRAME_BITS = 512,
    parameter MEM_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem"
) (
    input  wire                     clk,
    input  wire                     rst,
    input  wire                     start,
    input  wire [INDEX_W-1:0]       frame_bit_count,
    input  wire [INDEX_W-1:0]       preamble_count,
    input  wire                     in_valid,
    input  wire                     in_bit,
    output reg                      busy,
    output reg                      done,
    output reg [INDEX_W-1:0]        received_bits,
    output reg [INDEX_W-1:0]        total_errors,
    output reg [INDEX_W-1:0]        payload_errors
);

reg [0:0] frame_bits [0:MAX_FRAME_BITS-1];
integer idx;

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
        received_bits <= {INDEX_W{1'b0}};
        total_errors <= {INDEX_W{1'b0}};
        payload_errors <= {INDEX_W{1'b0}};
    end else begin
        done <= 1'b0;

        if (start && !busy && (frame_bit_count != 0)) begin
            busy <= 1'b1;
            received_bits <= {INDEX_W{1'b0}};
            total_errors <= {INDEX_W{1'b0}};
            payload_errors <= {INDEX_W{1'b0}};
        end else if (busy && in_valid) begin
            if (in_bit !== frame_bits[received_bits]) begin
                total_errors <= total_errors + 1'b1;
                if (received_bits >= preamble_count) begin
                    payload_errors <= payload_errors + 1'b1;
                end
            end

            if (received_bits == frame_bit_count - 1'b1) begin
                received_bits <= frame_bit_count;
                busy <= 1'b0;
                done <= 1'b1;
            end else begin
                received_bits <= received_bits + 1'b1;
            end
        end
    end
end

endmodule
