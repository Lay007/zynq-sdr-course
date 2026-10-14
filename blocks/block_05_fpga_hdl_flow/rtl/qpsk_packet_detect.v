// Packet detector for the listening QPSK receiver (issue #68)
//
// Between packets the receiver sees only noise. The timing and carrier loops would update on
// that noise and random-walk away from where the next packet needs them, so a receiver that
// waits for a packet must know when one is present. A fixed amplitude threshold does not work:
// the noise level depends on the RX gain (at 71 dB the board's noise alone passes the old
// |I|+|Q| >= 8 gate on almost every symbol). This block compares the symbol amplitude with the
// noise level it has seen:
//
//   a     = |I| + |Q| of each symbol
//   short = running mean of a over about 2^SHORT_LOG symbols
//   long  = running mean of a over about 2^LONG_LOG symbols (the noise level, since packets
//           are short compared to this window)
//   present = short > (THRESH_NUM / THRESH_DEN) * long
//
// Both means are exponential (acc += a - acc >> LOG). The first symbol after reset seeds the
// long mean, so the detector works from the start instead of waiting 2^LONG_LOG symbols. The
// parent resets this block only with the global reset, so the noise estimate is kept from one
// reception to the next, like the DC estimate (issue #66).

`timescale 1ns/1ps

module qpsk_packet_detect #(
    parameter integer W = 16,
    parameter integer SHORT_LOG = 3,
    parameter integer LONG_LOG = 12,
    parameter integer THRESH_NUM = 3,
    parameter integer THRESH_DEN = 2
) (
    input  wire                 clk,
    input  wire                 rst,
    input  wire                 in_valid,
    input  wire signed [W-1:0]  in_i,
    input  wire signed [W-1:0]  in_q,
    output reg                  present
);

localparam integer AW = W + 1;
localparam integer SW = AW + SHORT_LOG;
localparam integer LW = AW + LONG_LOG;
localparam integer CW = LW + 4;   // room for the THRESH_* products

wire [W-1:0] abs_i = in_i[W-1] ? (~in_i + 1'b1) : in_i;
wire [W-1:0] abs_q = in_q[W-1] ? (~in_q + 1'b1) : in_q;
wire [AW-1:0] a = {1'b0, abs_i} + {1'b0, abs_q};

reg [SW-1:0] short_acc = {SW{1'b0}};
reg [LW-1:0] long_acc = {LW{1'b0}};
reg          seeded = 1'b0;

wire [AW-1:0] short_mean = short_acc[SW-1:SHORT_LOG];
wire [AW-1:0] long_mean  = long_acc[LW-1:LONG_LOG];
wire [CW-1:0] short_scaled = short_mean * THRESH_DEN;
wire [CW-1:0] long_scaled  = long_mean * THRESH_NUM;

always @(posedge clk) begin
    if (rst) begin
        short_acc <= {SW{1'b0}};
        long_acc  <= {LW{1'b0}};
        seeded    <= 1'b0;
        present   <= 1'b0;
    end else if (in_valid) begin
        if (!seeded) begin
            short_acc <= {a, {SHORT_LOG{1'b0}}};
            long_acc  <= {a, {LONG_LOG{1'b0}}};
            seeded    <= 1'b1;
        end else begin
            short_acc <= short_acc + a - short_mean;
            long_acc  <= long_acc + a - long_mean;
        end
        present <= seeded && (short_scaled > long_scaled);
    end
end

endmodule
