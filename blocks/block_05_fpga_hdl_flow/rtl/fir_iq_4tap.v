// Lab 5.2 — 4-tap IQ FIR streaming block
//
// Educational fixed-point FIR block for complex IQ samples.
// Coefficients use Q1.15 format. Input and output samples are signed Q1.15.
// The example uses a simple symmetric 4-tap low-pass-like filter:
//   h = [0.125, 0.375, 0.375, 0.125]
// represented as Q1.15 coefficients.
//
// Latency model:
//   output at clock n corresponds to the FIR result for the input accepted
//   at the same clock edge, using the updated shift register state. out_valid
//   follows in_valid after one registered cycle.

`timescale 1ns/1ps

module fir_iq_4tap #(
    parameter integer W = 16,
    parameter integer CW = 16,
    parameter integer ACC_W = 40,
    parameter integer SHIFT = 15
)(
    input  wire                 clk,
    input  wire                 rst,

    input  wire                 in_valid,
    input  wire signed [W-1:0]  in_i,
    input  wire signed [W-1:0]  in_q,

    output reg                  out_valid,
    output reg  signed [W-1:0]  out_i,
    output reg  signed [W-1:0]  out_q
);

localparam signed [CW-1:0] H0 = 16'sd4096;   // 0.125 * 2^15
localparam signed [CW-1:0] H1 = 16'sd12288;  // 0.375 * 2^15
localparam signed [CW-1:0] H2 = 16'sd12288;  // 0.375 * 2^15
localparam signed [CW-1:0] H3 = 16'sd4096;   // 0.125 * 2^15

reg signed [W-1:0] xi0, xi1, xi2, xi3;
reg signed [W-1:0] xq0, xq1, xq2, xq3;

reg signed [ACC_W-1:0] acc_i;
reg signed [ACC_W-1:0] acc_q;
reg signed [ACC_W-1:0] rounded_i;
reg signed [ACC_W-1:0] rounded_q;

function signed [W-1:0] sat_q15;
    input signed [ACC_W-1:0] value;
    begin
        if (value > 32767)
            sat_q15 = 16'sd32767;
        else if (value < -32768)
            sat_q15 = -16'sd32768;
        else
            sat_q15 = value[W-1:0];
    end
endfunction

always @(posedge clk) begin
    if (rst) begin
        xi0 <= 0; xi1 <= 0; xi2 <= 0; xi3 <= 0;
        xq0 <= 0; xq1 <= 0; xq2 <= 0; xq3 <= 0;
        out_valid <= 1'b0;
        out_i <= 0;
        out_q <= 0;
        acc_i <= 0;
        acc_q <= 0;
        rounded_i <= 0;
        rounded_q <= 0;
    end else begin
        out_valid <= in_valid;

        if (in_valid) begin
            xi3 <= xi2;
            xi2 <= xi1;
            xi1 <= xi0;
            xi0 <= in_i;

            xq3 <= xq2;
            xq2 <= xq1;
            xq1 <= xq0;
            xq0 <= in_q;

            acc_i = $signed(in_i) * H0
                  + $signed(xi0) * H1
                  + $signed(xi1) * H2
                  + $signed(xi2) * H3;

            acc_q = $signed(in_q) * H0
                  + $signed(xq0) * H1
                  + $signed(xq1) * H2
                  + $signed(xq2) * H3;

            // Round half up before returning to Q1.15.
            rounded_i = (acc_i + ({{(ACC_W-1){1'b0}}, 1'b1} << (SHIFT-1))) >>> SHIFT;
            rounded_q = (acc_q + ({{(ACC_W-1){1'b0}}, 1'b1} << (SHIFT-1))) >>> SHIFT;

            out_i <= sat_q15(rounded_i);
            out_q <= sat_q15(rounded_q);
        end
    end
end

endmodule
