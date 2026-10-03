`timescale 1ns/1ps

// End-to-end pilot-corrected OFDM loopback for issue #48:
// bits -> OFDM TX -> channel rotated by ANGLE_DEG -> CP removal -> FFT
// -> extractor -> ofdm_pilot_phase_corrector -> QPSK decisions.
//
// Unlike tb_ofdm_tx_rx_equalized_loopback, nobody hands the equalizer its
// coefficient: the corrector estimates it from each symbol's own four pilots.
// ANGLE_DEG defaults to 120 degrees, well past the +-45 degree range a QPSK
// slicer tolerates, so an uncorrected or wrongly corrected symbol fails.
// Two OFDM symbols are sent back to back to exercise the symbol buffer and
// the backpressure between them.
//
// CFO_PPM adds a carrier frequency offset of CFO_PPM * 1e-6 cycles per sample:
// the channel phase then grows through every symbol (and inside it), so each
// symbol needs its own coefficient. The bench prints a RESULT line with the
// bit errors before PASS/FAIL, so tools/run_ofdm_cfo_sweep.py can map how much
// offset a common-phase correction tolerates.
module tb_ofdm_tx_rx_pilot_corrected_loopback;
    parameter integer ANGLE_DEG = 120;
    parameter integer CFO_PPM = 0;
    parameter integer SYMBOLS = 2;
    localparam integer PAIRS = 48 * SYMBOLS;

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

    // Flat channel exp(j*(ANGLE_DEG + 2*pi*CFO*n)) in Q1.15, applied in the
    // time domain; n counts the transmitted samples.
    real angle_rad;
    real sample_phase;
    integer tx_sample_count = 0;
    integer rot_c;
    integer rot_s;
    integer prod_re;
    integer prod_im;
    reg signed [15:0] channel_re;
    reg signed [15:0] channel_im;

    function automatic signed [15:0] round_clip_q15;
        input integer value;
        integer rounded;
        begin
            rounded = (value >= 0) ? ((value + 16384) >>> 15) : -(((-value) + 16384) >>> 15);
            if (rounded > 32767)
                round_clip_q15 = 16'sh7fff;
            else if (rounded < -32768)
                round_clip_q15 = 16'sh8000;
            else
                round_clip_q15 = rounded[15:0];
        end
    endfunction

    always @(posedge clk)
        if (tx_sample_valid && tx_sample_ready)
            tx_sample_count <= tx_sample_count + 1;

    always @* begin
        sample_phase = angle_rad + 6.283185307179586 * CFO_PPM * 1.0e-6 * tx_sample_count;
        rot_c = $rtoi($floor(32768.0 * $cos(sample_phase) + 0.5));
        rot_s = $rtoi($floor(32768.0 * $sin(sample_phase) + 0.5));
        if (rot_c > 32767) rot_c = 32767;
        if (rot_s > 32767) rot_s = 32767;
        prod_re = tx_sample_re * rot_c - tx_sample_im * rot_s;
        prod_im = tx_sample_re * rot_s + tx_sample_im * rot_c;
        channel_re = round_clip_q15(prod_re);
        channel_im = round_clip_q15(prod_im);
    end

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

    wire pilot_valid;
    wire pilot_ready;
    wire signed [15:0] pilot_re;
    wire signed [15:0] pilot_im;
    wire signed [15:0] pilot_ref_re;

    wire eq_valid;
    wire eq_ready;
    wire signed [15:0] eq_re;
    wire signed [15:0] eq_im;
    wire [5:0] eq_index;
    wire eq_last;
    wire [31:0] eq_saturation_count;
    wire signed [15:0] applied_coeff_re;
    wire signed [15:0] applied_coeff_im;
    wire signed [15:0] last_phase;
    wire last_zero_energy;
    wire [15:0] corrected_symbols;

    wire rx_bits_valid;
    wire [1:0] rx_bits;
    wire [5:0] rx_bits_index;
    wire rx_bits_last;

    reg [1:0] expected_bits [0:PAIRS-1];
    integer rx_symbol = 0;
    integer recovered_count = 0;
    integer bit_errors = 0;
    integer errors = 0;
    integer i;
    integer timeout;
    integer phase_error;
    integer expected_phase;

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
        .pilot_valid(pilot_valid), .pilot_ready(pilot_ready),
        .pilot_re(pilot_re), .pilot_im(pilot_im), .pilot_bin_index(),
        .pilot_slot(), .pilot_ref_re(pilot_ref_re)
    );

    ofdm_pilot_phase_corrector corrector (
        .clk(clk), .resetn(resetn),
        .data_valid(rx_data_valid), .data_ready(rx_data_ready),
        .data_re(rx_data_re), .data_im(rx_data_im),
        .data_index(rx_data_index), .data_last(rx_data_last),
        .pilot_valid(pilot_valid), .pilot_ready(pilot_ready),
        .pilot_re(pilot_re), .pilot_im(pilot_im), .pilot_ref_re(pilot_ref_re),
        .out_valid(eq_valid), .out_ready(eq_ready),
        .out_re(eq_re), .out_im(eq_im),
        .out_index(eq_index), .out_last(eq_last),
        .applied_coeff_re(applied_coeff_re), .applied_coeff_im(applied_coeff_im),
        .last_phase(last_phase), .last_zero_energy(last_zero_energy),
        .symbol_count(corrected_symbols),
        .saturation_count(eq_saturation_count)
    );

    ofdm_qpsk_demapper demapper (
        .resetn(resetn),
        .symbol_valid(eq_valid), .symbol_ready(eq_ready),
        .symbol_re(eq_re), .symbol_im(eq_im),
        .data_index(eq_index), .symbol_last(eq_last),
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
                if (rx_bits !== expected_bits[rx_symbol * 48 + rx_bits_index]) begin
                    $display("FAIL symbol %0d data index %0d expected=%b got=%b EQ=(%0d,%0d)",
                             rx_symbol, rx_bits_index,
                             expected_bits[rx_symbol * 48 + rx_bits_index], rx_bits, eq_re, eq_im);
                    bit_errors = bit_errors +
                        (rx_bits[1] !== expected_bits[rx_symbol * 48 + rx_bits_index][1]) +
                        (rx_bits[0] !== expected_bits[rx_symbol * 48 + rx_bits_index][0]);
                end
                recovered_count = recovered_count + 1;
                if (rx_bits_last)
                    rx_symbol = rx_symbol + 1;
            end
        end
    end

    task automatic send_pair;
        input integer idx;
        reg [1:0] value;
        begin
            // Different pattern per symbol so a symbol mix-up cannot pass.
            value = {idx[0], (idx[1] ^ idx[0] ^ idx[6])};
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
        angle_rad = ANGLE_DEG * 3.14159265358979 / 180.0;

        repeat (4) @(posedge clk);
        resetn = 1'b1;
        repeat (2) @(posedge clk);

        for (i = 0; i < PAIRS; i = i + 1)
            send_pair(i);

        timeout = 0;
        while ((recovered_count < PAIRS) && (timeout < 10000 * SYMBOLS)) begin
            @(posedge clk);
            timeout = timeout + 1;
        end

        if (recovered_count != PAIRS) begin
            $display("FAIL expected %0d recovered pairs, got %0d", PAIRS, recovered_count);
            errors = errors + 1;
        end
        if (bit_errors != 0) begin
            $display("FAIL BER nonzero: %0d/%0d bit errors", bit_errors, 2 * PAIRS);
            errors = errors + 1;
        end
        if (corrected_symbols != SYMBOLS) begin
            $display("FAIL corrector saw %0d symbols, expected %0d", corrected_symbols, SYMBOLS);
            errors = errors + 1;
        end
        if (last_zero_energy) begin
            $display("FAIL pilot energy reported as zero");
            errors = errors + 1;
        end
        // The tracker measures the channel angle (pi = 2^15 units); with a CFO,
        // the mean channel phase over the last symbol's 64 useful samples
        // (samples 16..79 of the last 80-sample symbol).
        expected_phase = $rtoi(((ANGLE_DEG / 180.0)
            + 2.0 * CFO_PPM * 1.0e-6 * (80.0 * (SYMBOLS - 1) + 16.0 + 31.5)) * 32768.0);
        expected_phase = ((expected_phase % 65536) + 65536) % 65536;
        if (expected_phase >= 32768) expected_phase = expected_phase - 65536;
        phase_error = last_phase - expected_phase;
        if (phase_error > 32767) phase_error = phase_error - 65536;
        if (phase_error < -32768) phase_error = phase_error + 65536;
        // With a CFO the data carriers leak into the pilot bins (ICI) and bias
        // the estimate in proportion to the offset (tools/ofdm_cfo_pilot_bias.py
        // reproduces the RTL value with a float model), so only the BER is
        // checked then; the phase is reported in the RESULT line.
        if ((CFO_PPM == 0) && (phase_error > 64 || phase_error < -64)) begin
            $display("FAIL measured channel phase %0d, expected about %0d", last_phase, expected_phase);
            errors = errors + 1;
        end
        if (tx_saturation_count != 16'd0 || eq_saturation_count != 32'd0) begin
            $display("FAIL unexpected saturation tx=%0d eq=%0d", tx_saturation_count, eq_saturation_count);
            errors = errors + 1;
        end

        $display("RESULT angle_deg=%0d cfo_ppm=%0d symbols=%0d bit_errors=%0d bits=%0d phase=%0d expected_phase=%0d",
                 ANGLE_DEG, CFO_PPM, SYMBOLS, bit_errors, 2 * PAIRS, last_phase, expected_phase);
        if (errors == 0) begin
            $display("PASS: OFDM %0d-degree channel -> pilot-corrected RX recovered %0d/%0d bits in %0d symbols, BER=0 (phase %0d, coeff=(%0d,%0d))",
                     ANGLE_DEG, 2 * PAIRS, 2 * PAIRS, SYMBOLS, last_phase, applied_coeff_re, applied_coeff_im);
            $finish;
        end else begin
            $display("FAIL tb_ofdm_tx_rx_pilot_corrected_loopback errors=%0d", errors);
            $fatal(1);
        end
    end
endmodule
