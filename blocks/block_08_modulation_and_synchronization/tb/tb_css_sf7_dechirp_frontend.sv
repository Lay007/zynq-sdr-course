`timescale 1ns/1ps

module tb_css_sf7_dechirp_frontend;

    localparam integer N = 128;
    localparam [6:0] SYMBOL = 7'd37;

    reg clk = 1'b0;
    reg resetn = 1'b0;
    reg valid_in = 1'b0;
    reg [6:0] sample_index = 7'd0;

    wire [6:0] symbol_addr = sample_index + SYMBOL;
    wire signed [15:0] iq_re;
    wire signed [15:0] iq_im;

    wire valid_out;
    wire signed [15:0] dechirp_re;
    wire signed [15:0] dechirp_im;
    wire overflow;

    reg [31:0] expected [0:N-1];
    integer i;
    integer errors = 0;
    integer overflow_count = 0;

    always #5 clk = ~clk;

    // Reuse the same committed SF7 reference ROM to construct symbol 37:
    // symbol[n] = reference[(n + 37) mod 128].
    css_sf7_ref_rom u_symbol_rom (
        .addr   (symbol_addr),
        .ref_re (iq_re),
        .ref_im (iq_im)
    );

    css_sf7_dechirp_frontend dut (
        .clk        (clk),
        .resetn     (resetn),
        .valid_in   (valid_in),
        .sample_index(sample_index),
        .iq_re      (iq_re),
        .iq_im      (iq_im),
        .valid_out  (valid_out),
        .dechirp_re (dechirp_re),
        .dechirp_im (dechirp_im),
        .overflow   (overflow)
    );

    task automatic check_bit;
        input [255:0] label;
        input actual;
        input expected_value;
        begin
            if (actual !== expected_value) begin
                $display("FAIL %-58s actual=%0d expected=%0d", label, actual, expected_value);
                errors = errors + 1;
            end else begin
                $display("PASS %-58s value=%0d", label, actual);
            end
        end
    endtask

    task automatic check_sample;
        input integer index;
        reg signed [15:0] exp_re;
        reg signed [15:0] exp_im;
        begin
            exp_re = expected[index][31:16];
            exp_im = expected[index][15:0];

            if (valid_out !== 1'b1) begin
                $display("FAIL sample[%0d] valid_out actual=%0d expected=1", index, valid_out);
                errors = errors + 1;
            end
            if (dechirp_re !== exp_re || dechirp_im !== exp_im) begin
                $display(
                    "FAIL sample[%0d] dechirped IQ actual=(%0d,%0d) expected=(%0d,%0d)",
                    index, dechirp_re, dechirp_im, exp_re, exp_im
                );
                errors = errors + 1;
            end
            if (overflow !== 1'b0) begin
                $display("FAIL sample[%0d] unexpected overflow", index);
                errors = errors + 1;
                overflow_count = overflow_count + 1;
            end
        end
    endtask

    initial begin
        $readmemh(
            "blocks/block_08_modulation_and_synchronization/tb/vectors/css_sf7_symbol37_dechirp_q15.hex",
            expected
        );

        repeat (3) @(posedge clk);
        #1;
        check_bit("valid reset", valid_out, 1'b0);
        check_bit("overflow reset", overflow, 1'b0);

        @(negedge clk);
        resetn = 1'b1;

        // Explicit invalid cycle before continuous streaming.
        sample_index = 7'd0;
        valid_in = 1'b0;
        @(posedge clk);
        #1;
        check_bit("valid gap produces no output", valid_out, 1'b0);

        // Stream the complete SF7 symbol without gaps. The expected file is an
        // independently generated fixed-point golden vector for symbol 37.
        for (i = 0; i < N; i = i + 1) begin
            @(negedge clk);
            sample_index = i[6:0];
            valid_in = 1'b1;
            @(posedge clk);
            #1;
            check_sample(i);
        end

        @(negedge clk);
        valid_in = 1'b0;
        @(posedge clk);
        #1;
        check_bit("valid pulse clears after full symbol", valid_out, 1'b0);

        if (overflow_count == 0)
            $display("PASS full SF7 symbol has no dechirp saturation");
        else begin
            $display("FAIL full SF7 symbol overflow count=%0d", overflow_count);
            errors = errors + 1;
        end

        if (errors == 0) begin
            $display("PASS all 128 symbol-37 dechirp samples match Q1.15 golden vector");
            $display("PASS tb_css_sf7_dechirp_frontend");
        end else begin
            $display("FAIL tb_css_sf7_dechirp_frontend errors=%0d", errors);
            $fatal(1);
        end

        $finish;
    end

endmodule
