// Lab 5.3 — Fixed-point NCO IQ mixer
//
// Educational Q1.15 complex mixer with a small phase accumulator and
// quarter-wave-free 16-entry sin/cos lookup table.
//
// This block is intentionally compact for simulation and teaching. A real SDR
// design normally uses a wider phase accumulator, larger LUT, interpolation or
// CORDIC, and explicit pipeline balancing.

`timescale 1ns/1ps

module nco_mixer_iq #(
    parameter integer W = 16,
    parameter integer PHASE_W = 4,
    parameter integer ACC_W = 40,
    parameter integer SHIFT = 15,
    parameter [PHASE_W-1:0] PHASE_INC = 4'd1
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

localparam signed [ACC_W-1:0] ROUND_BIAS = 40'sd1 <<< (SHIFT - 1);

reg [PHASE_W-1:0] phase;
reg signed [W-1:0] cos_q15;
reg signed [W-1:0] sin_q15;
reg signed [ACC_W-1:0] acc_i;
reg signed [ACC_W-1:0] acc_q;
reg signed [ACC_W-1:0] rounded_i;
reg signed [ACC_W-1:0] rounded_q;

function signed [W-1:0] sin_lut;
    input [PHASE_W-1:0] addr;
    begin
        case (addr)
            4'd0:  sin_lut =  16'sd0;
            4'd1:  sin_lut =  16'sd12540;
            4'd2:  sin_lut =  16'sd23170;
            4'd3:  sin_lut =  16'sd30274;
            4'd4:  sin_lut =  16'sd32767;
            4'd5:  sin_lut =  16'sd30274;
            4'd6:  sin_lut =  16'sd23170;
            4'd7:  sin_lut =  16'sd12540;
            4'd8:  sin_lut =  16'sd0;
            4'd9:  sin_lut = -16'sd12540;
            4'd10: sin_lut = -16'sd23170;
            4'd11: sin_lut = -16'sd30274;
            4'd12: sin_lut = -16'sd32768;
            4'd13: sin_lut = -16'sd30274;
            4'd14: sin_lut = -16'sd23170;
            4'd15: sin_lut = -16'sd12540;
            default: sin_lut = 16'sd0;
        endcase
    end
endfunction

function signed [W-1:0] cos_lut;
    input [PHASE_W-1:0] addr;
    begin
        cos_lut = sin_lut(addr + 4'd4);
    end
endfunction

function signed [ACC_W-1:0] round_q15;
    input signed [ACC_W-1:0] value;
    begin
        // Keep the expression signed. Without a signed bias, negative values can
        // be promoted to unsigned and then saturate incorrectly to +32767.
        round_q15 = (value + ROUND_BIAS) >>> SHIFT;
    end
endfunction

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
        phase <= {PHASE_W{1'b0}};
        out_valid <= 1'b0;
        out_i <= 0;
        out_q <= 0;
        cos_q15 <= 0;
        sin_q15 <= 0;
        acc_i <= 0;
        acc_q <= 0;
        rounded_i <= 0;
        rounded_q <= 0;
    end else begin
        out_valid <= in_valid;

        if (in_valid) begin
            cos_q15 = cos_lut(phase);
            sin_q15 = sin_lut(phase);

            // (I + jQ) * (cos + j sin)
            acc_i = $signed(in_i) * cos_q15 - $signed(in_q) * sin_q15;
            acc_q = $signed(in_i) * sin_q15 + $signed(in_q) * cos_q15;

            rounded_i = round_q15(acc_i);
            rounded_q = round_q15(acc_q);

            out_i <= sat_q15(rounded_i);
            out_q <= sat_q15(rounded_q);

            phase <= phase + PHASE_INC;
        end
    end
end

endmodule
