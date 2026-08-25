`timescale 1ns/1ps

module tb_css_dechirp_mul;
    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg resetn = 1'b0;
    reg valid_in = 1'b0;
    reg signed [15:0] iq_re = 16'sd0;
    reg signed [15:0] iq_im = 16'sd0;
    reg signed [15:0] ref_re = 16'sd0;
    reg signed [15:0] ref_im = 16'sd0;

    wire valid_out;
    wire signed [15:0] dechirp_re;
    wire signed [15:0] dechirp_im;
    wire overflow;

    integer errors = 0;

    css_dechirp_mul dut (
        .clk(clk),
        .resetn(resetn),
        .valid_in(valid_in),
        .iq_re(iq_re),
        .iq_im(iq_im),
        .ref_re(ref_re),
        .ref_im(ref_im),
        .valid_out(valid_out),
        .dechirp_re(dechirp_re),
        .dechirp_im(dechirp_im),
        .overflow(overflow)
    );

    task automatic expect_bit(
        input logic got,
        input logic expected,
        input string label_text
    );
        begin
            if (got === expected)
                $display("PASS %-60s value=%0d", label_text, got);
            else begin
                errors = errors + 1;
                $display("FAIL %-60s got=%0b expected=%0b", label_text, got, expected);
            end
        end
    endtask

    task automatic expect_signed16(
        input signed [15:0] got,
        input integer expected,
        input string label_text
    );
        begin
            if ($signed(got) === expected)
                $display("PASS %-60s value=%0d", label_text, $signed(got));
            else begin
                errors = errors + 1;
                $display("FAIL %-60s got=%0d expected=%0d", label_text, $signed(got), expected);
            end
        end
    endtask

    task automatic drive_and_expect(
        input integer xr,
        input integer xi,
        input integer rr,
        input integer ri,
        input integer expected_re,
        input integer expected_im,
        input logic expected_overflow,
        input string label_text
    );
        begin
            @(negedge clk);
            iq_re <= xr;
            iq_im <= xi;
            ref_re <= rr;
            ref_im <= ri;
            valid_in <= 1'b1;

            @(posedge clk);
            #1;
            expect_bit(valid_out, 1'b1, {label_text, " valid"});
            expect_signed16(dechirp_re, expected_re, {label_text, " real"});
            expect_signed16(dechirp_im, expected_im, {label_text, " imag"});
            expect_bit(overflow, expected_overflow, {label_text, " overflow"});

            @(negedge clk);
            valid_in <= 1'b0;
            @(posedge clk);
            #1;
            expect_bit(valid_out, 1'b0, {label_text, " valid pulse clears"});
            expect_bit(overflow, 1'b0, {label_text, " overflow pulse clears"});
        end
    endtask

    initial begin
        repeat (4) @(posedge clk);
        #1;
        expect_bit(valid_out, 1'b0, "valid reset");
        expect_signed16(dechirp_re, 0, "real reset");
        expect_signed16(dechirp_im, 0, "imag reset");
        expect_bit(overflow, 1'b0, "overflow reset");

        @(negedge clk);
        resetn <= 1'b1;
        repeat (2) @(posedge clk);

        // Q1.15 0.5 multiplied by the largest positive representation of +1.
        // Truncation is explicit: 16384*32767 >> 15 = 16383.
        drive_and_expect(
            16384, 0, 32767, 0,
            16383, 0, 1'b0,
            "half-scale times positive unity"
        );

        // Multiplication by conj(+j) rotates the input by -90 degrees.
        drive_and_expect(
            16384, 0, 0, 32767,
            0, -16384, 1'b0,
            "conjugate quadrature rotation"
        );

        // Non-trivial complex vector. The expected values are the exact
        // integer RTL equations, not a floating-point tolerance check.
        drive_and_expect(
            8192, 16384, 19661, 26214,
            18022, 3277, 1'b0,
            "mixed complex fixed-point vector"
        );

        drive_and_expect(
            -32768, 0, 32767, 0,
            -32767, 0, 1'b0,
            "negative full-scale without saturation"
        );

        // Arbitrary full-scale complex components can exceed Q1.15 even
        // though a unit-magnitude chirp reference normally does not. Keep the
        // protection explicit so future ROM/AGC mistakes cannot wrap silently.
        drive_and_expect(
            32767, 32767, 32767, 32767,
            32767, 0, 1'b1,
            "positive saturation"
        );

        drive_and_expect(
            32767, 32767, -32768, -32768,
            -32768, 0, 1'b1,
            "negative saturation"
        );

        // Reset has priority over an otherwise valid sample.
        @(negedge clk);
        valid_in <= 1'b1;
        iq_re <= 16'sd1234;
        iq_im <= -16'sd567;
        ref_re <= 16'sd32767;
        ref_im <= 16'sd0;
        resetn <= 1'b0;
        @(posedge clk);
        #1;
        expect_bit(valid_out, 1'b0, "reset suppresses accepted output");
        expect_signed16(dechirp_re, 0, "reset clears real output");
        expect_signed16(dechirp_im, 0, "reset clears imag output");
        expect_bit(overflow, 1'b0, "reset clears overflow output");

        @(negedge clk);
        valid_in <= 1'b0;
        resetn <= 1'b1;
        repeat (2) @(posedge clk);

        if (errors == 0)
            $display("PASS tb_css_dechirp_mul");
        else begin
            $display("FAIL tb_css_dechirp_mul errors=%0d", errors);
            $fatal(1);
        end

        $finish;
    end

endmodule
