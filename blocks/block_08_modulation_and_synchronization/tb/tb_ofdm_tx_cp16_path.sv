`timescale 1ns/1ps

module tb_ofdm_tx_cp16_path;

    reg clk = 1'b0;
    reg resetn = 1'b0;

    reg bits_valid = 1'b0;
    wire bits_ready;
    reg [1:0] bits_in = 2'b00;

    wire sample_valid;
    reg sample_ready = 1'b0;
    wire signed [15:0] sample_re;
    wire signed [15:0] sample_im;
    wire [6:0] sample_index;
    wire sample_is_cp;
    wire sample_last;
    wire ifft_busy;
    wire [15:0] total_saturation_count;
    wire frame_error;

    reg [31:0] expected_samples [0:63];

    integer errors = 0;
    integer accepted_pairs = 0;
    integer idx;
    integer source_index;
    integer wait_cycles;
    integer expected_re;
    integer expected_im;
    integer held_re;
    integer held_im;
    integer held_index;
    integer held_is_cp;
    integer held_last;
    integer held_error;

    ofdm_tx_cp16_path dut (
        .clk(clk),
        .resetn(resetn),
        .bits_valid(bits_valid),
        .bits_ready(bits_ready),
        .bits_in(bits_in),
        .sample_valid(sample_valid),
        .sample_ready(sample_ready),
        .sample_re(sample_re),
        .sample_im(sample_im),
        .sample_index(sample_index),
        .sample_is_cp(sample_is_cp),
        .sample_last(sample_last),
        .ifft_busy(ifft_busy),
        .total_saturation_count(total_saturation_count),
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

    function [1:0] cycle4_bits;
        input integer data_index;
        begin
            case (data_index % 4)
                0: cycle4_bits = 2'b00;
                1: cycle4_bits = 2'b01;
                2: cycle4_bits = 2'b10;
                default: cycle4_bits = 2'b11;
            endcase
        end
    endfunction

    task send_pair;
        input integer data_index;
        begin
            @(negedge clk);
            bits_in = cycle4_bits(data_index);
            bits_valid = 1'b1;

            while (!bits_ready)
                @(negedge clk);

            @(posedge clk);
            if (bits_valid && bits_ready) begin
                accepted_pairs = accepted_pairs + 1;
            end else begin
                $display("FAIL advertised ready did not produce input handshake");
                errors = errors + 1;
            end

            @(negedge clk);
            bits_valid = 1'b0;
        end
    endtask

    task check_current_sample;
        input integer expected_index;
        begin
            if (expected_index < 16)
                source_index = 48 + expected_index;
            else
                source_index = expected_index - 16;

            expected_re = $signed(expected_samples[source_index][31:16]);
            expected_im = $signed(expected_samples[source_index][15:0]);

            expect_int(sample_valid, 1, "TX+CP sample_valid during output frame");
            expect_int(sample_index, expected_index, "TX+CP natural 80-sample index");
            expect_int($signed(sample_re), expected_re, "TX+CP exact sample real");
            expect_int($signed(sample_im), expected_im, "TX+CP exact sample imag");
            expect_int(sample_is_cp, (expected_index < 16), "TX+CP CP flag only on first 16 samples");
            expect_int(sample_last, (expected_index == 79), "TX+CP sample_last only on sample 79");
            expect_int(frame_error, 0, "composed TX has correct inner TLAST contract");
            expect_int(total_saturation_count, 0, "canonical TX+CP frame has zero IFFT saturation");
            expect_int(bits_ready, 0, "TX+CP frame lock prevents next-frame prefetch");
        end
    endtask

    task stall_current_sample;
        input integer expected_index;
        input integer stall_cycles;
        integer stall_idx;
        begin
            sample_ready = 1'b0;
            #1;
            check_current_sample(expected_index);
            held_re = $signed(sample_re);
            held_im = $signed(sample_im);
            held_index = sample_index;
            held_is_cp = sample_is_cp;
            held_last = sample_last;
            held_error = frame_error;

            for (stall_idx = 0; stall_idx < stall_cycles; stall_idx = stall_idx + 1) begin
                @(posedge clk);
                #1;
                expect_int(sample_valid, 1, "TX+CP backpressure keeps valid asserted");
                expect_int(sample_index, held_index, "TX+CP backpressure holds index");
                expect_int($signed(sample_re), held_re, "TX+CP backpressure holds real");
                expect_int($signed(sample_im), held_im, "TX+CP backpressure holds imag");
                expect_int(sample_is_cp, held_is_cp, "TX+CP backpressure holds CP flag");
                expect_int(sample_last, held_last, "TX+CP backpressure holds last");
                expect_int(frame_error, held_error, "TX+CP backpressure holds frame error");
                expect_int(bits_ready, 0, "TX+CP stall keeps next frame locked");
            end
            @(negedge clk);
        end
    endtask

    initial begin
        $readmemh(
            "verification/vectors/block08_ofdm_tx_cycle4_expected.mem",
            expected_samples
        );

        repeat (3) @(posedge clk);
        #1;
        expect_int(bits_ready, 0, "reset closes complete TX bit input");
        expect_int(sample_valid, 0, "reset keeps complete TX output invalid");
        expect_int(ifft_busy, 0, "reset clears complete TX IFFT busy");
        expect_int(total_saturation_count, 0, "reset clears complete TX saturation count");
        expect_int(frame_error, 0, "reset clears complete TX frame error");

        @(negedge clk);
        resetn = 1'b1;
        #1;
        expect_int(bits_ready, 1, "released reset opens first complete TX input slot");

        accepted_pairs = 0;
        for (idx = 0; idx < 48; idx = idx + 1)
            send_pair(idx);
        expect_int(accepted_pairs, 48, "complete TX accepts exactly 48 QPSK pairs");

        // Hold a candidate from the following OFDM symbol. The outer wrapper
        // must reject it not only during IFFT processing, but also while CP
        // output is being emitted.
        bits_in = 2'b00;
        bits_valid = 1'b1;

        wait_cycles = 0;
        while (!sample_valid && (wait_cycles < 1000)) begin
            @(posedge clk);
            #1;
            expect_int(bits_ready, 0, "complete TX blocks 49th pair before CP output");
            wait_cycles = wait_cycles + 1;
        end
        expect_int(sample_valid, 1, "complete mapped OFDM symbol reaches CP output");
        expect_int(bits_ready, 0, "complete TX stays locked at CP output start");
        expect_int(total_saturation_count, 0, "complete mapped OFDM transform is unsaturated");
        expect_int(frame_error, 0, "complete mapped OFDM symbol has no CP frame error");

        // Consume the exact 80-sample symbol. Stall once in the CP and once
        // in the payload to prove the complete output contract is stable.
        for (idx = 0; idx < 80; idx = idx + 1) begin
            @(negedge clk);
            if (idx == 5)
                stall_current_sample(idx, 2);
            if (idx == 67)
                stall_current_sample(idx, 3);

            sample_ready = 1'b1;
            #1;
            check_current_sample(idx);
            @(posedge clk);
            #1;
        end

        sample_ready = 1'b0;
        // The final handshake clears the outer frame lock. Remove the held
        // candidate before the next rising edge can turn it into pair 0 of a
        // new frame.
        @(negedge clk);
        bits_valid = 1'b0;
        #1;
        expect_int(sample_valid, 0, "sample 79 handshake completes TX+CP frame");
        expect_int(bits_ready, 1, "completed TX+CP frame rearms bit input");
        expect_int(ifft_busy, 0, "completed TX+CP frame leaves IFFT idle");
        expect_int(frame_error, 0, "completed TX+CP frame clears frame error");
        expect_int(accepted_pairs, 48, "held 49th pair was never prefetched");

        // Start a partial second frame, then reset. The complete wrapper must
        // discard all partial mapper/allocator/IFFT/CP and frame-lock state.
        for (idx = 0; idx < 5; idx = idx + 1)
            send_pair(idx);
        expect_int(accepted_pairs, 53, "partial second frame accepts five pairs before reset");

        @(negedge clk);
        resetn = 1'b0;
        @(posedge clk);
        #1;
        expect_int(bits_ready, 0, "reset closes TX+CP bit input after partial frame");
        expect_int(sample_valid, 0, "reset discards partial TX+CP frame");
        expect_int(ifft_busy, 0, "reset clears TX+CP IFFT busy");
        expect_int(total_saturation_count, 0, "reset clears TX+CP saturation count");
        expect_int(frame_error, 0, "reset clears TX+CP frame error");

        @(negedge clk);
        resetn = 1'b1;
        #1;
        expect_int(bits_ready, 1, "post-reset TX+CP path is ready for a fresh frame");

        if (errors == 0) begin
            $display("PASS tb_ofdm_tx_cp16_path");
        end else begin
            $display("FAIL tb_ofdm_tx_cp16_path errors=%0d", errors);
            $fatal(1);
        end
        $finish;
    end

endmodule
