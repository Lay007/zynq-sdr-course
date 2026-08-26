`timescale 1ns/1ps

module tb_css_dft128_core;

    localparam integer N = 128;
    localparam integer MAX_RESULT_CYCLES = 17000;
    localparam integer EXPECTED_PEAK_BIN = 37;

    reg clk = 1'b0;
    reg resetn = 1'b0;
    reg start = 1'b0;

    wire busy;
    wire done;
    wire start_rejected;
    wire [6:0] sample_addr;
    wire signed [15:0] sample_re;
    wire signed [15:0] sample_im;
    wire bin_valid;
    wire [6:0] bin_index;
    wire signed [31:0] bin_re;
    wire signed [31:0] bin_im;
    wire signed [63:0] magnitude_squared;

    reg signed [15:0] input_re [0:N-1];
    reg signed [15:0] input_im [0:N-1];
    reg signed [31:0] expected_re [0:N-1];
    reg signed [31:0] expected_im [0:N-1];
    reg signed [63:0] expected_magnitude_squared [0:N-1];

    integer errors = 0;
    integer bin_count;
    integer wait_cycles;
    integer observed_peak_bin;
    reg signed [63:0] observed_peak_magnitude;
    reg previous_bin_valid;

    always #5 clk = ~clk;

    assign sample_re = input_re[sample_addr];
    assign sample_im = input_im[sample_addr];

    css_dft128_core dut (
        .clk(clk),
        .resetn(resetn),
        .start(start),
        .busy(busy),
        .done(done),
        .start_rejected(start_rejected),
        .sample_addr(sample_addr),
        .sample_re(sample_re),
        .sample_im(sample_im),
        .bin_valid(bin_valid),
        .bin_index(bin_index),
        .bin_re(bin_re),
        .bin_im(bin_im),
        .magnitude_squared(magnitude_squared)
    );

    task automatic fail;
        input [767:0] message;
        begin
            $display("FAIL %0s", message);
            errors = errors + 1;
        end
    endtask

    task automatic pulse_start;
        begin
            @(negedge clk);
            start = 1'b1;
            @(posedge clk);
            #1;
            if (busy !== 1'b1)
                fail("accepted start did not assert busy");
            @(negedge clk);
            start = 1'b0;
        end
    endtask

    initial begin
        $readmemh(
            "blocks/block_08_modulation_and_synchronization/tb/vectors/css_dft128_input_i_q15.hex",
            input_re
        );
        $readmemh(
            "blocks/block_08_modulation_and_synchronization/tb/vectors/css_dft128_input_q_q15.hex",
            input_im
        );
        $readmemh(
            "blocks/block_08_modulation_and_synchronization/tb/vectors/css_dft128_expected_i_s32.hex",
            expected_re
        );
        $readmemh(
            "blocks/block_08_modulation_and_synchronization/tb/vectors/css_dft128_expected_q_s32.hex",
            expected_im
        );
        $readmemh(
            "blocks/block_08_modulation_and_synchronization/tb/vectors/css_dft128_expected_mag2_s64.hex",
            expected_magnitude_squared
        );

        repeat (3) @(posedge clk);
        #1;
        if (busy !== 1'b0 || done !== 1'b0 || bin_valid !== 1'b0 ||
            start_rejected !== 1'b0)
            fail("reset outputs are not idle");

        @(negedge clk);
        resetn = 1'b1;
        @(posedge clk);
        #1;
        if (busy !== 1'b0 || done !== 1'b0 || bin_valid !== 1'b0)
            fail("core did not enter idle state after reset");

        // Begin a transform, then prove that a second start is rejected.
        pulse_start();
        repeat (8) @(posedge clk);
        @(negedge clk);
        start = 1'b1;
        @(posedge clk);
        #1;
        if (busy !== 1'b1 || start_rejected !== 1'b1)
            fail("start while busy was not explicitly rejected");
        @(negedge clk);
        start = 1'b0;
        @(posedge clk);
        #1;
        if (start_rejected !== 1'b0)
            fail("start_rejected is not a one-cycle pulse");

        // Reset must abort the partial transform without a bin or done event.
        repeat (16) @(posedge clk);
        @(negedge clk);
        resetn = 1'b0;
        @(posedge clk);
        #1;
        if (busy !== 1'b0 || done !== 1'b0 || bin_valid !== 1'b0 ||
            start_rejected !== 1'b0)
            fail("reset did not abort the active transform cleanly");
        repeat (2) @(posedge clk);
        #1;
        if (busy !== 1'b0 || done !== 1'b0 || bin_valid !== 1'b0)
            fail("aborted transform produced an output event during reset");

        @(negedge clk);
        resetn = 1'b1;
        @(posedge clk);
        #1;
        if (busy !== 1'b0)
            fail("core was not restartable after reset abort");

        pulse_start();
        bin_count = 0;
        wait_cycles = 0;
        previous_bin_valid = 1'b0;
        observed_peak_bin = 0;
        observed_peak_magnitude = -64'sd1;

        while (done !== 1'b1 && wait_cycles < MAX_RESULT_CYCLES) begin
            @(posedge clk);
            #1;
            wait_cycles = wait_cycles + 1;

            if (bin_valid) begin
                if (previous_bin_valid)
                    fail("bin_valid remained asserted for consecutive clocks");
                if ((^bin_index === 1'bx) || (^bin_re === 1'bx) ||
                    (^bin_im === 1'bx) || (^magnitude_squared === 1'bx))
                    fail("valid bin output contains X/Z values");
                if (bin_count >= N) begin
                    fail("more than 128 bins were emitted");
                end else begin
                    if (bin_index !== bin_count[6:0]) begin
                        $display(
                            "FAIL bin index progression actual=%0d expected=%0d",
                            bin_index,
                            bin_count
                        );
                        errors = errors + 1;
                    end
                    if (bin_re !== expected_re[bin_count]) begin
                        $display(
                            "FAIL bin=%0d real actual=%0d expected=%0d",
                            bin_count,
                            bin_re,
                            expected_re[bin_count]
                        );
                        errors = errors + 1;
                    end
                    if (bin_im !== expected_im[bin_count]) begin
                        $display(
                            "FAIL bin=%0d imag actual=%0d expected=%0d",
                            bin_count,
                            bin_im,
                            expected_im[bin_count]
                        );
                        errors = errors + 1;
                    end
                    if (magnitude_squared !== expected_magnitude_squared[bin_count]) begin
                        $display(
                            "FAIL bin=%0d magnitude actual=%0d expected=%0d",
                            bin_count,
                            magnitude_squared,
                            expected_magnitude_squared[bin_count]
                        );
                        errors = errors + 1;
                    end
                    if (bin_count == 0 ||
                        magnitude_squared > observed_peak_magnitude) begin
                        observed_peak_magnitude = magnitude_squared;
                        observed_peak_bin = bin_index;
                    end
                end
                bin_count = bin_count + 1;
            end
            previous_bin_valid = bin_valid;
        end

        if (done !== 1'b1)
            fail("transform timed out");
        if (bin_count != N) begin
            $display("FAIL emitted bin count actual=%0d expected=%0d", bin_count, N);
            errors = errors + 1;
        end
        if (observed_peak_bin != EXPECTED_PEAK_BIN) begin
            $display(
                "FAIL pure-tone peak actual=%0d expected=%0d",
                observed_peak_bin,
                EXPECTED_PEAK_BIN
            );
            errors = errors + 1;
        end
        if (busy !== 1'b0)
            fail("busy did not clear with done");

        @(posedge clk);
        #1;
        if (done !== 1'b0 || bin_valid !== 1'b0)
            fail("done/final bin_valid are not one-cycle events");

        if (errors == 0) begin
            $display(
                "PASS tb_css_dft128_core bins=%0d peak_bin=%0d cycles=%0d",
                bin_count,
                observed_peak_bin,
                wait_cycles
            );
        end else begin
            $display("FAIL tb_css_dft128_core errors=%0d", errors);
            $fatal(1);
        end
        $finish;
    end

endmodule
