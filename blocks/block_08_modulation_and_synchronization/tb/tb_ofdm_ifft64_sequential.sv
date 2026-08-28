`timescale 1ns/1ps

module tb_ofdm_ifft64_sequential;

    reg clk = 1'b0;
    reg resetn = 1'b0;

    reg bin_valid = 1'b0;
    wire bin_ready;
    reg signed [15:0] bin_re = 16'sd0;
    reg signed [15:0] bin_im = 16'sd0;

    wire sample_valid;
    reg sample_ready = 1'b0;
    wire signed [15:0] sample_re;
    wire signed [15:0] sample_im;
    wire [5:0] sample_index;
    wire sample_last;
    wire busy;
    wire [15:0] total_saturation_count;

    reg [31:0] expected_bin1 [0:63];

    integer errors = 0;
    integer idx;
    integer compute_cycles;
    integer expected_re;
    integer expected_im;
    integer held_re;
    integer held_im;
    integer held_index;

    ofdm_ifft64_sequential dut (
        .clk(clk),
        .resetn(resetn),
        .bin_valid(bin_valid),
        .bin_ready(bin_ready),
        .bin_re(bin_re),
        .bin_im(bin_im),
        .sample_valid(sample_valid),
        .sample_ready(sample_ready),
        .sample_re(sample_re),
        .sample_im(sample_im),
        .sample_index(sample_index),
        .sample_last(sample_last),
        .busy(busy),
        .total_saturation_count(total_saturation_count)
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

    task load_single_frequency_bin;
        input integer active_bin;
        begin
            for (idx = 0; idx < 64; idx = idx + 1) begin
                // Two deliberate input gaps prove that only handshakes advance
                // the natural-order input counter.
                if ((idx == 11) || (idx == 47)) begin
                    @(negedge clk);
                    bin_valid = 1'b0;
                    @(posedge clk);
                    #1;
                    expect_int(bin_ready, 1, "input gap keeps IFFT loader ready");
                    expect_int(busy, 0, "input gap does not start transform early");
                end

                @(negedge clk);
                bin_valid = 1'b1;
                if (idx == active_bin) begin
                    bin_re = 16'sd32767;
                    bin_im = 16'sd0;
                end else begin
                    bin_re = 16'sd0;
                    bin_im = 16'sd0;
                end

                @(posedge clk);
                #1;
                if (idx < 63) begin
                    expect_int(bin_ready, 1, "IFFT accepts remaining natural-order bins");
                end else begin
                    expect_int(bin_ready, 0, "64th bin closes IFFT input frame");
                    expect_int(busy, 1, "64th bin starts IFFT computation");
                    expect_int(sample_valid, 0, "output remains invalid at computation start");
                end
            end

            @(negedge clk);
            bin_valid = 1'b0;
            bin_re = 16'sd0;
            bin_im = 16'sd0;
        end
    endtask

    task wait_for_transform;
        begin
            compute_cycles = 0;
            while (!sample_valid && (compute_cycles < 400)) begin
                @(posedge clk);
                #1;
                compute_cycles = compute_cycles + 1;
            end
            expect_int(sample_valid, 1, "IFFT eventually presents output frame");
            expect_int(compute_cycles, 384, "single-butterfly IFFT compute latency clocks");
            expect_int(busy, 0, "busy drops when output frame becomes available");
            expect_int(sample_index, 0, "IFFT output starts at natural sample zero");
            expect_int(total_saturation_count, 0, "test transform has no saturation");
        end
    endtask

    task check_current_sample;
        input integer expected_index;
        input integer vector_kind;
        begin
            if (vector_kind == 0) begin
                expected_re = 512;
                expected_im = 0;
            end else begin
                expected_re = $signed(expected_bin1[expected_index][31:16]);
                expected_im = $signed(expected_bin1[expected_index][15:0]);
            end

            expect_int(sample_valid, 1, "sample_valid stays asserted during output frame");
            expect_int(sample_index, expected_index, "natural time-domain sample index");
            expect_int($signed(sample_re), expected_re, "time-domain sample real");
            expect_int($signed(sample_im), expected_im, "time-domain sample imag");
            expect_int(sample_last, (expected_index == 63), "sample_last only on sample 63");
            expect_int(total_saturation_count, 0, "output frame retains zero saturation count");
        end
    endtask

    task consume_output_frame;
        input integer vector_kind;
        begin
            for (idx = 0; idx < 64; idx = idx + 1) begin
                @(negedge clk);

                if (idx == 17) begin
                    sample_ready = 1'b0;
                    #1;
                    check_current_sample(idx, vector_kind);
                    held_re = $signed(sample_re);
                    held_im = $signed(sample_im);
                    held_index = sample_index;
                    repeat (2) begin
                        @(posedge clk);
                        #1;
                        expect_int(sample_index, held_index, "backpressure holds sample index");
                        expect_int($signed(sample_re), held_re, "backpressure holds sample real");
                        expect_int($signed(sample_im), held_im, "backpressure holds sample imag");
                        expect_int(sample_valid, 1, "backpressure keeps sample_valid asserted");
                    end
                    @(negedge clk);
                end

                sample_ready = 1'b1;
                #1;
                check_current_sample(idx, vector_kind);
                @(posedge clk);
                #1;
            end

            sample_ready = 1'b0;
            expect_int(sample_valid, 0, "sample 63 handshake completes output frame");
            expect_int(bin_ready, 1, "completed output frame rearms IFFT input");
            expect_int(busy, 0, "completed output frame leaves IFFT idle");
        end
    endtask

    initial begin
        $readmemh(
            "verification/vectors/block08_ofdm_ifft_bin1_expected.mem",
            expected_bin1
        );

        repeat (3) @(posedge clk);
        #1;
        expect_int(bin_ready, 1, "reset leaves IFFT ready for a new frame");
        expect_int(sample_valid, 0, "reset leaves IFFT output invalid");
        expect_int(busy, 0, "reset clears IFFT busy");
        expect_int(total_saturation_count, 0, "reset clears total saturation count");

        @(negedge clk);
        resetn = 1'b1;

        // DC-only input has the exact normalized IFFT result 32767/64 -> 512
        // on every real output sample. This validates bit reversal, all stage
        // traversals, distributed scaling and output ordering.
        load_single_frequency_bin(0);
        wait_for_transform();
        consume_output_frame(0);

        // A single k=+1 frequency bin produces the canonical complex sinusoid
        // generated by tools/ofdm_ifft_fixed.py. This vector exercises the
        // complete positive-sign IFFT twiddle table used by the six stages.
        load_single_frequency_bin(1);
        wait_for_transform();
        consume_output_frame(1);

        // Reset must discard a partially loaded third transform.
        @(negedge clk);
        bin_valid = 1'b1;
        bin_re = 16'sd1234;
        bin_im = -16'sd5678;
        @(posedge clk);
        @(negedge clk);
        resetn = 1'b0;
        @(posedge clk);
        #1;
        expect_int(bin_ready, 1, "reset discards partial IFFT input frame");
        expect_int(sample_valid, 0, "reset after partial frame keeps output invalid");
        expect_int(busy, 0, "reset after partial frame clears busy");
        expect_int(total_saturation_count, 0, "reset after partial frame clears saturation count");

        @(negedge clk);
        bin_valid = 1'b0;
        resetn = 1'b1;

        if (errors == 0) begin
            $display("PASS tb_ofdm_ifft64_sequential");
        end else begin
            $display("FAIL tb_ofdm_ifft64_sequential errors=%0d", errors);
            $fatal(1);
        end
        $finish;
    end

endmodule
