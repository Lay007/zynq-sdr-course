`timescale 1ns/1ps

// End-to-end deterministic digital baseline for issue #48:
// bits -> mapper -> allocator -> IFFT -> CP insert/remove -> scaled FFT
// -> subcarrier extractor -> hard QPSK decisions.
//
// No channel/equalizer is present here by design. This test proves framing,
// carrier ordering and sign decisions before channel-estimation RTL is added.
module tb_ofdm_tx_rx_digital_loopback;
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
    wire tx_ifft_busy;
    wire [15:0] tx_saturation_count;
    wire tx_frame_error;

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
    wire fft_busy;
    wire [15:0] fft_saturation_count;
    wire [15:0] fft_conjugation_saturation_count;

    wire rx_data_valid;
    wire rx_data_ready;
    wire signed [15:0] rx_data_re;
    wire signed [15:0] rx_data_im;
    wire [5:0] rx_data_index;
    wire rx_data_last;
    wire rx_pilot_valid;

    wire rx_bits_valid;
    wire [1:0] rx_bits;
    wire [5:0] rx_bits_index;
    wire rx_bits_last;

    reg [1:0] expected_bits [0:47];
    integer recovered_count = 0;
    integer errors = 0;
    integer i;
    integer timeout;

    ofdm_tx_cp16_path tx (
        .clk(clk), .resetn(resetn),
        .bits_valid(bits_valid), .bits_ready(bits_ready), .bits_in(bits_in),
        .sample_valid(tx_sample_valid), .sample_ready(tx_sample_ready),
        .sample_re(tx_sample_re), .sample_im(tx_sample_im),
        .sample_index(), .sample_is_cp(), .sample_last(tx_sample_last),
        .ifft_busy(tx_ifft_busy),
        .total_saturation_count(tx_saturation_count),
        .frame_error(tx_frame_error)
    );

    ofdm_cp16_remover cp_remove (
        .clk(clk), .resetn(resetn),
        .in_i(tx_sample_re), .in_q(tx_sample_im),
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
        .busy(fft_busy),
        .total_saturation_count(fft_saturation_count),
        .conjugation_saturation_count(fft_conjugation_saturation_count)
    );

    ofdm_subcarrier_extractor extractor (
        .resetn(resetn),
        .bin_valid(fft_bin_valid), .bin_ready(fft_bin_ready),
        .bin_re(fft_bin_re), .bin_im(fft_bin_im),
        .bin_index(fft_bin_index), .bin_last(fft_bin_last),
        .data_valid(rx_data_valid), .data_ready(rx_data_ready),
        .data_re(rx_data_re), .data_im(rx_data_im),
        .data_bin_index(), .data_index(rx_data_index), .data_last(rx_data_last),
        .pilot_valid(rx_pilot_valid), .pilot_ready(1'b1),
        .pilot_re(), .pilot_im(), .pilot_bin_index(), .pilot_slot(), .pilot_ref_re()
    );

    ofdm_qpsk_demapper demapper (
        .resetn(resetn),
        .symbol_valid(rx_data_valid), .symbol_ready(rx_data_ready),
        .symbol_re(rx_data_re), .symbol_im(rx_data_im),
        .data_index(rx_data_index), .symbol_last(rx_data_last),
        .bits_valid(rx_bits_valid), .bits_ready(1'b1),
        .bits_out(rx_bits), .bits_index(rx_bits_index), .bits_last(rx_bits_last)
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
                    $display("FAIL data index %0d expected=%b got=%b I=%0d Q=%0d",
                             rx_bits_index, expected_bits[rx_bits_index], rx_bits,
                             rx_data_re, rx_data_im);
                    errors = errors + 1;
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
        if (tx_saturation_count != 16'd0) begin
            $display("FAIL unexpected TX saturation count %0d", tx_saturation_count);
            errors = errors + 1;
        end
        if (fft_saturation_count != 16'd0) begin
            $display("FAIL unexpected RX FFT saturation count %0d", fft_saturation_count);
            errors = errors + 1;
        end

        if (errors == 0)
            $display("PASS: OFDM TX->RX digital loopback recovered 96/96 bits with zero errors");
        else begin
            $display("FAIL: OFDM TX->RX digital loopback errors=%0d", errors);
            $fatal(1);
        end
        $finish;
    end
endmodule
