`timescale 1ns/1ps

module tb_ofdm_one_tap_equalizer;
    reg clk = 1'b0;
    reg resetn = 1'b0;
    reg in_valid = 1'b0;
    wire in_ready;
    reg signed [15:0] in_re = 16'sd0;
    reg signed [15:0] in_im = 16'sd0;
    reg signed [15:0] coeff_re = 16'sd0;
    reg signed [15:0] coeff_im = 16'sd0;
    reg [5:0] in_index = 6'd0;
    reg in_last = 1'b0;

    wire out_valid;
    reg out_ready = 1'b1;
    wire signed [15:0] out_re;
    wire signed [15:0] out_im;
    wire [5:0] out_index;
    wire out_last;
    wire [31:0] saturation_count;

    integer errors = 0;
    integer held_re;
    integer held_im;
    integer held_index;

    ofdm_one_tap_equalizer dut (
        .clk(clk), .resetn(resetn),
        .in_valid(in_valid), .in_ready(in_ready),
        .in_re(in_re), .in_im(in_im),
        .coeff_re(coeff_re), .coeff_im(coeff_im),
        .in_index(in_index), .in_last(in_last),
        .out_valid(out_valid), .out_ready(out_ready),
        .out_re(out_re), .out_im(out_im),
        .out_index(out_index), .out_last(out_last),
        .saturation_count(saturation_count)
    );

    always #5 clk = ~clk;

    task automatic expect_int;
        input integer actual;
        input integer expected;
        input [8*48-1:0] label_text;
        begin
            if (actual !== expected) begin
                $display("FAIL %-40s actual=%0d expected=%0d", label_text, actual, expected);
                errors = errors + 1;
            end
        end
    endtask

    task automatic apply_sample;
        input signed [15:0] sample_re;
        input signed [15:0] sample_im;
        input signed [15:0] tap_re;
        input signed [15:0] tap_im;
        input [5:0] sample_index;
        input sample_last;
        input integer expected_re;
        input integer expected_im;
        begin
            @(negedge clk);
            in_valid = 1'b1;
            in_re = sample_re;
            in_im = sample_im;
            coeff_re = tap_re;
            coeff_im = tap_im;
            in_index = sample_index;
            in_last = sample_last;
            if (!in_ready) begin
                $display("FAIL equalizer unexpectedly not ready");
                errors = errors + 1;
            end
            @(posedge clk);
            #1;
            if (!out_valid) begin
                $display("FAIL equalizer output not valid");
                errors = errors + 1;
            end
            expect_int($signed(out_re), expected_re, "equalized real");
            expect_int($signed(out_im), expected_im, "equalized imag");
            expect_int(out_index, sample_index, "metadata index");
            expect_int(out_last, sample_last, "metadata last");
            @(negedge clk);
            in_valid = 1'b0;
            @(posedge clk);
            #1;
        end
    endtask

    initial begin
        repeat (2) @(posedge clk);
        #1;
        expect_int(out_valid, 0, "reset clears output valid");
        expect_int(saturation_count, 0, "reset clears saturation count");

        @(negedge clk);
        resetn = 1'b1;

        // Q2.14 coefficient 1.0 + j0: exact identity for these integers.
        apply_sample(16'sd10000, -16'sd7000,
                     16'sd16384, 16'sd0,
                     6'd4, 1'b0, 10000, -7000);

        // Input is the reference symbol rotated by +90 degrees. Multiplying by
        // -j must recover the original 10000 + j5000 sample exactly.
        apply_sample(-16'sd5000, 16'sd10000,
                     16'sd0, -16'sd16384,
                     6'd17, 1'b0, 10000, 5000);

        // A gain > 1 demonstrates why correction coefficients use Q2.14.
        apply_sample(16'sd10000, -16'sd8000,
                     16'sd24576, 16'sd0,
                     6'd31, 1'b0, 15000, -12000);

        // Both components clip at gain 1.5; diagnostics must count both.
        apply_sample(16'sd25000, 16'sd25000,
                     16'sd24576, 16'sd0,
                     6'd47, 1'b1, 32767, 32767);
        expect_int(saturation_count, 2, "two clipped components counted");

        // Backpressure must hold the complete output record stable.
        @(negedge clk);
        out_ready = 1'b0;
        in_valid = 1'b1;
        in_re = -16'sd6000;
        in_im = 16'sd4000;
        coeff_re = 16'sd16384;
        coeff_im = 16'sd0;
        in_index = 6'd22;
        in_last = 1'b1;
        @(posedge clk);
        #1;
        if (!out_valid || in_ready) begin
            $display("FAIL output stall did not close input");
            errors = errors + 1;
        end
        held_re = $signed(out_re);
        held_im = $signed(out_im);
        held_index = out_index;

        @(negedge clk);
        in_valid = 1'b0;
        repeat (2) begin
            @(posedge clk);
            #1;
            expect_int($signed(out_re), held_re, "stall holds real");
            expect_int($signed(out_im), held_im, "stall holds imag");
            expect_int(out_index, held_index, "stall holds metadata");
            expect_int(out_last, 1, "stall holds last");
        end

        @(negedge clk);
        out_ready = 1'b1;
        @(posedge clk);
        #1;
        expect_int(out_valid, 0, "output drains after backpressure release");
        expect_int(saturation_count, 2, "stall does not double-count saturation");

        if (errors == 0)
            $display("PASS: OFDM one-tap equalizer arithmetic and backpressure");
        else begin
            $display("FAIL: OFDM one-tap equalizer errors=%0d", errors);
            $fatal(1);
        end
        $finish;
    end
endmodule
