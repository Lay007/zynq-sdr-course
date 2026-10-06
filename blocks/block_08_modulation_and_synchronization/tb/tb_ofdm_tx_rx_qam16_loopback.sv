`timescale 1ns/1ps

// 16-QAM OFDM end to end, issue #48:
// 4-bit symbols -> OFDM TX (16-QAM) -> channel (multipath + CFO)
// -> ofdm_cfo_corrector (USE_CFO_CORR=1) -> CP removal -> FFT
// -> ofdm_channel_equalizer (zero-forcing) -> extractor
// -> ofdm_pilot_phase_corrector -> ofdm_qam16_demapper.
//
// The first symbol is the 16-QAM training symbol: the equalizer's QPSK
// training signs on the outer constellation points. CHANNEL selects
//   0: flat,
//   1: Lab 8.5 multipath  1 + 0.28 e^{j0.35} z^-2 + 0.12 e^{-j0.8} z^-4 (scaled by 0.7),
//   2: strong multipath   0.5 + 0.25 e^{j1.2} z^-3 + 0.15 e^{-j2.0} z^-7.
// CFO_PPM adds a carrier offset (1e-6 cycles per sample).
//
// The bench prints a RESULT line with the bit errors and the EVM against the
// ideal equalized grid (outer +-8192, inner +-8192/3), then requires BER = 0
// (unless REQUIRE_ZERO_BER = 0) and, when EVM_LIMIT_PCT > 0, an EVM below that
// limit.
//
// MODULATION = 0 runs QPSK through the same chain (ideal grid +-8192).
// ESN0_DB10 > 0 adds white Gaussian noise after the channel: Es/N0 per used
// subcarrier in tenths of a dB. In this chain a bin is X/64 and the FFT turns
// time-domain noise of variance 2*sigma^2 per sample into 2*sigma^2/64 per bin,
// so sigma = sqrt(|X|^2 / (128 * Es/N0)) with |X|^2 = 2 * 23170^2 (QPSK) or
// the 16-QAM average (the same energy). tools/run_ofdm_ber_sweep.py sweeps it.
module tb_ofdm_tx_rx_qam16_loopback;
    parameter integer MODULATION = 1;
    parameter integer ESN0_DB10 = 0;
    parameter integer REQUIRE_ZERO_BER = 1;
    parameter integer NOISE_SEED = 11;
    parameter integer CHANNEL = 1;
    parameter integer CFO_PPM = 0;
    parameter integer USE_CFO_CORR = 1;
    parameter integer SYMBOLS = 6;
    parameter integer EVM_LIMIT_PCT = 0;
    localparam integer TOTAL_SYMBOLS = SYMBOLS + 1;
    localparam integer PAIRS = 48 * TOTAL_SYMBOLS;
    localparam integer BITS_W = (MODULATION != 0) ? 4 : 2;

    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg resetn = 1'b0;
    reg bits_valid = 1'b0;
    wire bits_ready;
    reg [3:0] bits_in = 4'd0;

    wire tx_sample_valid, tx_sample_ready, tx_sample_last, tx_frame_error;
    wire signed [15:0] tx_sample_re, tx_sample_im;
    wire [15:0] tx_saturation_count;

    // ---- channel ----
    localparam integer MAXD = 7;
    integer d1, d2;
    integer h0_re, h0_im, h1_re, h1_im, h2_re, h2_im;
    reg signed [15:0] hist_re [0:MAXD];
    reg signed [15:0] hist_im [0:MAXD];
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

    // White Gaussian noise, one draw per transmitted sample.
    real noise_sigma;
    integer noise_seed = NOISE_SEED;
    integer noise_re = 0;
    integer noise_im = 0;
    integer sigma_int;
    always @(posedge clk)
        if (tx_sample_valid && tx_sample_ready && ESN0_DB10 > 0) begin
            noise_re <= $dist_normal(noise_seed, 0, sigma_int);
            noise_im <= $dist_normal(noise_seed, 0, sigma_int);
        end

    always @(posedge clk)
        if (tx_sample_valid && tx_sample_ready) begin
            for (j = MAXD; j > 0; j = j - 1) begin
                hist_re[j] <= hist_re[j-1];
                hist_im[j] <= hist_im[j-1];
            end
            hist_re[0] <= tx_sample_re;
            hist_im[0] <= tx_sample_im;
            tx_sample_count <= tx_sample_count + 1;
        end

    always @* begin
        acc_re = tx_sample_re * h0_re - tx_sample_im * h0_im
               + hist_re[d1-1] * h1_re - hist_im[d1-1] * h1_im
               + hist_re[d2-1] * h2_re - hist_im[d2-1] * h2_im;
        acc_im = tx_sample_re * h0_im + tx_sample_im * h0_re
               + hist_re[d1-1] * h1_im + hist_im[d1-1] * h1_re
               + hist_re[d2-1] * h2_im + hist_im[d2-1] * h2_re;
        mp_re = round_clip_q15(acc_re);
        mp_im = round_clip_q15(acc_im);
        sample_phase = 6.283185307179586 * CFO_PPM * 1.0e-6 * tx_sample_count;
        rot_c = $rtoi($floor(32768.0 * $cos(sample_phase) + 0.5));
        rot_s = $rtoi($floor(32768.0 * $sin(sample_phase) + 0.5));
        if (rot_c > 32767) rot_c = 32767;
        if (rot_s > 32767) rot_s = 32767;
        prod_re = mp_re * rot_c - mp_im * rot_s;
        prod_im = mp_re * rot_s + mp_im * rot_c;
        channel_re = round_clip_q15(prod_re + noise_re * 32768);
        channel_im = round_clip_q15(prod_im + noise_im * 32768);
    end

    // ---- receiver ----
    wire cc_valid, cc_ready, cc_last, cc_frame_error;
    wire signed [15:0] cc_re, cc_im;
    wire signed [23:0] cc_theta;
    wire [15:0] cc_symbols;

    wire useful_valid, useful_ready, useful_last, cp_frame_error;
    wire signed [15:0] useful_re, useful_im;
    wire fft_bin_valid, fft_bin_ready, fft_bin_last;
    wire signed [15:0] fft_bin_re, fft_bin_im;
    wire [5:0] fft_bin_index;
    wire ce_valid, ce_ready, ce_last, ce_trained;
    wire signed [15:0] ce_re, ce_im;
    wire [5:0] ce_index;
    wire [15:0] ce_train_count;
    wire [31:0] ce_saturation_count;
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
    wire [3:0] rx_bits;
    wire [1:0] rx_qpsk_bits;
    wire [5:0] rx_bits_index;

    ofdm_tx_cp16_path #(.MODULATION(MODULATION)) tx (
        .clk(clk), .resetn(resetn),
        .bits_valid(bits_valid), .bits_ready(bits_ready), .bits_in(bits_in[BITS_W-1:0]),
        .sample_valid(tx_sample_valid), .sample_ready(tx_sample_ready),
        .sample_re(tx_sample_re), .sample_im(tx_sample_im),
        .sample_index(), .sample_is_cp(), .sample_last(tx_sample_last),
        .ifft_busy(), .total_saturation_count(tx_saturation_count),
        .frame_error(tx_frame_error)
    );

    generate
        if (USE_CFO_CORR != 0) begin : g_cfo
            ofdm_cfo_corrector cfo_corr (
                .clk(clk), .resetn(resetn), .restart(1'b0),
                .in_valid(tx_sample_valid), .in_ready(tx_sample_ready),
                .in_re(channel_re), .in_im(channel_im), .in_last(tx_sample_last),
                .out_valid(cc_valid), .out_ready(cc_ready),
                .out_re(cc_re), .out_im(cc_im), .out_last(cc_last),
                .theta(cc_theta), .symbol_count(cc_symbols), .frame_error(cc_frame_error)
            );
        end else begin : g_no_cfo
            assign cc_valid = tx_sample_valid;
            assign tx_sample_ready = cc_ready;
            assign cc_re = channel_re;
            assign cc_im = channel_im;
            assign cc_last = tx_sample_last;
            assign cc_theta = 24'sd0;
            assign cc_symbols = 16'd0;
            assign cc_frame_error = 1'b0;
        end
    endgenerate

    ofdm_cp16_remover cp_remove (
        .clk(clk), .resetn(resetn),
        .in_i(cc_re), .in_q(cc_im),
        .in_valid(cc_valid), .in_ready(cc_ready), .in_last(cc_last),
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
        .busy(), .total_saturation_count(), .conjugation_saturation_count()
    );

    ofdm_channel_equalizer #(.NORMALIZE(1)) channel_eq (
        .clk(clk), .resetn(resetn), .retrain(1'b0),
        .bin_valid(fft_bin_valid), .bin_ready(fft_bin_ready),
        .bin_re(fft_bin_re), .bin_im(fft_bin_im),
        .bin_index(fft_bin_index), .bin_last(fft_bin_last),
        .out_valid(ce_valid), .out_ready(ce_ready),
        .out_re(ce_re), .out_im(ce_im), .out_index(ce_index), .out_last(ce_last),
        .trained(ce_trained), .train_count(ce_train_count), .saturation_count(ce_saturation_count)
    );

    ofdm_subcarrier_extractor extractor (
        .resetn(resetn),
        .bin_valid(ce_valid), .bin_ready(ce_ready),
        .bin_re(ce_re), .bin_im(ce_im), .bin_index(ce_index), .bin_last(ce_last),
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
        .out_re(eq_re), .out_im(eq_im), .out_index(eq_index), .out_last(eq_last),
        .applied_coeff_re(applied_coeff_re), .applied_coeff_im(applied_coeff_im),
        .last_phase(last_phase), .last_zero_energy(last_zero_energy),
        .symbol_count(corrected_symbols), .saturation_count(eq_saturation_count)
    );

    generate
        if (MODULATION != 0) begin : g_qam16
            ofdm_qam16_demapper demapper (
                .resetn(resetn),
                .symbol_valid(eq_valid), .symbol_ready(eq_ready),
                .symbol_re(eq_re), .symbol_im(eq_im),
                .data_index(eq_index), .symbol_last(eq_last),
                .bits_valid(rx_bits_valid), .bits_ready(1'b1),
                .bits_out(rx_bits), .bits_index(rx_bits_index), .bits_last(rx_bits_last)
            );
        end else begin : g_qpsk
            ofdm_qpsk_demapper demapper (
                .resetn(resetn),
                .symbol_valid(eq_valid), .symbol_ready(eq_ready),
                .symbol_re(eq_re), .symbol_im(eq_im),
                .data_index(eq_index), .symbol_last(eq_last),
                .bits_valid(rx_bits_valid), .bits_ready(1'b1),
                .bits_out(rx_qpsk_bits), .bits_index(rx_bits_index), .bits_last(rx_bits_last)
            );
            assign rx_bits = {2'b00, rx_qpsk_bits};
        end
    endgenerate

    // ---- scoring ----
    reg [3:0] expected_bits [0:PAIRS-1];
    integer rx_symbol = 1;       // the training symbol never reaches the demapper
    integer recovered_count = 0;
    integer bit_errors = 0;
    integer errors = 0;
    integer i, timeout, data_pairs;
    real err_sum = 0.0;
    real ref_sum = 0.0;
    real evm;
    integer ideal_re, ideal_im;
    reg [3:0] e;

    function automatic integer ideal_level;
        input sign_bit;
        input inner_bit;
        integer magnitude;
        begin
            magnitude = inner_bit ? 2731 : 8192;
            ideal_level = sign_bit ? -magnitude : magnitude;
        end
    endfunction

    always @(posedge clk) begin
        if (resetn) begin
            if (tx_frame_error || cp_frame_error || cc_frame_error) begin
                $display("FAIL framing error asserted");
                errors = errors + 1;
            end
            if (rx_bits_valid) begin
                e = expected_bits[rx_symbol * 48 + rx_bits_index];
                bit_errors = bit_errors + (rx_bits[1] !== e[1]) + (rx_bits[0] !== e[0]);
                if (MODULATION != 0) begin
                    bit_errors = bit_errors + (rx_bits[3] !== e[3]) + (rx_bits[2] !== e[2]);
                    ideal_re = ideal_level(e[3], e[2]);
                    ideal_im = ideal_level(e[1], e[0]);
                end else begin
                    ideal_re = ideal_level(e[1], 1'b0);
                    ideal_im = ideal_level(e[0], 1'b0);
                end
                err_sum = err_sum + 1.0 * ($signed(eq_re) - ideal_re) * ($signed(eq_re) - ideal_re)
                                  + 1.0 * ($signed(eq_im) - ideal_im) * ($signed(eq_im) - ideal_im);
                ref_sum = ref_sum + 1.0 * ideal_re * ideal_re + 1.0 * ideal_im * ideal_im;
                recovered_count = recovered_count + 1;
                if (rx_bits_last)
                    rx_symbol = rx_symbol + 1;
            end
        end
    end

    task automatic send_bits;
        input [3:0] value;
        begin
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

    reg [5:0] d;
    reg [3:0] value;
    initial begin
        case (CHANNEL)
            0: begin
                d1 = 1; d2 = 2;
                h0_re = 32767; h0_im = 0; h1_re = 0; h1_im = 0; h2_re = 0; h2_im = 0;
            end
            1: begin
                d1 = 2; d2 = 4;
                h0_re = $rtoi($floor(0.7 * 32768.0 + 0.5)); h0_im = 0;
                h1_re = $rtoi($floor(0.7 * 0.28 * 32768.0 * $cos(0.35) + 0.5));
                h1_im = $rtoi($floor(0.7 * 0.28 * 32768.0 * $sin(0.35) + 0.5));
                h2_re = $rtoi($floor(0.7 * 0.12 * 32768.0 * $cos(-0.8) + 0.5));
                h2_im = $rtoi($floor(0.7 * 0.12 * 32768.0 * $sin(-0.8) + 0.5));
            end
            default: begin
                d1 = 3; d2 = 7;
                h0_re = 16384; h0_im = 0;
                h1_re = $rtoi($floor(0.25 * 32768.0 * $cos(1.2) + 0.5));
                h1_im = $rtoi($floor(0.25 * 32768.0 * $sin(1.2) + 0.5));
                h2_re = $rtoi($floor(0.15 * 32768.0 * $cos(-2.0) + 0.5));
                h2_im = $rtoi($floor(0.15 * 32768.0 * $sin(-2.0) + 0.5));
            end
        endcase
        for (j = 0; j <= MAXD; j = j + 1) begin
            hist_re[j] = 16'sd0;
            hist_im[j] = 16'sd0;
        end
        // |X|^2 = 2 * 23170^2 for QPSK, (10362^2 + 31086^2) for 16-QAM (equal by design).
        noise_sigma = (ESN0_DB10 > 0)
            ? $sqrt(2.0 * 23170.0 * 23170.0 / (128.0 * $pow(10.0, ESN0_DB10 / 100.0)))
            : 0.0;
        sigma_int = $rtoi(noise_sigma + 0.5);

        repeat (4) @(posedge clk);
        resetn = 1'b1;
        repeat (2) @(posedge clk);

        for (i = 0; i < PAIRS; i = i + 1) begin
            d = i % 48;
            if (i < 48)
                // Training symbol: train_bits() signs (16-QAM: on the outer points).
                value = (MODULATION != 0) ? {d[0] ^ d[3], 1'b0, d[1] ^ d[2] ^ d[4], 1'b0}
                                          : {2'b00, d[0] ^ d[3], d[1] ^ d[2] ^ d[4]};
            else if (MODULATION != 0)
                value = {i[0], i[1] ^ i[6], i[2] ^ i[5], i[3] ^ i[1] ^ i[7]};
            else
                value = {2'b00, i[0], i[1] ^ i[0] ^ i[6]};
            expected_bits[i] = value;
            send_bits(value);
        end

        data_pairs = 48 * SYMBOLS;
        timeout = 0;
        while ((recovered_count < data_pairs) && (timeout < 20000 * TOTAL_SYMBOLS)) begin
            @(posedge clk);
            timeout = timeout + 1;
        end

        evm = (ref_sum > 0.0) ? 100.0 * $sqrt(err_sum / ref_sum) : 0.0;
        $display("RESULT modulation=%0d channel=%0d cfo_ppm=%0d cfo_corr=%0d esn0_db10=%0d sigma=%0d data_symbols=%0d bit_errors=%0d bits=%0d evm_pct=%0.2f theta=%0d ce_sat=%0d",
                 MODULATION, CHANNEL, CFO_PPM, USE_CFO_CORR, ESN0_DB10, sigma_int, SYMBOLS, bit_errors,
                 BITS_W * data_pairs, evm, cc_theta, ce_saturation_count);
        if (recovered_count != data_pairs) begin
            $display("FAIL expected %0d recovered symbols, got %0d", data_pairs, recovered_count);
            errors = errors + 1;
        end
        if (REQUIRE_ZERO_BER != 0 && bit_errors != 0) begin
            $display("FAIL BER nonzero: %0d/%0d bit errors", bit_errors, BITS_W * data_pairs);
            errors = errors + 1;
        end
        if (EVM_LIMIT_PCT > 0 && evm > EVM_LIMIT_PCT) begin
            $display("FAIL EVM %0.2f %% above the %0d %% limit", evm, EVM_LIMIT_PCT);
            errors = errors + 1;
        end

        if (errors == 0) begin
            $display("PASS: OFDM (MODULATION=%0d) channel %0d, CFO %0d ppm -> %0d bit errors in %0d bits, %0d symbols, EVM %0.2f %%",
                     MODULATION, CHANNEL, CFO_PPM, bit_errors, BITS_W * data_pairs, SYMBOLS, evm);
            $finish;
        end else begin
            $display("FAIL tb_ofdm_tx_rx_qam16_loopback errors=%0d", errors);
            $fatal(1);
        end
    end
endmodule
