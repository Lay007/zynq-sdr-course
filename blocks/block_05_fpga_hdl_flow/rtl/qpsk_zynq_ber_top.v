// Lab 5.10b - Zynq-ready deterministic QPSK BER top-level
//
// QPSK counterpart of bpsk_zynq_ber_top: framed dibit source -> QPSK TX chain ->
// (external loopback tx->rx) -> QPSK RX dibit recovery -> QPSK BER counter. The
// SPS upsampler, RRC TX/RX FIRs and fixed-phase timing sampler are the shared
// complex-I/Q blocks; only the mapper / decision / BER stages are QPSK-specific.

`timescale 1ns/1ps

module qpsk_zynq_ber_top #(
    parameter integer W = 16,
    parameter integer SPS = 8,
    parameter integer INDEX_W = 16,
    parameter integer MAX_FRAME_BITS = 512,
    parameter integer PHASE_W = 3,
    parameter integer FLUSH_SYMBOLS = 16,
    parameter integer RX_IDLE_TIMEOUT_CYCLES = 4096,
    parameter integer LOCK_PREAMBLE_BITS = 8,   // frame-sync correlation window (24 for OTA)
    parameter integer LOCK_ERR_TOL = 0,         // 0 = exact lock; >0 = OTA-robust correlation lock
    parameter integer RX_SIG_THRESH = 1000,     // matched-filter/symbol |I|+|Q| signal gate
    parameter integer COSTAS_KP_LOG_ACQ = 8,
    parameter integer COSTAS_KP_LOG_TRACK = 6,
    parameter integer COSTAS_ACQ_SYMBOLS = 32,
    parameter integer COSTAS_KI_LOG = 1,
    parameter integer TIMING_RECOVERY_ENABLE = 0,
    // Extra symbols the RX sampler emits beyond the frame length. On a real OTA link
    // the frame arrives after the AD9361 TX+RX group delay (hundreds of samples), so
    // a sampler window == frame length misses the late frame. This margin lets the
    // frame-sync find the frame regardless of round-trip latency. 0 for the tight
    // fabric loop; ~256 for OTA. (The counter still uses the true symbol_count.)
    parameter integer RX_SAMPLE_MARGIN = 0,
    // 0 (default) compiles the coarse-CFO estimator out of the RX chain for the stock timing-clean
    // bitstream; set to 1 only for the two-board fabric-CFO build (see qpsk_rx_bit_recovery_chain).
    parameter integer COARSE_ENABLE = 0,
    // DC blocker across frames (issue #66). 1: its estimate is reset only by rst and is kept from
    // frame to frame (the receiver gets samples only during a burst, so between bursts it simply
    // holds), with a long time constant of 2^DC_BLOCK_K_MAX samples, so one preamble is a small
    // part of the average. 0: the estimate restarts at every frame, as before.
    parameter integer DC_PERSIST = 1,
    parameter integer DC_BLOCK_K_MAX = 13,
    parameter MEM_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem",
    parameter COEF_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_rrc_tx_fir_taps.mem"
) (
    input  wire                     clk,
    input  wire                     rst,
    input  wire                     start,
    input  wire [INDEX_W-1:0]       symbol_count,   // QPSK symbols (2 bits each)
    input  wire [INDEX_W-1:0]       preamble_count, // preamble length in BITS (frame-sync)
    input  wire [INDEX_W-1:0]       start_offset,
    input  wire                     dc_block_en,    // 1 = RX DC blocker on (OTA); 0 = passthrough
    input  wire                     costas_en,      // 1 = carrier recovery on (OTA); 0 = passthrough
    input  wire                     coarse_cfo_en,  // 1 = strip bulk inter-board CFO before Costas; 0 = passthrough
    input  wire                     phase_pick_en,  // 1 = feedforward burst timing phase selection
    input  wire                     timing_recovery_en, // 1 = continuous Gardner timing recovery
    // 1 = carry the acquired carrier phase from one burst into the next instead of
    // restarting the loop at zero. Sound when the RF path phase is quasi-static (a single
    // board talking to itself); harmless otherwise, the loop simply re-acquires.
    input  wire                     costas_hold_phase,
    // 1 = differential QPSK: the TX phase-accumulates and the RX phase-differences, so a whole-burst
    // rotation cancels and the frame-sync quadrant ambiguity disappears. 0 = ordinary absolute QPSK
    // (bit-identical, for the coherent loopback). See qpsk_diff_encoder/decoder, Lab 11.43.
    input  wire                     diff_en,
    // 1 = listen for a packet from another transmitter (issue #68). 0 = the receive window is the
    // frame plus RX_SAMPLE_MARGIN symbols after start, which fits self-OTA, where this core sends
    // the frame it waits for. 1 = the sampler runs for up to 2^INDEX_W - 1 symbols (136 ms at
    // 480 kSym/s), so a packet that arrives any time in that window is found; the idle watchdog then
    // watches the sampler instead of the decisions, which the signal gate holds back in silence.
    // The window does not cut a packet off (issue #70): the sampler runs without a limit, and the
    // attempt ends after 2^INDEX_W - 1 symbols only once no packet is being received, so a packet
    // that starts at the very end of the window is still received whole.
    input  wire                     listen_en,
    // Level, issue #71: while high, a listening attempt ends at once (as a timeout) unless a packet
    // is being received. The mailbox raises it on RX_STOP, so that TX_START need not wait for the
    // rest of the listening window. Tie to 0 when unused.
    input  wire                     abort_listen,
    // 1 at start = this burst carries a message (issue #55, Lab 11.49): the transmitter sends the
    // burst head of Lab 11.48 and the frame preamble followed by msg_bits (256 whitened packet bits
    // from the mailbox) instead of the ROM frame. The receiver is unchanged. 0 = the ROM frame.
    input  wire                     msg_mode,
    input  wire [255:0]             msg_bits,
    output wire                     busy,
    output reg                      done,
    output wire                     tx_valid,
    output wire signed [W-1:0]      tx_i,
    output wire signed [W-1:0]      tx_q,
    input  wire                     rx_valid,
    input  wire signed [W-1:0]      rx_i,
    input  wire signed [W-1:0]      rx_q,
    output reg                      timed_out,
    output wire [INDEX_W-1:0]       received_symbols,
    output wire [INDEX_W-1:0]       total_bit_errors,
    output wire [INDEX_W-1:0]       payload_bit_errors,
    output wire [1:0]               rotation_index,  // resolved constellation rotation, k*90 deg
    output wire [31:0]              payload_error_segments,
    output wire [INDEX_W-1:0]       first_payload_error_index,
    output wire [INDEX_W-1:0]       last_payload_error_index,
    output wire                     debug_symbol_valid,
    output wire signed [W-1:0]      debug_symbol_i,
    output wire signed [W-1:0]      debug_symbol_q,
    // Decoded dibits, exactly as fed to the BER counter. Without these the QPSK path
    // has NO decoded-bit visibility (the bridge hard-wires its recovered-bit debug to
    // zero in QPSK mode), so a reported payload error index cannot be checked against
    // the bits the receiver actually produced.
    output wire                     debug_recovered_valid,
    output wire [1:0]               debug_recovered_dibit,
    output wire [15:0]              timing_mu,
    output wire signed [16:0]       timing_omega,
    output wire signed [2:0]        timing_error
);

localparam integer RX_IDLE_TIMEOUT_W = (RX_IDLE_TIMEOUT_CYCLES <= 1) ? 1 : $clog2(RX_IDLE_TIMEOUT_CYCLES);

wire frame_start = start && !busy;
wire src_valid;
wire [1:0] src_dibit;
wire src_last;
wire src_ready;
wire src_busy;
wire rom_valid, rom_last, rom_busy, msg_valid, msg_last, msg_busy;
wire [1:0] rom_dibit, msg_dibit;
reg msg_active = 1'b0;   // latched at frame_start
wire tx_busy;
// Differential encoder output (absolute symbol dibit) into the TX chain.
wire enc_valid;
wire [1:0] enc_dibit;
wire enc_last;
wire tx_src_ready;      // qpsk_framed_tx_chain.s_ready, fed back to the encoder's m_ready
// Raw absolute dibit out of the RX chain, before differential decoding.
wire rx_raw_valid;
wire [1:0] rx_raw_dibit;
wire recovered_valid;
wire [1:0] recovered_dibit;
// Differential decoder output, before the listen-mode gate.
wire dd_valid;
wire [1:0] dd_dibit;
wire packet_present;

assign debug_recovered_valid = recovered_valid;
assign debug_recovered_dibit = recovered_dibit;
wire ber_busy;
wire ber_done;
reg ber_abort = 1'b0;
reg [RX_IDLE_TIMEOUT_W-1:0] rx_idle_counter = {RX_IDLE_TIMEOUT_W{1'b0}};
// Listen mode: symbols sampled in this attempt, saturating (issue #70).
reg [INDEX_W-1:0] listen_window = {INDEX_W{1'b0}};

assign busy = src_busy || tx_busy || ber_busy;

qpsk_frame_dibit_source #(
    .INDEX_W(INDEX_W),
    .MAX_FRAME_BITS(MAX_FRAME_BITS),
    .MEM_FILE(MEM_FILE)
) source_i (
    .clk(clk),
    .rst(rst),
    .start(frame_start && !msg_mode),
    .symbol_count(symbol_count),
    .out_ready(src_ready && !msg_active),
    .out_valid(rom_valid),
    .out_dibit(rom_dibit),
    .out_last(rom_last),
    .busy(rom_busy),
    .done()
);

qpsk_message_dibit_source #(
    .MAX_FRAME_BITS(MAX_FRAME_BITS),
    .MEM_FILE(MEM_FILE)
) message_source_i (
    .clk(clk),
    .rst(rst),
    .start(frame_start && msg_mode),
    .msg_bits(msg_bits),
    .out_ready(src_ready && msg_active),
    .out_valid(msg_valid),
    .out_dibit(msg_dibit),
    .out_last(msg_last),
    .busy(msg_busy),
    .done()
);

always @(posedge clk) begin
    if (rst)
        msg_active <= 1'b0;
    else if (frame_start)
        msg_active <= msg_mode;
end

assign src_valid = msg_active ? msg_valid : rom_valid;
assign src_dibit = msg_active ? msg_dibit : rom_dibit;
assign src_last  = msg_active ? msg_last  : rom_last;
assign src_busy  = rom_busy || msg_busy;

// Differential encoder: phase-accumulates the info dibits into absolute symbols. Combinational and
// handshake-transparent, so it drops into the backpressured source->TX path with no added latency.
qpsk_diff_encoder diff_encoder_i (
    .clk(clk),
    .rst(rst || frame_start),
    .enable(diff_en),
    .s_valid(src_valid),
    .s_dibit(src_dibit),
    .s_last(src_last),
    .s_ready(src_ready),
    .m_valid(enc_valid),
    .m_dibit(enc_dibit),
    .m_last(enc_last),
    .m_ready(tx_src_ready)
);

qpsk_framed_tx_chain #(
    .W(W),
    .SPS(SPS),
    .PHASE_W(PHASE_W),
    .FLUSH_SYMBOLS(FLUSH_SYMBOLS),
    .COUNT_W(INDEX_W),
    .COEF_FILE(COEF_FILE)
) tx_chain_i (
    .clk(clk),
    .rst(rst),
    .s_valid(enc_valid),
    .s_dibit(enc_dibit),
    .s_last(enc_last),
    .s_ready(tx_src_ready),
    .m_valid(tx_valid),
    .m_i(tx_i),
    .m_q(tx_q),
    .busy(tx_busy)
);

qpsk_rx_bit_recovery_chain #(
    .W(W),
    .SPS(SPS),
    .INDEX_W(INDEX_W),
    .COSTAS_KP_LOG_ACQ(COSTAS_KP_LOG_ACQ),
    .COSTAS_KP_LOG_TRACK(COSTAS_KP_LOG_TRACK),
    .COSTAS_ACQ_SYMBOLS(COSTAS_ACQ_SYMBOLS),
    .COSTAS_KI_LOG(COSTAS_KI_LOG),
    .COSTAS_SIG_THRESH(RX_SIG_THRESH),
    .TIMING_RECOVERY_ENABLE(TIMING_RECOVERY_ENABLE),
    .COARSE_ENABLE(COARSE_ENABLE),
    .DC_BLOCK_K_MAX(DC_PERSIST ? DC_BLOCK_K_MAX : 10),
    .COEF_FILE(COEF_FILE)
) rx_chain_i (
    .clk(clk),
    // restart the matched filter + sampler each frame so back-to-back bursts realign
    .rst(rst || frame_start),
    // ... but optionally let the carrier loop keep the phase it already found
    .rst_carrier(rst || (frame_start && !costas_hold_phase)),
    // ... and keep the DC estimate across frames unless DC_PERSIST = 0
    .rst_dc(DC_PERSIST ? rst : (rst || frame_start)),
    // ... and in listen mode hold the timing loop through the silence before the packet
    .listen_en(listen_en),
    .dc_block_en(dc_block_en),
    .costas_en(costas_en),
    // Runtime coarse-CFO enable. The bridge drives this from a gp_ctrl bit so the fabric receiver
    // can strip a real inter-board CFO (validated standalone in Lab 11.30/11.31); benches tie it to
    // 0 (passthrough). The estimator's output is registered either way, so the coherent loopback
    // still decodes at BER 0 (one added clock, below the sampler phase choice).
    .coarse_cfo_en(coarse_cfo_en),
    .phase_pick_en(phase_pick_en),
    .timing_recovery_en(timing_recovery_en),
    .diff_en(diff_en),
    .in_valid(rx_valid),
    .in_i(rx_i),
    .in_q(rx_q),
    .start_offset(start_offset),
    // sampler emits margin extra symbols so a latency-delayed OTA frame still fits;
    // in listen mode it runs for the whole counter range
    .symbol_count(listen_en ? {INDEX_W{1'b1}} : symbol_count + RX_SAMPLE_MARGIN[INDEX_W-1:0]),
    .out_valid(rx_raw_valid),
    .out_dibit(rx_raw_dibit),
    .debug_symbol_valid(debug_symbol_valid),
    .debug_symbol_i(debug_symbol_i),
    .debug_symbol_q(debug_symbol_q),
    .timing_mu(timing_mu),
    .timing_omega(timing_omega),
    .timing_error(timing_error),
    .packet_present(packet_present)
);

// Differential decoder: recovers info from consecutive-symbol phase differences, so a whole-burst
// rotation cancels before the frame sync ever sees it. Runs continuously through the burst (reset
// once at frame_start, so the first symbol -- pre-frame noise -- is the only one without a
// reference). enable=0 passes the absolute dibit through unchanged.
qpsk_diff_decoder diff_decoder_i (
    .clk(clk),
    .rst(rst || frame_start),
    .enable(diff_en),
    .in_valid(rx_raw_valid),
    .in_dibit(rx_raw_dibit),
    .out_valid(dd_valid),
    .out_dibit(dd_dibit)
);

// Listen mode: keep the frame sync off the noise between packets. Over a long wait the
// correlator would otherwise test tens of thousands of noise positions, and with LOCK_ERR_TOL = 1
// and four rotation hypotheses a false lock (a "frame" with about half its bits wrong) becomes
// likely (about 1 in 5 over 30 ms in simulation). The decisions are delayed by LISTEN_DELAY
// symbols and passed only while the packet detector sees a packet, plus LISTEN_HANG symbols
// after it stops; the delay lets the first symbols of the packet, which arrive before the
// detector has decided, through as well. Outside listen mode the decisions pass unchanged.
localparam integer LISTEN_DELAY = 16;
localparam integer LISTEN_HANG = 64;
reg [2*LISTEN_DELAY-1:0] listen_sr = {(2*LISTEN_DELAY){1'b0}};
reg [4:0] listen_fill = 5'd0;
reg [6:0] listen_hang = 7'd0;
wire listen_open = packet_present || (listen_hang != 7'd0);

always @(posedge clk) begin
    if (rst || frame_start) begin
        listen_sr   <= {(2*LISTEN_DELAY){1'b0}};
        listen_fill <= 5'd0;
        listen_hang <= 7'd0;
    end else if (dd_valid) begin
        listen_sr <= {listen_sr[2*LISTEN_DELAY-3:0], dd_dibit};
        if (listen_fill != LISTEN_DELAY[4:0]) listen_fill <= listen_fill + 1'b1;
        if (packet_present) listen_hang <= LISTEN_HANG[6:0];
        else if (listen_hang != 7'd0) listen_hang <= listen_hang - 1'b1;
    end
end

assign recovered_valid = listen_en ? (dd_valid && (listen_fill == LISTEN_DELAY[4:0]) && listen_open)
                                   : dd_valid;
assign recovered_dibit = listen_en ? listen_sr[2*LISTEN_DELAY-1 -: 2] : dd_dibit;

qpsk_ber_counter #(
    .INDEX_W(INDEX_W),
    .MAX_FRAME_BITS(MAX_FRAME_BITS),
    .LOCK_PREAMBLE_BITS(LOCK_PREAMBLE_BITS),
    .LOCK_ERR_TOL(LOCK_ERR_TOL),
    .MEM_FILE(MEM_FILE)
) ber_counter_i (
    .clk(clk),
    .rst(rst),
    .start(frame_start),
    .abort(ber_abort),
    .symbol_count(symbol_count),
    .preamble_count(preamble_count),
    .in_valid(recovered_valid),
    .in_dibit(recovered_dibit),
    .busy(ber_busy),
    .done(ber_done),
    .rotation_index(rotation_index),
    .received_symbols(received_symbols),
    .total_bit_errors(total_bit_errors),
    .payload_bit_errors(payload_bit_errors),
    .payload_error_segments(payload_error_segments),
    .first_payload_error_index(first_payload_error_index),
    .last_payload_error_index(last_payload_error_index)
);

always @(posedge clk) begin
    if (rst) begin
        done <= 1'b0;
        timed_out <= 1'b0;
        ber_abort <= 1'b0;
        rx_idle_counter <= {RX_IDLE_TIMEOUT_W{1'b0}};
        listen_window <= {INDEX_W{1'b0}};
    end else begin
        done <= 1'b0;
        timed_out <= 1'b0;
        ber_abort <= 1'b0;

        if (frame_start) begin
            rx_idle_counter <= {RX_IDLE_TIMEOUT_W{1'b0}};
            listen_window <= {INDEX_W{1'b0}};
        end else if (ber_busy && listen_en && listen_window == {INDEX_W{1'b1}}
                     && !listen_open && received_symbols == {INDEX_W{1'b0}}) begin
            // Listen window used up and no packet in progress: end the attempt as a timeout.
            ber_abort <= 1'b1;
            timed_out <= 1'b1;
        end else if (ber_busy && listen_en && abort_listen
                     && !listen_open && received_symbols == {INDEX_W{1'b0}}) begin
            // Listening stopped (#71): end the attempt now, unless a packet is coming in (#70).
            ber_abort <= 1'b1;
            timed_out <= 1'b1;
        end else if (ber_busy) begin
            if (listen_en && debug_symbol_valid && listen_window != {INDEX_W{1'b1}})
                listen_window <= listen_window + 1'b1;
            // Listen mode: silence before the packet is expected, so the watchdog watches the sampler,
            // which runs without a limit there; it only fires if the input samples stop.
            if (listen_en ? debug_symbol_valid : recovered_valid) begin
                rx_idle_counter <= {RX_IDLE_TIMEOUT_W{1'b0}};
            end else if (rx_idle_counter == RX_IDLE_TIMEOUT_CYCLES - 1) begin
                ber_abort <= 1'b1;
                timed_out <= 1'b1;
            end else begin
                rx_idle_counter <= rx_idle_counter + 1'b1;
            end
        end

        if (ber_done) begin
            done <= 1'b1;
        end
    end
end

endmodule
