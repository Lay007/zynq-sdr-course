`timescale 1ns/1ps

// OFDM through a frequency-selective (multipath) channel, issue #48:
// bits -> OFDM TX -> 3-path channel (+ optional CFO) -> CP removal -> FFT
// -> ofdm_channel_equalizer -> extractor -> ofdm_pilot_phase_corrector -> QPSK.
//
// The first transmitted symbol is the training symbol (the equalizer's known
// pattern), then SYMBOLS data symbols. The channel is
//     h = 0.5 + 0.25*exp(j*1.2)*z^-3 + 0.15*exp(-j*2.0)*z^-7
// (inside the 16-sample CP), so the channel phase differs between subcarriers
// by more than the +-45 degrees a QPSK slicer tolerates: one common phase per
// symbol is not enough. USE_CHANNEL_EQ=0 bypasses the per-subcarrier
// equalizer (the training symbol is then decoded as data and ignored) to show
// exactly that. CFO_PPM adds a carrier offset in 1e-6 cycles per sample.
// NORMALIZE=1 uses the zero-forcing equalizer (CORDIC 1/|G|^2).
//
// Grid spread: every decided component c is compared with sign * A, where A
// is the mean |c| over all data components; spread = rms(c - sign*A) / A. It
// says how well all carriers land on one amplitude grid, which a 16-QAM
// slicer would need; QPSK only needs the signs.
module tb_ofdm_tx_rx_multipath_loopback;
    parameter integer USE_CHANNEL_EQ = 1;
    parameter integer NORMALIZE = 0;
    parameter integer CFO_PPM = 0;
    parameter integer SYMBOLS = 4;
    localparam integer TOTAL_SYMBOLS = SYMBOLS + 1;
    localparam integer PAIRS = 48 * TOTAL_SYMBOLS;

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

    // ---- channel: 3 paths, delays 0/3/7, Q1.15 taps, optional CFO ----
    localparam integer D1 = 3;
    localparam integer D2 = 7;
    integer h0_re, h0_im, h1_re, h1_im, h2_re, h2_im;
    reg signed [15:0] hist_re [0:D2];
    reg signed [15:0] hist_im [0:D2];
    integer tx_sample_count = 0;
    integer acc_re, acc_im, j;
    real sample_phase;
    integer rot_c, rot_s, prod_re, prod_im;
    reg signed [15:0] mp_re, mp_im, channel_re, channel_im;

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
        if (tx_sample_valid && tx_sample_ready) begin
            for (j = D2; j > 0; j = j - 1) begin
                hist_re[j] <= hist_re[j-1];
                hist_im[j] <= hist_im[j-1];
            end
            hist_re[0] <= tx_sample_re;
            hist_im[0] <= tx_sample_im;
            tx_sample_count <= tx_sample_count + 1;
        end

    always @* begin
        // hist[d-1] is the sample d positions back from the current one.
        acc_re = tx_sample_re * h0_re - tx_sample_im * h0_im
               + hist_re[D1-1] * h1_re - hist_im[D1-1] * h1_im
               + hist_re[D2-1] * h2_re - hist_im[D2-1] * h2_im;
        acc_im = tx_sample_re * h0_im + tx_sample_im * h0_re
               + hist_re[D1-1] * h1_im + hist_im[D1-1] * h1_re
               + hist_re[D2-1] * h2_im + hist_im[D2-1] * h2_re;
        mp_re = round_clip_q15(acc_re);
        mp_im = round_clip_q15(acc_im);
        sample_phase = 6.283185307179586 * CFO_PPM * 1.0e-6 * tx_sample_count;
        rot_c = $rtoi($floor(32768.0 * $cos(sample_phase) + 0.5));
        rot_s = $rtoi($floor(32768.0 * $sin(sample_phase) + 0.5));
        if (rot_c > 32767) rot_c = 32767;
        if (rot_s > 32767) rot_s = 32767;
        prod_re = mp_re * rot_c - mp_im * rot_s;
        prod_im = mp_re * rot_s + mp_im * rot_c;
        channel_re = round_clip_q15(prod_re);
        channel_im = round_clip_q15(prod_im);
    end

    wire useful_valid, useful_ready, useful_last, cp_frame_error;
    wire signed [15:0] useful_re, useful_im;

    wire fft_bin_valid, fft_bin_ready, fft_bin_last;
    wire signed [15:0] fft_bin_re, fft_bin_im;
    wire [5:0] fft_bin_index;
    wire [15:0] fft_saturation_count;

    wire ce_valid, ce_ready, ce_last;
    wire signed [15:0] ce_re, ce_im;
    wire [5:0] ce_index;
    wire ce_trained;
    wire [15:0] ce_train_count;
    wire [31:0] ce_saturation_count;

    wire ext_bin_valid, ext_bin_ready, ext_bin_last;
    wire signed [15:0] ext_bin_re, ext_bin_im;
    wire [5:0] ext_bin_index;

    wire rx_data_valid, rx_data_ready, rx_data_last;
    wire signed [15:0] rx_data_re, rx_data_im;
    wire [5:0] rx_data_index;

    wire pilot_valid, pilot_ready;
    wire signed [15:0] pilot_re, pilot_im, pilot_ref_re;

    wire eq_valid, eq_ready, eq_last;
    wire signed [15:0] eq_re, eq_im;
    wire [5:0] eq_index;
    wire [31:0] eq_saturation_count;
    wire signed [15:0] applied_coeff_re, applied_coeff_im, last_phase;
    wire last_zero_energy;
    wire [15:0] corrected_symbols;

    wire rx_bits_valid, rx_bits_last;
    wire [1:0] rx_bits;
    wire [5:0] rx_bits_index;

    reg [1:0] expected_bits [0:PAIRS-1];
    integer rx_symbol;
    integer recovered_count = 0;
    integer bit_errors = 0;
    integer errors = 0;
    integer i;
    integer timeout;
    integer data_pairs;
    real abs_sum = 0.0;
    real comp_count = 0.0;
    real grid_amp;
    real err_sum;
    real spread;
    integer comp_log [0:2*PAIRS-1];
    integer sign_log [0:2*PAIRS-1];
    integer n_comp = 0;

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

    generate
        if (USE_CHANNEL_EQ != 0) begin : g_channel_eq
            ofdm_channel_equalizer #(.NORMALIZE(NORMALIZE)) channel_eq (
                .clk(clk), .resetn(resetn), .retrain(1'b0),
                .bin_valid(fft_bin_valid), .bin_ready(fft_bin_ready),
                .bin_re(fft_bin_re), .bin_im(fft_bin_im),
                .bin_index(fft_bin_index), .bin_last(fft_bin_last),
                .out_valid(ce_valid), .out_ready(ce_ready),
                .out_re(ce_re), .out_im(ce_im),
                .out_index(ce_index), .out_last(ce_last),
                .trained(ce_trained), .train_count(ce_train_count),
                .saturation_count(ce_saturation_count)
            );
            assign ext_bin_valid = ce_valid;
            assign ce_ready = ext_bin_ready;
            assign ext_bin_re = ce_re;
            assign ext_bin_im = ce_im;
            assign ext_bin_index = ce_index;
            assign ext_bin_last = ce_last;
        end else begin : g_bypass
            assign ext_bin_valid = fft_bin_valid;
            assign fft_bin_ready = ext_bin_ready;
            assign ext_bin_re = fft_bin_re;
            assign ext_bin_im = fft_bin_im;
            assign ext_bin_index = fft_bin_index;
            assign ext_bin_last = fft_bin_last;
            assign ce_trained = 1'b0;
            assign ce_train_count = 16'd0;
            assign ce_saturation_count = 32'd0;
        end
    endgenerate

    ofdm_subcarrier_extractor extractor (
        .resetn(resetn),
        .bin_valid(ext_bin_valid), .bin_ready(ext_bin_ready),
        .bin_re(ext_bin_re), .bin_im(ext_bin_im),
        .bin_index(ext_bin_index), .bin_last(ext_bin_last),
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

    // With the equalizer the training symbol never reaches the demapper, so
    // the first decoded symbol is data symbol 1; without it, symbol 0 (the
    // training symbol) is decoded too and simply not scored.
    initial rx_symbol = (USE_CHANNEL_EQ != 0) ? 1 : 0;

    always @(posedge clk) begin
        if (resetn) begin
            if (tx_frame_error || cp_frame_error) begin
                $display("FAIL framing error asserted");
                errors = errors + 1;
            end
            if (rx_bits_valid) begin
                if (rx_symbol >= 1) begin
                    comp_log[n_comp] = $signed(eq_re);
                    sign_log[n_comp] = expected_bits[rx_symbol * 48 + rx_bits_index][1] ? -1 : 1;
                    comp_log[n_comp + 1] = $signed(eq_im);
                    sign_log[n_comp + 1] = expected_bits[rx_symbol * 48 + rx_bits_index][0] ? -1 : 1;
                    n_comp = n_comp + 2;
                    if (rx_bits !== expected_bits[rx_symbol * 48 + rx_bits_index]) begin
                        bit_errors = bit_errors +
                            (rx_bits[1] !== expected_bits[rx_symbol * 48 + rx_bits_index][1]) +
                            (rx_bits[0] !== expected_bits[rx_symbol * 48 + rx_bits_index][0]);
                    end
                    recovered_count = recovered_count + 1;
                end
                if (rx_bits_last)
                    rx_symbol = rx_symbol + 1;
            end
        end
    end

    task automatic send_pair;
        input integer idx;
        reg [1:0] value;
        reg [5:0] d;
        begin
            d = idx % 48;
            if (idx < 48)
                // Training symbol: must match train_bits() in ofdm_channel_equalizer.v.
                value = {d[0] ^ d[3], d[1] ^ d[2] ^ d[4]};
            else
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
        h0_re = 16384;  h0_im = 0;                                           // 0.5
        h1_re = $rtoi($floor(0.25 * 32768.0 * $cos(1.2) + 0.5));             // 0.25 e^{j1.2}
        h1_im = $rtoi($floor(0.25 * 32768.0 * $sin(1.2) + 0.5));
        h2_re = $rtoi($floor(0.15 * 32768.0 * $cos(-2.0) + 0.5));            // 0.15 e^{-j2.0}
        h2_im = $rtoi($floor(0.15 * 32768.0 * $sin(-2.0) + 0.5));
        for (j = 0; j <= D2; j = j + 1) begin
            hist_re[j] = 16'sd0;
            hist_im[j] = 16'sd0;
        end

        repeat (4) @(posedge clk);
        resetn = 1'b1;
        repeat (2) @(posedge clk);

        for (i = 0; i < PAIRS; i = i + 1)
            send_pair(i);

        data_pairs = 48 * SYMBOLS;
        timeout = 0;
        while ((recovered_count < data_pairs) && (timeout < 12000 * TOTAL_SYMBOLS)) begin
            @(posedge clk);
            timeout = timeout + 1;
        end

        abs_sum = 0.0;
        for (i = 0; i < n_comp; i = i + 1)
            abs_sum = abs_sum + ((comp_log[i] < 0) ? -comp_log[i] : comp_log[i]);
        grid_amp = (n_comp > 0) ? abs_sum / n_comp : 1.0;
        err_sum = 0.0;
        for (i = 0; i < n_comp; i = i + 1)
            err_sum = err_sum + (comp_log[i] - sign_log[i] * grid_amp) * (comp_log[i] - sign_log[i] * grid_amp);
        spread = (n_comp > 0) ? 100.0 * $sqrt(err_sum / n_comp) / grid_amp : 0.0;
        $display("RESULT channel_eq=%0d normalize=%0d cfo_ppm=%0d data_symbols=%0d bit_errors=%0d bits=%0d trained=%0d ce_saturations=%0d grid_amp=%0.0f grid_spread_pct=%0.1f",
                 USE_CHANNEL_EQ, NORMALIZE, CFO_PPM, SYMBOLS, bit_errors, 2 * data_pairs, ce_trained, ce_saturation_count,
                 grid_amp, spread);
        if (recovered_count != data_pairs) begin
            $display("FAIL expected %0d recovered pairs, got %0d", data_pairs, recovered_count);
            errors = errors + 1;
        end
        if (bit_errors != 0) begin
            $display("FAIL BER nonzero: %0d/%0d bit errors", bit_errors, 2 * data_pairs);
            errors = errors + 1;
        end
        if (USE_CHANNEL_EQ != 0 && (!ce_trained || ce_train_count != 16'd1)) begin
            $display("FAIL channel equalizer trained=%0d train_count=%0d", ce_trained, ce_train_count);
            errors = errors + 1;
        end
        if (USE_CHANNEL_EQ != 0 && NORMALIZE != 0 && CFO_PPM == 0 &&
            (spread > 2.0 || grid_amp < 8028.0 || grid_amp > 8356.0)) begin
            $display("FAIL zero-forcing grid: amplitude %0.0f (expected 8192 +- 2%%), spread %0.1f%% (expected < 2%%)",
                     grid_amp, spread);
            errors = errors + 1;
        end
        if (tx_saturation_count != 16'd0) begin
            $display("FAIL unexpected TX saturation %0d", tx_saturation_count);
            errors = errors + 1;
        end

        if (errors == 0) begin
            $display("PASS: OFDM 3-path channel -> per-subcarrier equalizer recovered %0d/%0d data bits in %0d symbols after 1 training symbol, BER=0 (equalizer saturations %0d)",
                     2 * data_pairs, 2 * data_pairs, SYMBOLS, ce_saturation_count);
            $finish;
        end else begin
            $display("FAIL tb_ofdm_tx_rx_multipath_loopback errors=%0d", errors);
            $fatal(1);
        end
    end
endmodule
