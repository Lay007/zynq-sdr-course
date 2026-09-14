`timescale 1ns/1ps

// End-to-end deterministic flat-channel test for issue #48:
// bits -> OFDM TX -> +90 degree complex channel -> CP removal -> FFT
// -> data extraction -> one-tap equalizer (-90 degrees) -> QPSK decisions.
//
// The +j channel is deliberately applied in the time domain so the complete
// CP/FFT path sees a nontrivial complex channel. The equalizer receives the
// exact inverse coefficient W=-j in Q2.14. The expected result is BER=0 with
// no undocumented arithmetic saturation.
module tb_ofdm_tx_rx_equalized_loopback;
    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg resetn = 1'b0;
    reg bits_valid = 1'b0;
    wire bits_ready;
    reg [1:0] bits_in = 2'b00;

    wire tx_sample_valid;
    wire tx_sample_ready;
    wire signed [15:0] tx_sample_re;
    wire signed [15:0] tx_sample_im;
    wire tx_sample_last;
    wire [15:0] tx_saturation_count;
    wire tx_frame_error;

    // Flat channel H=+j: (I + jQ) * j = -Q + jI.
    wire signed [15:0] channel_re = -$signed(tx_sample_im);
    wire signed [15:0] channel_im = tx_sample_re;

    wire useful_valid;
    wire useful_ready;
    wire signed [15:0] useful_re;
    wire signed [15:0] useful_im;
    wire useful_last;
    wire cp_frame_error;

    wire fft_bin_valid;
    wire fft_bin_ready;
    wire signed [15:0] fft_bin_re;
    wire signed [15:0] fft_bin_im;
    wire [5:0] fft_bin_index;
    wire fft_bin_last;
    wire [15:0] fft_saturation_count;

    wire rx_data_valid;
    wire rx_data_ready;
    wire signed [15:0] rx_data_re;
    wire signed [15:0] rx_data_im;
    wire [5:0] rx_data_index;
    wire rx_data_last;

    wire eq_valid;
    wire eq_ready;
    wire signed [15:0] eq_re;
    wire signed [15:0] eq_im;
    wire [5:0] eq_index;
    wire eq_last;
    wire [31:0] eq_saturation_count;

    wire rx_bits_valid;
    wire [1:0] rx_bits;
    wire [5:0] rx_bits_index;

    reg [1:0] expected_bits [0:47];
    integer recovered_count = 0;
    integer bit_errors = 0;
    integer errors = 0;
    integer i;
    integer timeout;

    ofdm_tx_cp16_path tx (
        .clk(clk), .resetn(resetn),
        .bits_valid(bits_valid), .bits_ready(bits_ready), .bits_in(bits_in),
        .sample_valid(tx_sample_valid), .sample_ready(tx_sample_ready),
        .sample_re(tx_sample_re), .sample_im(tx_sample_im),
        .sample_index(), .sample_is_cp(), .sample_last(tx_sample_last),
        .ifft_busy(), .total_saturation_count(tx_saturation_count),
        .frame_error(tx_frame_error)
    );

    ofdm_cp16_remover cp_remove (
        .clk(clk), .resetn(resetn),
        .in_i(channel_re), .in_q(channel_im),
        .in_valid(tx_sample_valid), .in_ready(tx_sample_ready),
        .in_last(tx_sample_last),
        .out_i(useful_re), .out_q(useful_im),
        .out_valid(useful_valid), .out_ready(useful_ready),
        .out_last(useful_last), .frame_error(cp_frame_error)
    );

    ofdm_fft64_sequential fft (
        .clk(clk), .resetn(resetn),
        .sample_valid(useful_valid), .sample_ready(useful_ready),
        .sample_re(useful_re), .sample_im(useful_im),
        .bin_valid(fft_bin_valid), .bin_ready(fft_bin_ready),
        .bin_re(fft_bin_re), .bin_im(fft_bin_im),
        .bin_index(fft_bin_index), .bin_last(fft_bin_last),
        .busy(), .total_saturation_count(fft_saturation_count),
        .conjugation_saturation_count()
    );

    ofdm_subcarrier_extractor extractor (
        .resetn(resetn),
        .bin_valid(fft_bin_valid), .bin_ready(fft_bin_ready),
        .bin_re(fft_bin_re), .bin_im(fft_bin_im),
        .bin_index(fft_bin_index), .bin_last(fft_bin_last),
        .data_valid(rx_data_valid), .data_ready(rx_data_ready),
        .data_re(rx_data_re), .data_im(rx_data_im),
        .data_bin_index(), .data_index(rx_data_index), .data_last(rx_data_last),
        .pilot_valid(), .pilot_ready(1'b1),
        .pilot_re(), .pilot_im(), .pilot_bin_index(), .pilot_slot(), .pilot_ref_re()
    );

    ofdm_one_tap_equalizer equalizer (
        .clk(clk), .resetn(resetn),
        .in_valid(rx_data_valid), .in_ready(rx_data_ready),
        .in_re(rx_data_re), .in_im(rx_data_im),
        .coeff_re(16'sd0), .coeff_im(-16'sd16384),
        .in_index(rx_data_index), .in_last(rx_data_last),
        .out_valid(eq_valid), .out_ready(eq_ready),
        .out_re(eq_re), .out_im(eq_im),
        .out_index(eq_index), .out_last(eq_last),
        .saturation_count(eq_saturation_count)
    );

    ofdm_qpsk_demapper demapper (
        .resetn(resetn),
        .symbol_valid(eq_valid), .symbol_ready(eq_ready),
        .symbol_re(eq_re), .symbol_im(eq_im),
        .data_index(eq_index), .symbol_last(eq_last),
        .bits_valid(rx_bits_valid), .bits_ready(1'b1),
        .bits_out(rx_bits), .bits_index(rx_bits_index), .bits_last()
    );

    always @(posedge clk) begin
        if (resetn) begin
            if (tx_frame_error || cp_frame_error) begin
                $display("FAIL framing error asserted");
                errors = errors + 1;
            end

            if (rx_bits_valid) begin
                if (rx_bits_index > 6'd47) begin
                    $display("FAIL invalid recovered data index %0d", rx_bits_index);
                    errors = errors + 1;
                end else if (rx_bits !== expected_bits[rx_bits_index]) begin
                    $display("FAIL data index %0d expected=%b got=%b EQ=(%0d,%0d)",
                             rx_bits_index, expected_bits[rx_bits_index], rx_bits,
                             eq_re, eq_im);
                    bit_errors = bit_errors +
                        (rx_bits[1] !== expected_bits[rx_bits_index][1]) +
                        (rx_bits[0] !== expected_bits[rx_bits_index][0]);
                end
                recovered_count = recovered_count + 1;
            end
        end
    end

    task automatic send_pair;
        input integer idx;
        reg [1:0] value;
        begin
            value = {idx[0], (idx[1] ^ idx[0])};
            expected_bits[idx] = value;
            @(negedge clk);
            bits_in = value;
            bits_valid = 1'b1;
            while (!bits_ready)
                @(posedge clk);
            @(posedge clk);
            @(negedge clk);
            bits_valid = 1'b0;
        end
    endtask

    initial begin
        repeat (4) @(posedge clk);
        resetn = 1'b1;
        repeat (2) @(posedge clk);

        for (i = 0; i < 48; i = i + 1)
            send_pair(i);

        timeout = 0;
        while ((recovered_count < 48) && (timeout < 5000)) begin
            @(posedge clk);
            timeout = timeout + 1;
        end

        if (recovered_count != 48) begin
            $display("FAIL expected 48 recovered pairs, got %0d", recovered_count);
            errors = errors + 1;
        end
        if (bit_errors != 0) begin
            $display("FAIL BER nonzero: %0d/96 bit errors", bit_errors);
            errors = errors + 1;
        end
        if (tx_saturation_count != 16'd0) begin
            $display("FAIL unexpected TX saturation count %0d", tx_saturation_count);
            errors = errors + 1;
        end
        if (fft_saturation_count != 16'd0) begin
            $display("FAIL unexpected RX FFT saturation count %0d", fft_saturation_count);
            errors = errors + 1;
        end
        if (eq_saturation_count != 32'd0) begin
            $display("FAIL unexpected equalizer saturation count %0d", eq_saturation_count);
            errors = errors + 1;
        end

        if (errors == 0)
            $display("PASS: OFDM +90deg channel -> -90deg equalizer recovered 96/96 bits, BER=0");
        else begin
            $display("FAIL: equalized OFDM loopback errors=%0d", errors);
            $fatal(1);
        end
        $finish;
    end
endmodule
