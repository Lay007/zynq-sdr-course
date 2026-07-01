// Course-specific AD9361 sample-domain bridge for the deterministic BPSK core.
//
// Control words arrive from the PS-side axi_gpreg block on sys_cpu_clk.
// The modem itself runs on the divided AD9361 sample clock, so this bridge
// captures quasi-static configuration words, generates a one-shot start pulse,
// and returns stable status/counter snapshots back to the PS clock domain.

`timescale 1ns/1ps

module bpsk_zynq_ber_gpreg_bridge #(
    parameter integer W = 16,
    parameter integer SPS = 8,
    parameter integer INDEX_W = 16,
    parameter integer MAX_FRAME_BITS = 512,
    parameter integer PHASE_W = 3,
    parameter integer FLUSH_SYMBOLS = 16,
    parameter MEM_FILE = "bpsk_frame_bits.mem",
    parameter COEF_FILE = "bpsk_rrc_tx_fir_taps.mem"
) (
    input  wire                     ctrl_clk,
    input  wire                     ctrl_resetn,
    input  wire                     adc_input_clk,
    input  wire                     adc_input_reset,
    input  wire                     adc_input_enable,
    input  wire                     adc_input_valid,
    input  wire signed [W-1:0]      adc_input_i,
    input  wire signed [W-1:0]      adc_input_q,
    input  wire                     sample_clk,
    input  wire                     sample_resetn,
    input  wire [31:0]              gp_ctrl,
    input  wire [31:0]              gp_frame_bit_count,
    input  wire [31:0]              gp_preamble_count,
    input  wire [31:0]              gp_start_offset,
    output wire [31:0]              gp_status,
    output wire [31:0]              gp_received_bits,
    output wire [31:0]              gp_total_errors,
    output wire [31:0]              gp_signature,
    output wire [31:0]              gp_tx_valid_count,
    output wire [31:0]              gp_rx_valid_count,
    output wire [31:0]              gp_adc_input_debug,
    output wire [31:0]              gp_capture_debug,
    output wire                     tx_path_active,
    output wire                     burst_out_valid,
    output wire signed [W-1:0]      burst_out_i,
    output wire signed [W-1:0]      burst_out_q,
    input  wire                     capture_in_valid,
    input  wire signed [W-1:0]      capture_in_i,
    input  wire signed [W-1:0]      capture_in_q
);

localparam [31:0] SIGNATURE = 32'h4250534B; // "BPSK"

wire sample_rst = ~sample_resetn;

// Dual-modem plane. gp_ctrl[4] selects which core drives the DAC mux and the
// status/counter registers: 0 = BPSK (bit-identical to the original bridge),
// 1 = QPSK. Both cores are always instantiated and share the sample-domain
// TX/RX plane, the start pulse and the ADC capture stream; only the selected
// core's TX reaches the DAC and only its counters are reported. Adding the
// second core is a second LUT-based RRC pair (xc7z020 headroom is ample:
// ~24% LUT / 13% DSP / 3% BRAM before this), DSP/BRAM untouched.
wire mod_qpsk = control_sync[4];

wire bpsk_busy;
wire bpsk_done;
wire bpsk_timed_out;
wire [INDEX_W-1:0] bpsk_received_bits;
wire [INDEX_W-1:0] bpsk_total_errors;
wire [INDEX_W-1:0] bpsk_payload_errors;
wire bpsk_recovered_valid_debug;
wire bpsk_recovered_bit_debug;
wire bpsk_symbol_valid_debug;
wire signed [W-1:0] bpsk_symbol_i_debug;
wire bpsk_tx_valid;
wire signed [W-1:0] bpsk_tx_i;
wire signed [W-1:0] bpsk_tx_q;

wire qpsk_busy;
wire qpsk_done;
wire qpsk_timed_out;
wire [INDEX_W-1:0] qpsk_received_symbols;
wire [INDEX_W-1:0] qpsk_total_bit_errors;
wire qpsk_symbol_valid_debug;
wire signed [W-1:0] qpsk_symbol_i_debug;
wire signed [W-1:0] qpsk_symbol_q_debug;
wire qpsk_tx_valid;
wire signed [W-1:0] qpsk_tx_i;
wire signed [W-1:0] qpsk_tx_q;

// Modulation-selected views consumed by the rest of the bridge unchanged.
wire core_busy       = mod_qpsk ? qpsk_busy      : bpsk_busy;
wire core_done       = mod_qpsk ? qpsk_done      : bpsk_done;
wire core_timed_out  = mod_qpsk ? qpsk_timed_out : bpsk_timed_out;
wire [INDEX_W-1:0] received_bits  = mod_qpsk ? qpsk_received_symbols : bpsk_received_bits;
wire [INDEX_W-1:0] total_errors   = mod_qpsk ? qpsk_total_bit_errors : bpsk_total_errors;
wire [INDEX_W-1:0] payload_errors = mod_qpsk ? {INDEX_W{1'b0}}       : bpsk_payload_errors;
wire recovered_valid_debug = mod_qpsk ? 1'b0 : bpsk_recovered_valid_debug;
wire recovered_bit_debug   = mod_qpsk ? 1'b0 : bpsk_recovered_bit_debug;
wire symbol_valid_debug    = mod_qpsk ? qpsk_symbol_valid_debug : bpsk_symbol_valid_debug;
wire signed [W-1:0] symbol_i_debug = mod_qpsk ? qpsk_symbol_i_debug : bpsk_symbol_i_debug;

(* ASYNC_REG = "TRUE" *) reg [31:0] control_meta = 32'd0;
(* ASYNC_REG = "TRUE" *) reg [31:0] control_sync = 32'd0;
reg [31:0] control_sync_d = 32'd0;
(* ASYNC_REG = "TRUE" *) reg [31:0] frame_meta = 32'd0;
(* ASYNC_REG = "TRUE" *) reg [31:0] frame_sync = 32'd0;
(* ASYNC_REG = "TRUE" *) reg [31:0] preamble_meta = 32'd0;
(* ASYNC_REG = "TRUE" *) reg [31:0] preamble_sync = 32'd0;
(* ASYNC_REG = "TRUE" *) reg [31:0] offset_meta = 32'd0;
(* ASYNC_REG = "TRUE" *) reg [31:0] offset_sync = 32'd0;

reg [INDEX_W-1:0] frame_bit_count_cfg = {INDEX_W{1'b0}};
reg [INDEX_W-1:0] preamble_count_cfg = {INDEX_W{1'b0}};
reg [INDEX_W-1:0] start_offset_cfg = {INDEX_W{1'b0}};
reg start_pulse_sample = 1'b0;
reg tx_path_active_sample = 1'b0;
reg done_sticky_sample = 1'b0;
reg timeout_sticky_sample = 1'b0;
reg [INDEX_W-1:0] received_bits_sample = {INDEX_W{1'b0}};
reg [INDEX_W-1:0] total_errors_sample = {INDEX_W{1'b0}};
reg [INDEX_W-1:0] payload_errors_sample = {INDEX_W{1'b0}};
reg [31:0] tx_valid_count_sample = 32'd0;
reg [31:0] rx_valid_count_sample = 32'd0;
reg adc_input_valid_seen_any_sample = 1'b0;
reg adc_input_nonzero_seen_any_sample = 1'b0;
reg adc_input_enable_seen_any_sample = 1'b0;
reg [14:0] adc_input_valid_count_lsb_sample = 15'd0;
reg [15:0] adc_input_clk_counter_sample = 16'd0;
reg capture_valid_seen_any_sample = 1'b0;
reg capture_nonzero_seen_any_sample = 1'b0;
reg capture_valid_while_active_seen_any_sample = 1'b0;
reg capture_i_negative_seen_any_sample = 1'b0;
reg capture_q_negative_seen_any_sample = 1'b0;
reg [12:0] capture_valid_count_lsb_sample = 13'd0;
reg [13:0] capture_peak_abs_sample = 14'd0;
reg recovered_valid_seen_any_sample = 1'b0;
reg recovered_one_seen_any_sample = 1'b0;
reg decision_negative_seen_any_sample = 1'b0;
reg decision_nonzero_seen_any_sample = 1'b0;
reg [8:0] recovered_valid_count_lsb_sample = 9'd0;
reg [8:0] recovered_one_count_lsb_sample = 9'd0;
reg [9:0] decision_negative_count_lsb_sample = 10'd0;

(* ASYNC_REG = "TRUE" *) reg [31:0] status_meta_ctrl = 32'd0;
(* ASYNC_REG = "TRUE" *) reg [31:0] status_sync_ctrl = 32'd0;
(* ASYNC_REG = "TRUE" *) reg [31:0] received_meta_ctrl = 32'd0;
(* ASYNC_REG = "TRUE" *) reg [31:0] received_sync_ctrl = 32'd0;
(* ASYNC_REG = "TRUE" *) reg [31:0] error_counts_meta_ctrl = 32'd0;
(* ASYNC_REG = "TRUE" *) reg [31:0] error_counts_sync_ctrl = 32'd0;
(* ASYNC_REG = "TRUE" *) reg [31:0] tx_valid_meta_ctrl = 32'd0;
(* ASYNC_REG = "TRUE" *) reg [31:0] tx_valid_sync_ctrl = 32'd0;
(* ASYNC_REG = "TRUE" *) reg [31:0] rx_valid_meta_ctrl = 32'd0;
(* ASYNC_REG = "TRUE" *) reg [31:0] rx_valid_sync_ctrl = 32'd0;
(* ASYNC_REG = "TRUE" *) reg [14:0] adc_input_debug_meta_ctrl = 15'd0;
(* ASYNC_REG = "TRUE" *) reg [14:0] adc_input_debug_sync_ctrl = 15'd0;
(* ASYNC_REG = "TRUE" *) reg [15:0] adc_input_counter_meta_ctrl = 16'd0;
(* ASYNC_REG = "TRUE" *) reg [15:0] adc_input_counter_sync_ctrl = 16'd0;
(* ASYNC_REG = "TRUE" *) reg adc_input_reset_meta_ctrl = 1'b0;
(* ASYNC_REG = "TRUE" *) reg adc_input_reset_sync_ctrl = 1'b0;
(* ASYNC_REG = "TRUE" *) reg [31:0] capture_debug_meta_ctrl = 32'd0;
(* ASYNC_REG = "TRUE" *) reg [31:0] capture_debug_sync_ctrl = 32'd0;

wire start_edge = control_sync[0] && !control_sync_d[0];
wire clear_done_edge = control_sync[1] && !control_sync_d[1];
wire [1:0] rx_decision_mode = control_sync[3:2];
wire adc_input_sample_nonzero = (adc_input_i != {W{1'b0}}) || (adc_input_q != {W{1'b0}});
wire capture_sample_nonzero = (capture_in_i != {W{1'b0}}) || (capture_in_q != {W{1'b0}});

function [W:0] abs_wide;
    input signed [W-1:0] value;
    begin
        if (value[W-1]) begin
            abs_wide = {1'b0, (~value + {{(W-1){1'b0}}, 1'b1})};
        end else begin
            abs_wide = {1'b0, value};
        end
    end
endfunction

wire [W:0] capture_abs_i = abs_wide(capture_in_i);
wire [W:0] capture_abs_q = abs_wide(capture_in_q);
wire [W:0] capture_abs_max = (capture_abs_i >= capture_abs_q) ? capture_abs_i : capture_abs_q;
wire [13:0] capture_peak_abs_saturated =
    (capture_abs_max > 17'd16383) ? 14'h3FFF : capture_abs_max[13:0];
wire [W:0] adc_input_abs_i = abs_wide(adc_input_i);
wire [W:0] adc_input_abs_q = abs_wide(adc_input_q);
wire [W:0] adc_input_abs_max = (adc_input_abs_i >= adc_input_abs_q) ? adc_input_abs_i : adc_input_abs_q;
// The cf-ad9361-lpc RX channels report `in_voltageN_type = le:S12/16>>0`, i.e. the
// ADC samples on the fabric tap are already SIGNED 12-bit sign-extended into 16
// bits (two's complement), NOT offset-binary. Feed them to the RX chain directly.
// The earlier ad9361_offset_binary12_to_signed16() conversion flipped bit 11 and
// corrupted the already-two's-complement samples with a sign-dependent +/-2048
// shift, which was the root cause of the ~40% BER floor seen in both OTA and
// AD9361 coherent digital loopback (where there is no carrier offset at all).
wire signed [W-1:0] capture_in_i_fmt = capture_in_i;
wire signed [W-1:0] capture_in_q_fmt = capture_in_q;

bpsk_zynq_ber_top #(
    .W(W),
    .SPS(SPS),
    .INDEX_W(INDEX_W),
    .MAX_FRAME_BITS(MAX_FRAME_BITS),
    .PHASE_W(PHASE_W),
    .FLUSH_SYMBOLS(FLUSH_SYMBOLS),
    // Fixed-phase symbol sampler. With the gap-free TX prefetch (no DAC-FIFO
    // under-run) the looped stream is a clean SPS samples/symbol burst that the
    // 8-bit frame-sync in bpsk_ber_counter aligns to full-frame BER=0. The Gardner
    // loop was tried here but mis-tracks this short loopback burst and is worse; it
    // stays available (TIMING_RECOVERY=1) for genuinely drifted streams. Residual
    // per-burst sampling-phase jitter (AD9361 loopback latency) is handled by a host
    // retry until BER=0.
    .TIMING_RECOVERY(0),
    .MEM_FILE(MEM_FILE),
    .COEF_FILE(COEF_FILE)
) core_i (
    .clk(sample_clk),
    .rst(sample_rst),
    .start(start_pulse_sample),
    .frame_bit_count(frame_bit_count_cfg),
    .preamble_count(preamble_count_cfg),
    .start_offset(start_offset_cfg),
    .busy(bpsk_busy),
    .done(bpsk_done),
    .tx_valid(bpsk_tx_valid),
    .tx_i(bpsk_tx_i),
    .tx_q(bpsk_tx_q),
    .rx_valid(capture_in_valid && tx_path_active_sample),
    .rx_i(capture_in_i_fmt),
    .rx_q(capture_in_q_fmt),
    .rx_decision_mode(rx_decision_mode),
    .timed_out(bpsk_timed_out),
    .received_bits(bpsk_received_bits),
    .total_errors(bpsk_total_errors),
    .payload_errors(bpsk_payload_errors),
    .debug_recovered_valid(bpsk_recovered_valid_debug),
    .debug_recovered_bit(bpsk_recovered_bit_debug),
    .debug_symbol_valid(bpsk_symbol_valid_debug),
    .debug_symbol_i(bpsk_symbol_i_debug)
);

// QPSK counterpart (Block 5 qpsk_zynq_ber_top). Reuses the shared upsampler /
// RRC / sampler; gp_frame_bit_count is reinterpreted as the QPSK *symbol* count
// (2 bits/symbol) and the fixed-phase sampler is aligned by gp_start_offset,
// swept by the host until BER=0 exactly like the BPSK path. Same frame-bit and
// RRC coefficient .mem files.
qpsk_zynq_ber_top #(
    .W(W),
    .SPS(SPS),
    .INDEX_W(INDEX_W),
    .MAX_FRAME_BITS(MAX_FRAME_BITS),
    .PHASE_W(PHASE_W),
    .FLUSH_SYMBOLS(FLUSH_SYMBOLS),
    .MEM_FILE(MEM_FILE),
    .COEF_FILE(COEF_FILE)
) qpsk_core_i (
    .clk(sample_clk),
    .rst(sample_rst),
    .start(start_pulse_sample),
    .symbol_count(frame_bit_count_cfg),
    .start_offset(start_offset_cfg),
    .busy(qpsk_busy),
    .done(qpsk_done),
    .tx_valid(qpsk_tx_valid),
    .tx_i(qpsk_tx_i),
    .tx_q(qpsk_tx_q),
    .rx_valid(capture_in_valid && tx_path_active_sample),
    .rx_i(capture_in_i_fmt),
    .rx_q(capture_in_q_fmt),
    .timed_out(qpsk_timed_out),
    .received_symbols(qpsk_received_symbols),
    .total_bit_errors(qpsk_total_bit_errors),
    .debug_symbol_valid(qpsk_symbol_valid_debug),
    .debug_symbol_i(qpsk_symbol_i_debug),
    .debug_symbol_q(qpsk_symbol_q_debug)
);

always @(posedge adc_input_clk) begin
    if (adc_input_reset) begin
        adc_input_valid_seen_any_sample <= 1'b0;
        adc_input_nonzero_seen_any_sample <= 1'b0;
        adc_input_enable_seen_any_sample <= 1'b0;
        adc_input_valid_count_lsb_sample <= 15'd0;
        adc_input_clk_counter_sample <= 16'd0;
    end else begin
        adc_input_clk_counter_sample <= adc_input_clk_counter_sample + 1'b1;
        if (adc_input_enable) begin
            adc_input_enable_seen_any_sample <= 1'b1;
        end
        if (adc_input_valid) begin
            adc_input_valid_seen_any_sample <= 1'b1;
            if (adc_input_valid_count_lsb_sample != 15'h7FFF) begin
                adc_input_valid_count_lsb_sample <= adc_input_valid_count_lsb_sample + 1'b1;
            end
            if (adc_input_sample_nonzero) begin
                adc_input_nonzero_seen_any_sample <= 1'b1;
            end
        end
    end
end

always @(posedge sample_clk) begin
    if (!sample_resetn) begin
        control_meta <= 32'd0;
        control_sync <= 32'd0;
        control_sync_d <= 32'd0;
        frame_meta <= 32'd0;
        frame_sync <= 32'd0;
        preamble_meta <= 32'd0;
        preamble_sync <= 32'd0;
        offset_meta <= 32'd0;
        offset_sync <= 32'd0;
        frame_bit_count_cfg <= {INDEX_W{1'b0}};
        preamble_count_cfg <= {INDEX_W{1'b0}};
        start_offset_cfg <= {INDEX_W{1'b0}};
        start_pulse_sample <= 1'b0;
        tx_path_active_sample <= 1'b0;
        done_sticky_sample <= 1'b0;
        timeout_sticky_sample <= 1'b0;
        received_bits_sample <= {INDEX_W{1'b0}};
        total_errors_sample <= {INDEX_W{1'b0}};
        payload_errors_sample <= {INDEX_W{1'b0}};
        tx_valid_count_sample <= 32'd0;
        rx_valid_count_sample <= 32'd0;
        capture_valid_seen_any_sample <= 1'b0;
        capture_nonzero_seen_any_sample <= 1'b0;
        capture_valid_while_active_seen_any_sample <= 1'b0;
        capture_i_negative_seen_any_sample <= 1'b0;
        capture_q_negative_seen_any_sample <= 1'b0;
        capture_valid_count_lsb_sample <= 13'd0;
        capture_peak_abs_sample <= 14'd0;
        recovered_valid_seen_any_sample <= 1'b0;
        recovered_one_seen_any_sample <= 1'b0;
        decision_negative_seen_any_sample <= 1'b0;
        decision_nonzero_seen_any_sample <= 1'b0;
        recovered_valid_count_lsb_sample <= 9'd0;
        recovered_one_count_lsb_sample <= 9'd0;
        decision_negative_count_lsb_sample <= 10'd0;
    end else begin
        control_meta <= gp_ctrl;
        control_sync <= control_meta;
        control_sync_d <= control_sync;
        frame_meta <= gp_frame_bit_count;
        frame_sync <= frame_meta;
        preamble_meta <= gp_preamble_count;
        preamble_sync <= preamble_meta;
        offset_meta <= gp_start_offset;
        offset_sync <= offset_meta;
        start_pulse_sample <= 1'b0;

        if (start_edge) begin
            frame_bit_count_cfg <= frame_sync[INDEX_W-1:0];
            preamble_count_cfg <= preamble_sync[INDEX_W-1:0];
            start_offset_cfg <= offset_sync[INDEX_W-1:0];
            start_pulse_sample <= 1'b1;
            tx_path_active_sample <= 1'b1;
            done_sticky_sample <= 1'b0;
            timeout_sticky_sample <= 1'b0;
            received_bits_sample <= {INDEX_W{1'b0}};
            total_errors_sample <= {INDEX_W{1'b0}};
            payload_errors_sample <= {INDEX_W{1'b0}};
            tx_valid_count_sample <= 32'd0;
            rx_valid_count_sample <= 32'd0;
            capture_valid_seen_any_sample <= 1'b0;
            capture_nonzero_seen_any_sample <= 1'b0;
            capture_valid_while_active_seen_any_sample <= 1'b0;
            capture_i_negative_seen_any_sample <= 1'b0;
            capture_q_negative_seen_any_sample <= 1'b0;
            capture_valid_count_lsb_sample <= 13'd0;
            capture_peak_abs_sample <= 14'd0;
            recovered_valid_seen_any_sample <= 1'b0;
            recovered_one_seen_any_sample <= 1'b0;
            decision_negative_seen_any_sample <= 1'b0;
            decision_nonzero_seen_any_sample <= 1'b0;
            recovered_valid_count_lsb_sample <= 9'd0;
            recovered_one_count_lsb_sample <= 9'd0;
            decision_negative_count_lsb_sample <= 10'd0;
        end else if (clear_done_edge) begin
            done_sticky_sample <= 1'b0;
            timeout_sticky_sample <= 1'b0;
        end

        if (tx_path_active_sample && burst_out_valid) begin
            tx_valid_count_sample <= tx_valid_count_sample + 1'b1;
        end

        if (tx_path_active_sample && capture_in_valid) begin
            rx_valid_count_sample <= rx_valid_count_sample + 1'b1;
        end

        if (capture_in_valid) begin
            capture_valid_seen_any_sample <= 1'b1;
            if (capture_valid_count_lsb_sample != 13'h1FFF) begin
                capture_valid_count_lsb_sample <= capture_valid_count_lsb_sample + 1'b1;
            end
            if (capture_sample_nonzero) begin
                capture_nonzero_seen_any_sample <= 1'b1;
            end
            if (capture_in_i < 0) begin
                capture_i_negative_seen_any_sample <= 1'b1;
            end
            if (capture_in_q < 0) begin
                capture_q_negative_seen_any_sample <= 1'b1;
            end
            if (tx_path_active_sample) begin
                capture_valid_while_active_seen_any_sample <= 1'b1;
            end
            if (capture_peak_abs_sample < capture_peak_abs_saturated) begin
                capture_peak_abs_sample <= capture_peak_abs_saturated;
            end
        end

        if (recovered_valid_debug) begin
            recovered_valid_seen_any_sample <= 1'b1;
            if (recovered_valid_count_lsb_sample != 9'h1FF) begin
                recovered_valid_count_lsb_sample <= recovered_valid_count_lsb_sample + 1'b1;
            end
            if (recovered_bit_debug) begin
                recovered_one_seen_any_sample <= 1'b1;
                if (recovered_one_count_lsb_sample != 9'h1FF) begin
                    recovered_one_count_lsb_sample <= recovered_one_count_lsb_sample + 1'b1;
                end
            end
        end

        if (symbol_valid_debug) begin
            if (symbol_i_debug != {W{1'b0}}) begin
                decision_nonzero_seen_any_sample <= 1'b1;
            end
            if (symbol_i_debug < 0) begin
                decision_negative_seen_any_sample <= 1'b1;
                if (decision_negative_count_lsb_sample != 10'h3FF) begin
                    decision_negative_count_lsb_sample <= decision_negative_count_lsb_sample + 1'b1;
                end
            end
        end

        if (core_timed_out) begin
            tx_path_active_sample <= 1'b0;
            timeout_sticky_sample <= 1'b1;
        end

        if (core_done) begin
            tx_path_active_sample <= 1'b0;
            done_sticky_sample <= 1'b1;
            received_bits_sample <= received_bits;
            total_errors_sample <= total_errors;
            payload_errors_sample <= payload_errors;
        end
    end
end

always @(posedge ctrl_clk) begin
    if (!ctrl_resetn) begin
        status_meta_ctrl <= 32'd0;
        status_sync_ctrl <= 32'd0;
        received_meta_ctrl <= 32'd0;
        received_sync_ctrl <= 32'd0;
        error_counts_meta_ctrl <= 32'd0;
        error_counts_sync_ctrl <= 32'd0;
        tx_valid_meta_ctrl <= 32'd0;
        tx_valid_sync_ctrl <= 32'd0;
        rx_valid_meta_ctrl <= 32'd0;
        rx_valid_sync_ctrl <= 32'd0;
        adc_input_debug_meta_ctrl <= 15'd0;
        adc_input_debug_sync_ctrl <= 15'd0;
        adc_input_counter_meta_ctrl <= 16'd0;
        adc_input_counter_sync_ctrl <= 16'd0;
        adc_input_reset_meta_ctrl <= 1'b0;
        adc_input_reset_sync_ctrl <= 1'b0;
        capture_debug_meta_ctrl <= 32'd0;
        capture_debug_sync_ctrl <= 32'd0;
    end else begin
        status_meta_ctrl <= {16'd0, SPS[7:0], 3'd0, control_sync[4], timeout_sticky_sample, done_sticky_sample, core_busy, control_sync[0]};
        status_sync_ctrl <= status_meta_ctrl;
        received_meta_ctrl <= {{(32-INDEX_W){1'b0}}, received_bits_sample};
        received_sync_ctrl <= received_meta_ctrl;
        error_counts_meta_ctrl <= {
            {{(16-INDEX_W){1'b0}}, total_errors_sample},
            {{(16-INDEX_W){1'b0}}, payload_errors_sample}
        };
        error_counts_sync_ctrl <= error_counts_meta_ctrl;
        rx_valid_meta_ctrl <= rx_valid_count_sample;
        rx_valid_sync_ctrl <= rx_valid_meta_ctrl;
        adc_input_debug_meta_ctrl <= {
            adc_input_valid_seen_any_sample,
            adc_input_nonzero_seen_any_sample,
            adc_input_enable_seen_any_sample,
            adc_input_valid_count_lsb_sample[11:0]
        };
        adc_input_debug_sync_ctrl <= adc_input_debug_meta_ctrl;
        adc_input_counter_meta_ctrl <= adc_input_clk_counter_sample;
        adc_input_counter_sync_ctrl <= adc_input_counter_meta_ctrl;
        adc_input_reset_meta_ctrl <= adc_input_reset;
        adc_input_reset_sync_ctrl <= adc_input_reset_meta_ctrl;
        capture_debug_meta_ctrl <= {
            capture_valid_seen_any_sample,
            capture_nonzero_seen_any_sample,
            capture_valid_while_active_seen_any_sample,
            capture_i_negative_seen_any_sample,
            capture_q_negative_seen_any_sample,
            capture_valid_count_lsb_sample,
            capture_peak_abs_sample
        };
        capture_debug_sync_ctrl <= capture_debug_meta_ctrl;
        tx_valid_meta_ctrl <= {
            recovered_valid_seen_any_sample,
            recovered_one_seen_any_sample,
            decision_negative_seen_any_sample,
            decision_nonzero_seen_any_sample,
            recovered_valid_count_lsb_sample[7:0],
            recovered_one_count_lsb_sample[7:0],
            tx_valid_count_sample[11:0]
        };
        tx_valid_sync_ctrl <= tx_valid_meta_ctrl;
    end
end

assign gp_status = status_sync_ctrl;
assign gp_received_bits = received_sync_ctrl;
assign gp_total_errors = error_counts_sync_ctrl;
assign gp_signature = SIGNATURE;
assign gp_tx_valid_count = tx_valid_sync_ctrl;
assign gp_rx_valid_count = rx_valid_sync_ctrl;
assign gp_adc_input_debug = {
    adc_input_debug_sync_ctrl[14],
    adc_input_debug_sync_ctrl[13],
    adc_input_debug_sync_ctrl[12],
    adc_input_reset_sync_ctrl,
    adc_input_counter_sync_ctrl,
    adc_input_debug_sync_ctrl[11:0]
};
assign gp_capture_debug = capture_debug_sync_ctrl;
assign tx_path_active = tx_path_active_sample;

// DAC-facing TX stream: the selected modem drives the mux; BPSK mode is
// bit-identical to the original single-core bridge.
assign burst_out_valid = mod_qpsk ? qpsk_tx_valid : bpsk_tx_valid;
assign burst_out_i     = mod_qpsk ? qpsk_tx_i     : bpsk_tx_i;
assign burst_out_q     = mod_qpsk ? qpsk_tx_q     : bpsk_tx_q;

endmodule
