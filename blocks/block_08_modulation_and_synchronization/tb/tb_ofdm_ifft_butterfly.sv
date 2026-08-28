`timescale 1ns/1ps

module tb_ofdm_ifft_butterfly;

    reg clk = 1'b0;
    reg resetn = 1'b0;
    reg valid_in = 1'b0;

    reg signed [15:0] a_re = 16'sd0;
    reg signed [15:0] a_im = 16'sd0;
    reg signed [15:0] b_re = 16'sd0;
    reg signed [15:0] b_im = 16'sd0;
    reg signed [15:0] w_re = 16'sd0;
    reg signed [15:0] w_im = 16'sd0;

    wire valid_out;
    wire signed [15:0] y0_re;
    wire signed [15:0] y0_im;
    wire signed [15:0] y1_re;
    wire signed [15:0] y1_im;
    wire [2:0] saturation_count;

    integer errors = 0;
    integer held_y0_re;
    integer held_y0_im;
    integer held_y1_re;
    integer held_y1_im;
    integer held_saturations;

    ofdm_ifft_butterfly dut (
        .clk(clk),
        .resetn(resetn),
        .valid_in(valid_in),
        .a_re(a_re),
        .a_im(a_im),
        .b_re(b_re),
        .b_im(b_im),
        .w_re(w_re),
        .w_im(w_im),
        .valid_out(valid_out),
        .y0_re(y0_re),
        .y0_im(y0_im),
        .y1_re(y1_re),
        .y1_im(y1_im),
        .saturation_count(saturation_count)
    );

    always #5 clk = ~clk;

    task expect_int;
        input integer actual;
        input integer expected;
        input [8*64-1:0] label_text;
        begin
            if (actual !== expected) begin
                $display("FAIL %-52s actual=%0d expected=%0d", label_text, actual, expected);
                errors = errors + 1;
            end else begin
                $display("PASS %-52s value=%0d", label_text, actual);
            end
        end
    endtask

    task apply_and_check;
        input integer in_a_re;
        input integer in_a_im;
        input integer in_b_re;
        input integer in_b_im;
        input integer in_w_re;
        input integer in_w_im;
        input integer exp_y0_re;
        input integer exp_y0_im;
        input integer exp_y1_re;
        input integer exp_y1_im;
        input integer exp_saturations;
        input [8*64-1:0] label_text;
        begin
            @(negedge clk);
            a_re = in_a_re;
            a_im = in_a_im;
            b_re = in_b_re;
            b_im = in_b_im;
            w_re = in_w_re;
            w_im = in_w_im;
            valid_in = 1'b1;

            @(posedge clk);
            #1;
            expect_int(valid_out, 1, label_text);
            expect_int($signed(y0_re), exp_y0_re, "butterfly y0 real");
            expect_int($signed(y0_im), exp_y0_im, "butterfly y0 imag");
            expect_int($signed(y1_re), exp_y1_re, "butterfly y1 real");
            expect_int($signed(y1_im), exp_y1_im, "butterfly y1 imag");
            expect_int(saturation_count, exp_saturations, "butterfly saturation count");

            @(negedge clk);
            valid_in = 1'b0;
        end
    endtask

    initial begin
        repeat (3) @(posedge clk);
        #1;
        expect_int(valid_out, 0, "reset clears valid_out");
        expect_int($signed(y0_re), 0, "reset clears y0 real");
        expect_int($signed(y0_im), 0, "reset clears y0 imag");
        expect_int($signed(y1_re), 0, "reset clears y1 real");
        expect_int($signed(y1_im), 0, "reset clears y1 imag");
        expect_int(saturation_count, 0, "reset clears saturation count");

        @(negedge clk);
        resetn = 1'b1;

        // W ~= +1: b*32767/32768 rounds back to b for these values.
        apply_and_check(
            1000, -2000,
            3000, 4000,
            32767, 0,
            2000, 1000,
            -1000, -3000,
            0,
            "unit twiddle produces scaled sum/difference"
        );

        // W ~= +j verifies the positive-sign IFFT twiddle convention.
        apply_and_check(
            1000, -2000,
            3000, 4000,
            0, 32767,
            -1500, 500,
            2500, -2500,
            0,
            "+j twiddle rotates b before butterfly"
        );

        // The Q30 product is exactly +0.5 LSB before its >>15 conversion.
        // Ties must round away from zero, then the /2 tie also rounds away.
        apply_and_check(
            0, 0,
            1, 0,
            16384, 0,
            1, 0,
            -1, 0,
            0,
            "positive half-LSB ties round away from zero"
        );

        // Same check on the negative side: -0.5 LSB must become -1.
        apply_and_check(
            0, 0,
            -1, 0,
            16384, 0,
            -1, 0,
            1, 0,
            0,
            "negative half-LSB ties round away from zero"
        );

        // This vector makes the widened twiddle result exceed Q1.15 before
        // the stage scaling. It must not be clipped there. After /2 only the
        // y0 imaginary component saturates.
        apply_and_check(
            32767, 32767,
            32767, 32767,
            23170, 23170,
            16384, 32767,
            16384, -6786,
            1,
            "positive final-component saturation is counted"
        );

        // Symmetric negative case checks the -32768 endpoint and saturation.
        apply_and_check(
            -32768, -32768,
            -32768, -32768,
            23170, 23170,
            -16384, -32768,
            -16384, 6786,
            1,
            "negative final-component saturation is counted"
        );

        // valid_in=0 must suppress valid_out and preserve the last payload.
        held_y0_re = $signed(y0_re);
        held_y0_im = $signed(y0_im);
        held_y1_re = $signed(y1_re);
        held_y1_im = $signed(y1_im);
        held_saturations = saturation_count;
        @(posedge clk);
        #1;
        expect_int(valid_out, 0, "valid gap suppresses valid_out");
        expect_int($signed(y0_re), held_y0_re, "valid gap holds y0 real");
        expect_int($signed(y0_im), held_y0_im, "valid gap holds y0 imag");
        expect_int($signed(y1_re), held_y1_re, "valid gap holds y1 real");
        expect_int($signed(y1_im), held_y1_im, "valid gap holds y1 imag");
        expect_int(saturation_count, held_saturations, "valid gap holds saturation count");

        // Reset has priority over a simultaneous valid request.
        @(negedge clk);
        resetn = 1'b0;
        valid_in = 1'b1;
        a_re = 16'sd7777;
        a_im = -16'sd7777;
        b_re = 16'sd3333;
        b_im = 16'sd2222;
        w_re = 16'sd32767;
        w_im = 16'sd0;
        @(posedge clk);
        #1;
        expect_int(valid_out, 0, "reset suppresses simultaneous valid request");
        expect_int($signed(y0_re), 0, "reset clears y0 real after activity");
        expect_int($signed(y0_im), 0, "reset clears y0 imag after activity");
        expect_int($signed(y1_re), 0, "reset clears y1 real after activity");
        expect_int($signed(y1_im), 0, "reset clears y1 imag after activity");
        expect_int(saturation_count, 0, "reset clears saturation count after activity");

        @(negedge clk);
        valid_in = 1'b0;
        resetn = 1'b1;

        if (errors == 0) begin
            $display("PASS tb_ofdm_ifft_butterfly");
        end else begin
            $display("FAIL tb_ofdm_ifft_butterfly errors=%0d", errors);
            $fatal(1);
        end
        $finish;
    end

endmodule
