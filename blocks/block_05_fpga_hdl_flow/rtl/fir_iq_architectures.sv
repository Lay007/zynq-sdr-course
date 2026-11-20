`timescale 1ns/1ps

// Three schedules for the same four-tap complex FIR. Coefficients remain
// stable from reset through the last result. The sink takes every valid result.
module fir_iq_architectures #(
    parameter integer ARCH = 0  // 0: parallel, 1: folded, 2: pipelined
) (
    input wire clk, rst, in_valid,
    output wire in_ready,
    input wire signed [15:0] in_i, in_q,
    input wire signed [15:0] h0, h1, h2, h3,
    output reg out_valid,
    output reg signed [15:0] out_i, out_q
);
    wire accept = in_valid && in_ready;
    wire signed [15:0] samples_i [0:3];
    wire signed [15:0] samples_q [0:3];
    wire signed [15:0] taps [0:3];
    assign {taps[0], taps[1], taps[2], taps[3]} = {h0, h1, h2, h3};
    assign samples_i[0] = in_i;
    assign samples_q[0] = in_q;

    for (genvar tap = 1; tap < 4; tap = tap + 1) begin : history
        reg signed [15:0] delay_i, delay_q;
        always @(posedge clk) begin
            if (rst) begin
                delay_i <= 0;
                delay_q <= 0;
            end else if (accept) begin
                delay_i <= samples_i[tap-1];
                delay_q <= samples_q[tap-1];
            end
        end
        assign samples_i[tap] = delay_i;
        assign samples_q[tap] = delay_q;
    end

    function automatic signed [15:0] quantize(input signed [33:0] sum);
        // Four signed 16x16 products can sum to +2**32. Round once.
        reg signed [33:0] rounded;
        begin
            rounded = (sum + 34'sd16384) >>> 15;
            if (rounded > 32767)
                quantize = 16'sh7fff;
            else if (rounded < -32768)
                quantize = 16'sh8000;
            else
                quantize = rounded[15:0];
        end
    endfunction

    if (ARCH == 1) begin : folded
        reg busy;
        reg [1:0] tap_index;
        reg signed [33:0] acc_i, acc_q;
        reg signed [15:0] oldest_i, oldest_q;
        reg signed [15:0] operand_i, operand_q;
        wire signed [31:0] product_i = operand_i * taps[tap_index];
        wire signed [31:0] product_q = operand_q * taps[tap_index];
        wire signed [33:0] next_i = acc_i + product_i;
        wire signed [33:0] next_q = acc_q + product_q;
        assign in_ready = !rst && !busy;

        // On acceptance the history shifts and keeps the first three operands.
        // Save the displaced oldest sample for the fourth MAC cycle.
        always @* begin
            case (tap_index)
                0: begin operand_i = samples_i[1]; operand_q = samples_q[1]; end
                1: begin operand_i = samples_i[2]; operand_q = samples_q[2]; end
                2: begin operand_i = samples_i[3]; operand_q = samples_q[3]; end
                3: begin operand_i = oldest_i; operand_q = oldest_q; end
            endcase
        end

        always @(posedge clk) begin
            if (rst) begin
                busy <= 0;
                tap_index <= 0;
                acc_i <= 0;
                acc_q <= 0;
                oldest_i <= 0;
                oldest_q <= 0;
                out_valid <= 0;
                out_i <= 0;
                out_q <= 0;
            end else begin
                out_valid <= 0;
                if (accept) begin
                    busy <= 1;
                    tap_index <= 0;
                    acc_i <= 0;
                    acc_q <= 0;
                    oldest_i <= samples_i[3];
                    oldest_q <= samples_q[3];
                end else if (busy) begin
                    if (tap_index == 3) begin
                        busy <= 0;
                        out_i <= quantize(next_i);
                        out_q <= quantize(next_q);
                        out_valid <= 1;
                    end else begin
                        tap_index <= tap_index + 1'b1;
                        acc_i <= next_i;
                        acc_q <= next_q;
                    end
                end
            end
        end
    end else begin : full_rate
        wire signed [31:0] products_i [0:3];
        wire signed [31:0] products_q [0:3];
        assign in_ready = !rst;
        for (genvar tap = 0; tap < 4; tap = tap + 1) begin : multiply
            wire signed [31:0] product_i = samples_i[tap] * taps[tap];
            wire signed [31:0] product_q = samples_q[tap] * taps[tap];
            if (ARCH == 2) begin : register_products
                reg signed [31:0] saved_i, saved_q;
                // Invalid pipeline data need no reset. Valid bits gate the result.
                always @(posedge clk) begin
                    saved_i <= product_i;
                    saved_q <= product_q;
                end
                assign products_i[tap] = saved_i;
                assign products_q[tap] = saved_q;
            end else begin : direct_products
                assign products_i[tap] = product_i;
                assign products_q[tap] = product_q;
            end
        end

        wire signed [32:0] pair01_i = products_i[0] + products_i[1];
        wire signed [32:0] pair23_i = products_i[2] + products_i[3];
        wire signed [32:0] pair01_q = products_q[0] + products_q[1];
        wire signed [32:0] pair23_q = products_q[2] + products_q[3];
        wire signed [33:0] sum_i, sum_q;
        wire result_valid;
        if (ARCH == 2) begin : pipeline
            reg valid_products, valid_pairs;
            reg signed [32:0] saved01_i, saved23_i, saved01_q, saved23_q;
            always @(posedge clk) begin
                valid_products <= !rst && accept;
                valid_pairs <= !rst && valid_products;
                saved01_i <= pair01_i;
                saved23_i <= pair23_i;
                saved01_q <= pair01_q;
                saved23_q <= pair23_q;
            end
            assign sum_i = saved01_i + saved23_i;
            assign sum_q = saved01_q + saved23_q;
            assign result_valid = valid_pairs;
        end else begin : direct_sum
            assign sum_i = pair01_i + pair23_i;
            assign sum_q = pair01_q + pair23_q;
            assign result_valid = accept;
        end

        always @(posedge clk) begin
            out_valid <= !rst && result_valid;
            if (rst) begin
                out_i <= 0;
                out_q <= 0;
            end else if (result_valid) begin
                out_i <= quantize(sum_i);
                out_q <= quantize(sum_q);
            end
        end
    end
endmodule
