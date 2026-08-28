`timescale 1ns/1ps

module tb_ofdm_cp16_inserter;

    reg clk = 1'b0;
    reg resetn = 1'b0;

    reg in_valid = 1'b0;
    wire in_ready;
    reg signed [15:0] in_re = 16'sd0;
    reg signed [15:0] in_im = 16'sd0;
    reg in_last = 1'b0;

    wire out_valid;
    reg out_ready = 1'b0;
    wire signed [15:0] out_re;
    wire signed [15:0] out_im;
    wire [6:0] out_index;
    wire out_is_cp;
    wire out_last;
    wire frame_error;

    integer errors = 0;
    integer idx;
    integer source_index;
    integer expected_re;
    integer expected_im;
    integer held_re;
    integer held_im;
    integer held_index;

    ofdm_cp16_inserter dut (
        .clk(clk),
        .resetn(resetn),
        .in_valid(in_valid),
        .in_ready(in_ready),
        .in_re(in_re),
        .in_im(in_im),
        .in_last(in_last),
        .out_valid(out_valid),
        .out_ready(out_ready),
        .out_re(out_re),
        .out_im(out_im),
        .out_index(out_index),
        .out_is_cp(out_is_cp),
        .out_last(out_last),
        .frame_error(frame_error)
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

    task send_sample;
        input integer sample_number;
        input integer early_last_index;
        begin
            @(negedge clk);
            in_valid = 1'b1;
            in_re = 16'sd1000 + sample_number;
            in_im = -(16'sd2000 + sample_number);
            in_last =
                (sample_number == 63) ||
                ((early_last_index >= 0) && (sample_number == early_last_index));

            while (!in_ready)
                @(negedge clk);

            @(posedge clk);
            #1;
            if (sample_number < 63) begin
                expect_int(in_ready, 1, "CP inserter keeps collecting before sample 63");
                expect_int(out_valid, 0, "CP inserter does not emit partial symbol");
            end else begin
                expect_int(in_ready, 0, "sample 63 closes CP input symbol");
                expect_int(out_valid, 1, "sample 63 makes CP output symbol available");
                expect_int(out_index, 0, "CP output begins at index zero");
            end

            @(negedge clk);
            in_valid = 1'b0;
            in_last = 1'b0;
        end
    endtask

    task load_symbol;
        input integer early_last_index;
        begin
            for (idx = 0; idx < 64; idx = idx + 1) begin
                if ((idx == 9) || (idx == 41)) begin
                    @(negedge clk);
                    in_valid = 1'b0;
                    in_last = 1'b0;
                    @(posedge clk);
                    #1;
                    expect_int(in_ready, 1, "input valid gap keeps CP collector ready");
                    expect_int(out_valid, 0, "input valid gap does not emit early symbol");
                end
                send_sample(idx, early_last_index);
            end
        end
    endtask

    task check_output;
        input integer output_number;
        input integer expected_error;
        begin
            if (output_number < 16)
                source_index = 48 + output_number;
            else
                source_index = output_number - 16;

            expected_re = 1000 + source_index;
            expected_im = -(2000 + source_index);

            expect_int(out_valid, 1, "CP output valid during 80-sample symbol");
            expect_int(out_index, output_number, "CP output index");
            expect_int($signed(out_re), expected_re, "CP output real payload");
            expect_int($signed(out_im), expected_im, "CP output imag payload");
            expect_int(out_is_cp, (output_number < 16), "CP flag covers output indices 0 through 15");
            expect_int(out_last, (output_number == 79), "CP out_last only on output index 79");
            expect_int(frame_error, expected_error, "CP frame_error is stable for output symbol");
        end
    endtask

    task consume_symbol;
        input integer expected_error;
        begin
            for (idx = 0; idx < 80; idx = idx + 1) begin
                @(negedge clk);

                if (idx == 5) begin
                    out_ready = 1'b0;
                    #1;
                    check_output(idx, expected_error);
                    held_re = $signed(out_re);
                    held_im = $signed(out_im);
                    held_index = out_index;
                    repeat (2) begin
                        @(posedge clk);
                        #1;
                        expect_int(out_index, held_index, "CP backpressure holds output index");
                        expect_int($signed(out_re), held_re, "CP backpressure holds output real");
                        expect_int($signed(out_im), held_im, "CP backpressure holds output imag");
                        expect_int(out_valid, 1, "CP backpressure keeps output valid");
                        expect_int(frame_error, expected_error, "CP backpressure holds frame_error");
                    end
                    @(negedge clk);
                end

                out_ready = 1'b1;
                #1;
                check_output(idx, expected_error);
                @(posedge clk);
                #1;
            end

            out_ready = 1'b0;
            expect_int(out_valid, 0, "output index 79 completes CP symbol");
            expect_int(in_ready, 1, "completed CP symbol rearms input collector");
            expect_int(frame_error, 0, "frame_error clears between symbols");
        end
    endtask

    initial begin
        repeat (3) @(posedge clk);
        #1;
        expect_int(in_ready, 1, "reset leaves CP inserter ready");
        expect_int(out_valid, 0, "reset leaves CP output invalid");
        expect_int(frame_error, 0, "reset clears CP frame_error");

        @(negedge clk);
        resetn = 1'b1;

        // Correct TLAST: output must be exactly x[48:63] followed by x[0:63].
        load_symbol(-1);
        expect_int(frame_error, 0, "correct input TLAST leaves frame_error clear");
        consume_symbol(0);

        // An early TLAST is diagnostic only: grouping remains exactly 64
        // accepted input samples and the output data mapping remains intact.
        load_symbol(10);
        expect_int(frame_error, 1, "early input TLAST sets frame_error");
        consume_symbol(1);

        // Reset while collecting a partial third symbol discards all partial
        // state and returns to a clean collector.
        send_sample(0, -1);
        send_sample(1, -1);
        @(negedge clk);
        resetn = 1'b0;
        in_valid = 1'b1;
        in_re = 16'sd7777;
        in_im = -16'sd7777;
        in_last = 1'b1;
        @(posedge clk);
        #1;
        expect_int(in_ready, 1, "reset reopens CP collector after partial symbol");
        expect_int(out_valid, 0, "reset discards partial CP symbol");
        expect_int(frame_error, 0, "reset clears partial-symbol frame_error");

        @(negedge clk);
        resetn = 1'b1;
        in_valid = 1'b0;
        in_last = 1'b0;

        if (errors == 0) begin
            $display("PASS tb_ofdm_cp16_inserter");
        end else begin
            $display("FAIL tb_ofdm_cp16_inserter errors=%0d", errors);
            $fatal(1);
        end
        $finish;
    end

endmodule
