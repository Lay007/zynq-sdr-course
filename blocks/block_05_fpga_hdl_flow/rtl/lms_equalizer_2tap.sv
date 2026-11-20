`timescale 1ns/1ps

// Real, symbol-rate LMS with a known training target and an always-ready sink.
// Inputs use signed Q1.15, weights Q2.14, and y keeps 15 fractional bits
// in 19 bits so the feedback error sees the full rounded dot product.
module lms_equalizer_2tap (
    input wire clk, rst, in_valid, train,
    input wire signed [15:0] sample, desired,
    output reg out_valid,
    output reg signed [18:0] y,
    output reg signed [15:0] w0, w1,
    output reg weight_clipped
);
    reg signed [15:0] previous_sample;
    wire signed [31:0] mac0 = w0 * sample;
    wire signed [31:0] mac1 = w1 * previous_sample;
    // The sum can reach +2**31. Widen the sum before rounding.
    wire signed [32:0] dot = mac0 + mac1;
    wire signed [32:0] dot_rounded = (dot + 33'sd8192) >>> 14;
    wire signed [18:0] estimate = dot_rounded[18:0];
    wire signed [18:0] error = $signed(desired) - estimate;
    wire signed [34:0] grad0 = error * sample;
    wire signed [34:0] grad1 = error * previous_sample;
    // e*x has 30 fractional bits. Multiply by 1/16 and convert to Q2.14.
    wire signed [34:0] delta0 = (grad0 + 35'sd524288) >>> 20;
    wire signed [34:0] delta1 = (grad1 + 35'sd524288) >>> 20;
    wire signed [34:0] next0 = w0 + delta0;
    wire signed [34:0] next1 = w1 + delta1;

    function automatic outside_q14(input signed [34:0] value);
        outside_q14 = (value > 35'sd32767) || (value < -35'sd32768);
    endfunction

    function automatic signed [15:0] sat_q14(input signed [34:0] value);
        if (outside_q14(value))
            sat_q14 = value[34] ? 16'sh8000 : 16'sh7fff;
        else
            sat_q14 = value[15:0];
    endfunction

    always @(posedge clk) begin
        if (rst) begin
            previous_sample <= 0;
            w0 <= 0;
            w1 <= 0;
            out_valid <= 0;
            y <= 0;
            weight_clipped <= 0;
        end else begin
            out_valid <= in_valid;
            weight_clipped <= 0;
            if (in_valid) begin
                y <= estimate;
                previous_sample <= sample;
                if (train) begin
                    w0 <= sat_q14(next0);
                    w1 <= sat_q14(next1);
                    weight_clipped <= outside_q14(next0) || outside_q14(next1);
                end
            end
        end
    end
endmodule
