`timescale 1ns/1ps

module tb_ofdm_tx_mapper_ifft_path;

    reg clk = 1'b0;
    reg resetn = 1'b0;

    reg bits_valid = 1'b0;
    wire bits_ready;
    reg [1:0] bits_in = 2'b00;

    wire sample_valid;
    reg sample_ready = 1'b0;
    wire signed [15:0] sample_re;
    wire signed [15:0] sample_im;
    wire [5:0] sample_index;
    wire sample_last;
    wire ifft_busy;
    wire [15:0] total_saturation_count;

    reg [31:0] expected_samples [0:63];

    integer errors = 0;
    integer accepted_pairs = 0;
    integer idx;
    integer wait_cycles;
    integer expected_re;
    integer expected_im;
    integer held_re;
    integer held_im;
    integer held_index;

    ofdm_tx_mapper_ifft_path dut (
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
        .sample_last(sample_last),
        .ifft_busy(ifft_busy),
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

            // Hold valid/data stable until the cycle whose rising edge sees
            // ready high. Count the transfer at that edge, not after NBA state
            // updates have changed ready for the following cycle.
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
            expected_re = $signed(expected_samples[expected_index][31:16]);
            expected_im = $signed(expected_samples[expected_index][15:0]);

            expect_int(sample_valid, 1, "TX path sample_valid during output frame");
            expect_int(sample_index, expected_index, "TX path natural sample index");
            expect_int($signed(sample_re), expected_re, "TX path exact sample real");
            expect_int($signed(sample_im), expected_im, "TX path exact sample imag");
            expect_int(sample_last, (expected_index == 63), "TX path sample_last only on 63");
            expect_int(total_saturation_count, 0, "canonical TX frame has zero IFFT saturation");
        end
    endtask

    initial begin
        $readmemh(
            "verification/vectors/block08_ofdm_tx_cycle4_expected.mem",
            expected_samples
        );

        repeat (3) @(posedge clk);
        #1;
        expect_int(bits_ready, 0, "reset keeps external bits_ready low");
        expect_int(sample_valid, 0, "reset keeps TX output invalid");
        expect_int(ifft_busy, 0, "reset clears TX IFFT busy");
        expect_int(total_saturation_count, 0, "reset clears TX saturation count");

        @(negedge clk);
        resetn = 1'b1;
        #1;
        expect_int(bits_ready, 1, "released reset opens first QPSK input slot");

        accepted_pairs = 0;
        for (idx = 0; idx < 48; idx = idx + 1)
            send_pair(idx);
        expect_int(accepted_pairs, 48, "exactly 48 QPSK data pairs accepted");

        // Keep a 49th candidate continuously asserted. frame_locked must keep
        // it from being accepted until sample 63 of this frame is consumed.
        bits_in = 2'b00;
        bits_valid = 1'b1;

        wait_cycles = 0;
        while (!sample_valid && (wait_cycles < 600)) begin
            @(posedge clk);
            #1;
            expect_int(bits_ready, 0, "frame lock blocks a 49th data pair");
            wait_cycles = wait_cycles + 1;
        end
        expect_int(sample_valid, 1, "mapped OFDM frame reaches IFFT output");
        expect_int(bits_ready, 0, "frame stays locked while output is pending");
        expect_int(total_saturation_count, 0, "mapped OFDM transform is unsaturated");

        // Consume all 64 exact fixed-point samples. Stall at sample 17 and
        // prove payload/index remain stable under downstream backpressure.
        for (idx = 0; idx < 64; idx = idx + 1) begin
            @(negedge clk);
            if (idx == 17) begin
                sample_ready = 1'b0;
                #1;
                check_current_sample(idx);
                held_re = $signed(sample_re);
                held_im = $signed(sample_im);
                held_index = sample_index;
                repeat (2) begin
                    @(posedge clk);
                    #1;
                    expect_int(sample_index, held_index, "TX backpressure holds sample index");
                    expect_int($signed(sample_re), held_re, "TX backpressure holds sample real");
                    expect_int($signed(sample_im), held_im, "TX backpressure holds sample imag");
                    expect_int(bits_ready, 0, "TX frame remains locked during output stall");
                end
                @(negedge clk);
            end

            sample_ready = 1'b1;
            #1;
            check_current_sample(idx);
            @(posedge clk);
            #1;
        end

        sample_ready = 1'b0;
        // sample63 cleared frame_locked after its handshake. Drop the held
        // 49th candidate before another rising edge can accept it.
        @(negedge clk);
        bits_valid = 1'b0;
        #1;
        expect_int(sample_valid, 0, "sample 63 handshake completes mapped TX frame");
        expect_int(bits_ready, 1, "completed mapped TX frame rearms input");
        expect_int(ifft_busy, 0, "completed mapped TX frame leaves IFFT idle");
        expect_int(accepted_pairs, 48, "held 49th candidate was never accepted");

        // Reset with a newly launched mapper item must discard all partial
        // state across mapper, bridge, allocator and IFFT.
        bits_valid = 1'b1;
        bits_in = 2'b11;
        @(posedge clk);
        @(negedge clk);
        resetn = 1'b0;
        @(posedge clk);
        #1;
        expect_int(bits_ready, 0, "reset closes TX bit input");
        expect_int(sample_valid, 0, "reset discards partial mapped TX frame");
        expect_int(ifft_busy, 0, "reset clears composed IFFT busy");
        expect_int(total_saturation_count, 0, "reset clears composed saturation count");

        @(negedge clk);
        bits_valid = 1'b0;
        resetn = 1'b1;

        if (errors == 0) begin
            $display("PASS tb_ofdm_tx_mapper_ifft_path");
        end else begin
            $display("FAIL tb_ofdm_tx_mapper_ifft_path errors=%0d", errors);
            $fatal(1);
        end
        $finish;
    end

endmodule
