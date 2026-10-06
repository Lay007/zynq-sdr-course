`timescale 1ns/1ps

// ofdm_qam16_mapper and ofdm_qam16_demapper against tools/ofdm_qam16_fixed.py:
// every 4-bit code maps to the Gray levels, the mapped levels scaled to the
// equalized grid slice back to the same code, and the slicer behaves exactly
// at its thresholds (strict comparisons, 0 is positive and inner).
module tb_ofdm_qam16_mapper_demapper;
    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg resetn = 1'b0;
    reg valid_in = 1'b0;
    reg [3:0] bits_in = 4'd0;
    wire valid_out;
    wire signed [15:0] i_out, q_out;

    reg signed [15:0] sym_re = 16'sd0, sym_im = 16'sd0;
    wire [3:0] bits_out;
    wire bits_valid, symbol_ready, bits_last;
    wire [5:0] bits_index;

    integer errors = 0;
    integer code;
    integer exp_i, exp_q;

    ofdm_qam16_mapper mapper (
        .clk(clk), .resetn(resetn), .valid_in(valid_in), .bits_in(bits_in),
        .valid_out(valid_out), .i_out(i_out), .q_out(q_out)
    );

    ofdm_qam16_demapper demapper (
        .resetn(resetn), .symbol_valid(1'b1), .symbol_ready(symbol_ready),
        .symbol_re(sym_re), .symbol_im(sym_im), .data_index(6'd5), .symbol_last(1'b0),
        .bits_valid(bits_valid), .bits_ready(1'b1), .bits_out(bits_out),
        .bits_index(bits_index), .bits_last(bits_last)
    );

    function automatic integer level;
        input integer sign_bit;
        input integer inner_bit;
        begin
            level = inner_bit ? 10362 : 31086;
            if (sign_bit) level = -level;
        end
    endfunction

    task automatic check_slice;
        input integer re;
        input integer im;
        input [3:0] expected;
        begin
            sym_re = re;
            sym_im = im;
            #1;
            if (bits_out !== expected) begin
                $display("FAIL slice (%0d,%0d): got %b expected %b", re, im, bits_out, expected);
                errors = errors + 1;
            end
        end
    endtask

    initial begin
        repeat (2) @(posedge clk);
        resetn = 1'b1;
        for (code = 0; code < 16; code = code + 1) begin
            @(negedge clk);
            bits_in = code;
            valid_in = 1'b1;
            @(posedge clk);
            #1;
            exp_i = level(code[3], code[2]);
            exp_q = level(code[1], code[0]);
            if (!valid_out || $signed(i_out) !== exp_i || $signed(q_out) !== exp_q) begin
                $display("FAIL map %b: got (%0d,%0d) expected (%0d,%0d)", code[3:0], i_out, q_out, exp_i, exp_q);
                errors = errors + 1;
            end
            // The equalized grid: outer 8192, inner 2731.
            check_slice((exp_i > 0 ? 1 : -1) * ((exp_i == 10362 || exp_i == -10362) ? 2731 : 8192),
                        (exp_q > 0 ? 1 : -1) * ((exp_q == 10362 || exp_q == -10362) ? 2731 : 8192),
                        code[3:0]);
        end
        @(negedge clk);
        valid_in = 1'b0;

        // Thresholds: |c| < 5461 is inner; 0 is positive.
        check_slice(5460, -5460, 4'b0111);
        check_slice(5461, -5461, 4'b0010);
        check_slice(0, 0, 4'b0101);
        check_slice(-1, 1, 4'b1101);
        check_slice(32767, -32768, 4'b0010);

        if (errors == 0) begin
            $display("PASS: 16-QAM mapper and slicer match the model (16 codes, thresholds)");
            $finish;
        end else begin
            $display("FAIL tb_ofdm_qam16_mapper_demapper errors=%0d", errors);
            $fatal(1);
        end
    end
endmodule
