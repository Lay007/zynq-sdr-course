// Lab 11.49 - dibit source for one message burst (issue #55)
//
// The ROM source (qpsk_frame_dibit_source) sends the fixed course frame. This one sends a frame
// that carries a message: the same 48-bit preamble from the frame ROM, then the 256 packet bits
// that the PS/PL mailbox put on msg_bits (packet-v1, already PN9-whitened, bit i of the packet in
// msg_bits[i]). In front of the frame it puts the burst head of Lab 11.48, as info dibits for the
// differential encoder: one dibit 00 (increment 0, phase state 0) and LEAD_FLIPS dibits 11
// (increment 2, a 180-degree flip each). With an even LEAD_FLIPS the last flip lands on state 0,
// the encoder's starting state, so it is the reference symbol, and the flips before it are the
// training lead-in that lets the receiver's loops settle before the preamble.
//
// Dibit k of the frame part is {bit[2k+1], bit[2k]}, as in the ROM source.

`timescale 1ns/1ps

module qpsk_message_dibit_source #(
    parameter integer LEAD_FLIPS = 64,   // 32 was enough after short pauses; 64 after long ones (Lab 11.49)
    parameter integer PRE_DIBITS = 24,
    parameter integer MSG_DIBITS = 128,
    parameter integer MAX_FRAME_BITS = 512,
    parameter MEM_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem"
) (
    input  wire                         clk,
    input  wire                         rst,
    input  wire                         start,
    input  wire [2*MSG_DIBITS-1:0]      msg_bits,
    input  wire                         out_ready,
    output wire                         out_valid,
    output reg  [1:0]                   out_dibit,
    output wire                         out_last,
    output reg                          busy,
    output reg                          done
);

localparam integer HEAD = 1 + LEAD_FLIPS;
localparam integer TOTAL = HEAD + PRE_DIBITS + MSG_DIBITS;

reg [0:0] frame_bits [0:MAX_FRAME_BITS-1];
reg [15:0] k = 16'd0;
integer idx;

initial begin
    for (idx = 0; idx < MAX_FRAME_BITS; idx = idx + 1) begin
        frame_bits[idx] = 1'b0;
    end
    $readmemh(MEM_FILE, frame_bits);
end

wire [15:0] kp = k - HEAD;                 // index into preamble + message
wire [15:0] km = k - HEAD - PRE_DIBITS;    // index into the message
always @(*) begin
    if (k == 16'd0)
        out_dibit = 2'b00;
    else if (k < HEAD)
        out_dibit = 2'b11;
    else if (kp < PRE_DIBITS)
        out_dibit = {frame_bits[{kp, 1'b1}], frame_bits[{kp, 1'b0}]};
    else
        out_dibit = {msg_bits[2*km + 1], msg_bits[2*km]};
end

assign out_valid = busy;
assign out_last = busy && (k == TOTAL - 1);

always @(posedge clk) begin
    if (rst) begin
        k <= 16'd0;
        busy <= 1'b0;
        done <= 1'b0;
    end else begin
        done <= 1'b0;
        if (start && !busy) begin
            k <= 16'd0;
            busy <= 1'b1;
        end else if (busy && out_ready) begin
            if (k == TOTAL - 1) begin
                k <= 16'd0;
                busy <= 1'b0;
                done <= 1'b1;
            end else begin
                k <= k + 1'b1;
            end
        end
    end
end

endmodule
