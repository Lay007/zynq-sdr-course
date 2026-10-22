`timescale 1ns/1ps

// Issue #48, stage 4b: the OFDM modem on the radio. One frame out of the DAC, one frame found in the
// ADC stream, with the PS writing and reading bits through AXI4-Lite.
//
//   TX: TX_START -> preamble (ofdm_sync_preamble_rom) + the modem's training symbol + DATA_SYMBOLS
//       data symbols (bits from the TX buffer) -> gain (Q4.12) -> dual-clock FIFO -> one sample per
//       DAC FIFO request (fifo_rd_req) in the sample domain, with tx_select high for the burst.
//   RX: ADC samples (rx_sample_bus, sample domain) -> dual-clock FIFO -> at most one sample every
//       RX_SPACING clocks -> <<< RX_SHIFT (the AD9361's 12 bits to Q1.15 at 4) -> ofdm_frame_sync ->
//       ofdm_frame_conditioner (coarse CFO and level from the preamble) -> the modem's receiver, for
//       the first frame after RX_ARM -> RX buffer.
//
// Everything but the sample-domain ends runs on s_axi_aclk (100 MHz on the board): the modem needs
// 9-12 clocks per sample on average and ofdm_frame_sync 11 between samples to match its model
// (reports/fpga/ofdm-frame-sync-rtl-sim-20261019.md), while the sample domain runs at the converter
// rate. The frame on the air is the frame of stage 4a (tools/ofdm_rf_link.py) without the silence.
//
// Bits: 48 QPSK groups per OFDM symbol, 16 groups per 32-bit word, group k of a word in bits
// [2k+1:2k] as {I bit, Q bit}, 3 words per symbol; data symbol s starts at word 3s, in both buffers.
//
// AXI4-Lite (byte addresses, 32-bit):
//   0x000 ID            "OFDR" (0x4F464452)
//   0x004 VERSION       0x00020000 (1.0 had no conditioner)
//   0x008 CONTROL (W)   [0] RX_ARM: reset the modem, the frame search and the RX buffer state, then
//                           take the first frame found; [1] TX_START (ignored while TX is busy);
//                       [2] RX_STOP; [8] clear the sticky flags
//   0x00C STATUS        [0] TX busy  [1] TX done (since TX_START)  [2] RX armed  [3] RX frame found
//                       [4] RX done (DATA_SYMBOLS decided)  [5] TX underflow (sticky)
//                       [6] RX FIFO overflow (sticky); the modem's own flags are at 0x10C
//   0x010 DATA_SYMBOLS  data symbols per frame, 1..MAX_SYMBOLS (default 4)
//   0x014 TX_GAIN       Q4.12 (default 9170 = +7 dB: -12 dBFS RMS, the level stage 4a found best)
//   0x018 RX_SHIFT      0..8 (default 4)
//   0x01C MAX_SYMBOLS   (read only)
//   0x020 FRAMES_FOUND  0x024 FRAMES_MISSED  0x028 SYNC_OVERFLOWS (ofdm_frame_sync, since RX_ARM)
//   0x02C RX_SYMBOLS    data symbols decided since RX_ARM
//   0x030 TX_SAMPLES    samples queued by the last TX_START
//   0x034 TX_UNDERFLOWS DAC requests during a burst that found the FIFO empty
//   0x038 RX_OVERFLOWS  ADC samples lost at the RX FIFO
//   0x03C RX_SAMPLES    samples handed to the frame search since RX_ARM
//   0x040 CONFIG        [0] coarse CFO from the preamble, [1] level normalization (both default 1;
//                       ofdm_frame_conditioner)
//   0x044 THETA         preamble angle of the last frame, 2^16 = one turn: CFO = THETA / 2^21 * fs
//   0x048 GAIN_K        level gain of the last frame, 2^(GAIN_K / 2)
//   0x100-0x13F         the modem's own registers (ofdm_axi_modem: CFO_THETA, CE_TRAINED, ...)
//   0x400-0x7FF         TX buffer (write only)
//   0x800-0xBFF         RX buffer (read only)
module ofdm_radio_core #(
    parameter integer DATA_WORDS = 256,     // per buffer; MAX_SYMBOLS = DATA_WORDS / 3
    parameter integer TX_FIFO_AW = 8,
    parameter integer RX_FIFO_AW = 5,
    parameter integer PRIME = 160,          // samples queued before the burst starts
    parameter integer RX_SPACING = 16       // clocks at least between two samples into the search
) (
    input  wire         s_axi_aclk,
    input  wire         s_axi_aresetn,
    input  wire [11:0]  s_axi_awaddr,
    input  wire         s_axi_awvalid,
    output reg          s_axi_awready,
    input  wire [31:0]  s_axi_wdata,
    input  wire [3:0]   s_axi_wstrb,
    input  wire         s_axi_wvalid,
    output reg          s_axi_wready,
    output reg  [1:0]   s_axi_bresp,
    output reg          s_axi_bvalid,
    input  wire         s_axi_bready,
    input  wire [11:0]  s_axi_araddr,
    input  wire         s_axi_arvalid,
    output reg          s_axi_arready,
    output reg  [31:0]  s_axi_rdata,
    output reg  [1:0]   s_axi_rresp,
    output reg          s_axi_rvalid,
    input  wire         s_axi_rready,

    input  wire         sample_clk,
    input  wire         sample_resetn,
    input  wire         fifo_rd_req,          // the DAC FIFO's request (course_dac_fifo_source_mux)
    output reg          tx_select,            // valid with tx_sample_bus, one clock after the request
    output wire [32:0]  tx_sample_bus,        // {valid, I[15:0], Q[15:0]}
    input  wire [32:0]  rx_sample_bus         // {valid, I[15:0], Q[15:0]}
);

localparam integer MAX_SYMBOLS = DATA_WORDS / 3;
localparam integer BA = $clog2(DATA_WORDS);
localparam [31:0] CORE_ID = 32'h4F464452;
localparam [31:0] CORE_VERSION = 32'h00020000;

wire clk = s_axi_aclk;
wire rst = !s_axi_aresetn;

// =============================================================================================
// Registers
// =============================================================================================
reg [7:0]  data_symbols = 8'd4;
reg [15:0] tx_gain = 16'd9170;
reg [3:0]  rx_shift = 4'd4;
reg        cfg_cfo = 1'b1, cfg_agc = 1'b1;
reg        tx_start_pulse = 1'b0, rx_arm_pulse = 1'b0, rx_stop_pulse = 1'b0, clear_pulse = 1'b0;
reg [3:0]  modem_rst_count = 4'd0;
wire       modem_resetn = s_axi_aresetn && (modem_rst_count == 0);

// TX buffer: AXI writes, the bit feeder reads (one block RAM)
reg [31:0] txbuf [0:DATA_WORDS-1];
reg [BA-1:0] txbuf_ra = 0;
reg [31:0] txbuf_q = 0;
// RX buffer: the RX writer writes, AXI reads
reg [31:0] rxbuf [0:DATA_WORDS-1];
reg        rxbuf_we = 1'b0;
reg [BA-1:0] rxbuf_wa = 0;
reg [31:0] rxbuf_wd = 0;
reg [31:0] rxbuf_q = 0;

// =============================================================================================
// The modem
// =============================================================================================
wire       mt_valid, mt_ready, mo_valid, mo_last, mr_valid, mr_ready, mr_last, md_valid, md_last;
wire [7:0] mt_data;
wire [31:0] mo_data, mr_data;
wire [7:0] md_data;
reg        md_ready = 1'b1;
reg  [5:0] m_awaddr = 0, m_araddr = 0;
reg        m_awvalid = 1'b0, m_wvalid = 1'b0, m_arvalid = 1'b0;
reg [31:0] m_wdata = 0;
wire       m_awready, m_wready, m_bvalid, m_arready, m_rvalid;
wire [1:0] m_bresp, m_rresp;
wire [31:0] m_rdata;
reg        mo_ready = 1'b0;

ofdm_axi_modem modem (
    .aclk(clk), .aresetn(modem_resetn),
    .s_axis_tx_tvalid(mt_valid), .s_axis_tx_tready(mt_ready), .s_axis_tx_tdata(mt_data), .s_axis_tx_tlast(1'b0),
    .m_axis_tx_tvalid(mo_valid), .m_axis_tx_tready(mo_ready), .m_axis_tx_tdata(mo_data), .m_axis_tx_tlast(mo_last),
    .s_axis_rx_tvalid(mr_valid), .s_axis_rx_tready(mr_ready), .s_axis_rx_tdata(mr_data), .s_axis_rx_tlast(mr_last),
    .m_axis_rx_tvalid(md_valid), .m_axis_rx_tready(md_ready), .m_axis_rx_tdata(md_data), .m_axis_rx_tlast(md_last),
    .s_axi_awaddr(m_awaddr), .s_axi_awvalid(m_awvalid), .s_axi_awready(m_awready),
    .s_axi_wdata(m_wdata), .s_axi_wstrb(4'hF), .s_axi_wvalid(m_wvalid), .s_axi_wready(m_wready),
    .s_axi_bresp(m_bresp), .s_axi_bvalid(m_bvalid), .s_axi_bready(1'b1),
    .s_axi_araddr(m_araddr), .s_axi_arvalid(m_arvalid), .s_axi_arready(m_arready),
    .s_axi_rdata(m_rdata), .s_axi_rresp(m_rresp), .s_axi_rvalid(m_rvalid), .s_axi_rready(1'b1)
);

// =============================================================================================
// TX, control domain: bit feeder
// =============================================================================================
localparam [2:0] F_IDLE = 3'd0, F_TRAIN = 3'd1, F_FETCH = 3'd2, F_WAIT = 3'd3, F_LOAD = 3'd4, F_SEND = 3'd5;
reg [2:0]  f_state = F_IDLE;
reg [5:0]  f_k = 0;                 // group within the training symbol
reg [3:0]  f_pair = 0;              // group within the word
reg [BA-1:0] f_word = 0;
reg [BA-1:0] f_words = 0;           // words to send
reg [31:0] f_bits = 0;
wire [5:0] f_d = f_k;
assign mt_valid = (f_state == F_TRAIN) || (f_state == F_SEND);
assign mt_data  = (f_state == F_TRAIN) ? {6'd0, f_d[0] ^ f_d[3], f_d[1] ^ f_d[2] ^ f_d[4]}
                                       : {6'd0, f_bits[2 * f_pair +: 2]};

always @(posedge clk) txbuf_q <= txbuf[txbuf_ra];

always @(posedge clk) begin
    if (rst || rx_arm_pulse) begin
        f_state <= F_IDLE;
    end else begin
        case (f_state)
        F_IDLE: if (tx_start_pulse) begin
            f_state <= F_TRAIN;
            f_k <= 0;
            f_word <= 0;
            f_words <= data_symbols * 3;
        end
        F_TRAIN: if (mt_ready) begin
            f_k <= f_k + 1'b1;
            if (f_k == 6'd47) f_state <= F_FETCH;
        end
        F_FETCH: begin txbuf_ra <= f_word; f_state <= F_WAIT; end
        F_WAIT:  f_state <= F_LOAD;
        F_LOAD:  begin f_bits <= txbuf_q; f_pair <= 0; f_state <= F_SEND; end
        F_SEND: if (mt_ready) begin
            f_pair <= f_pair + 1'b1;
            if (f_pair == 4'd15) begin
                f_word <= f_word + 1'b1;
                f_state <= (f_word + 1'b1 == f_words) ? F_IDLE : F_FETCH;
            end
        end
        default: f_state <= F_IDLE;
        endcase
    end
end

// =============================================================================================
// TX, control domain: preamble, then the modem's samples, gain, into the FIFO
// =============================================================================================
localparam [1:0] T_IDLE = 2'd0, T_PRE = 2'd1, T_MOD = 2'd2, T_DRAIN = 2'd3;
reg [1:0]  t_state = T_IDLE;
reg [6:0]  pre_idx = 0;
reg [7:0]  t_sym = 0;               // modem symbols taken
reg [7:0]  t_syms = 0;              // training + data symbols in this frame
reg [31:0] tx_samples = 0;
reg        tx_busy = 1'b0, tx_done = 1'b0, primed = 1'b0;
reg        go_toggle = 1'b0;
wire signed [15:0] pre_re, pre_im;
ofdm_sync_preamble_rom rom (.index(pre_idx), .re(pre_re), .im(pre_im));

wire        txf_full;
reg         s1_valid = 1'b0, s1_last = 1'b0, s2_valid = 1'b0;
reg signed [32:0] s1_re = 0, s1_im = 0;
reg  [32:0] s2_word = 0;                                   // {last, Q, I}
wire        adv = !s2_valid || !txf_full;
wire        src_pre = (t_state == T_PRE);
wire        src_mod = (t_state == T_MOD) && mo_valid;
wire        src_valid = src_pre || src_mod;
wire signed [15:0] src_re = src_pre ? pre_re : mo_data[15:0];
wire signed [15:0] src_im = src_pre ? pre_im : mo_data[31:16];
wire        src_last = src_mod && mo_last && (t_sym + 1'b1 == t_syms);
always @(*) mo_ready = (t_state == T_MOD) && adv;

function [15:0] sat16(input signed [32:0] v);
    begin
        if (v > 33'sd32767) sat16 = 16'h7FFF;
        else if (v < -33'sd32768) sat16 = 16'h8000;
        else sat16 = v[15:0];
    end
endfunction

always @(posedge clk) begin
    if (rst) begin
        s1_valid <= 1'b0;
        s2_valid <= 1'b0;
    end else if (adv) begin
        s1_valid <= src_valid;
        s1_last <= src_last;
        s1_re <= src_re * $signed({1'b0, tx_gain});
        s1_im <= src_im * $signed({1'b0, tx_gain});
        s2_valid <= s1_valid;
        s2_word <= {s1_last, sat16(s1_im >>> 12), sat16(s1_re >>> 12)};
    end
end

wire txf_wr = s2_valid && !txf_full;
reg  done_sync1 = 1'b0, done_sync2 = 1'b0, done_sync3 = 1'b0;
wire done_toggle_s;
always @(posedge clk) {done_sync3, done_sync2, done_sync1} <= {done_sync2, done_sync1, done_toggle_s};

always @(posedge clk) begin
    if (rst) begin
        t_state <= T_IDLE;
        tx_busy <= 1'b0;
        tx_done <= 1'b0;
        primed <= 1'b0;
    end else begin
        if (txf_wr) tx_samples <= tx_samples + 1'b1;
        if (txf_wr && !primed && (tx_samples + 1 >= PRIME || s2_word[32])) begin
            primed <= 1'b1;
            go_toggle <= ~go_toggle;
        end
        case (t_state)
        T_IDLE: if (tx_start_pulse && !tx_busy) begin
            t_state <= T_PRE;
            pre_idx <= 0;
            t_sym <= 0;
            t_syms <= data_symbols + 1'b1;
            tx_samples <= 0;
            tx_busy <= 1'b1;
            tx_done <= 1'b0;
            primed <= 1'b0;
        end
        T_PRE: if (adv) begin
            pre_idx <= pre_idx + 1'b1;
            if (pre_idx == 7'd79) t_state <= T_MOD;
        end
        T_MOD: if (adv && mo_valid && mo_last) begin
            t_sym <= t_sym + 1'b1;
            if (t_sym + 1'b1 == t_syms) t_state <= T_DRAIN;
        end
        T_DRAIN: if (done_sync3 != done_sync2) begin     // the sample domain played the last sample
            t_state <= T_IDLE;
            tx_busy <= 1'b0;
            tx_done <= 1'b1;
        end
        endcase
    end
end

// =============================================================================================
// TX, sample domain
// =============================================================================================
wire [32:0] txf_rd_data;
wire        txf_empty;
reg         s_active = 1'b0;
reg         go_s1 = 1'b0, go_s2 = 1'b0, go_s3 = 1'b0;
reg         done_toggle = 1'b0, unf_toggle = 1'b0;
reg  [32:0] tx_out = 0;
wire        txf_rd = fifo_rd_req && s_active && !txf_empty;
assign done_toggle_s = done_toggle;
assign tx_sample_bus = tx_out;

ofdm_async_fifo #(.W(33), .AW(TX_FIFO_AW)) tx_fifo (
    .wr_clk(clk), .wr_rst(rst), .wr_en(txf_wr), .wr_data(s2_word), .wr_full(txf_full),
    .rd_clk(sample_clk), .rd_rst(!sample_resetn), .rd_en(txf_rd), .rd_data(txf_rd_data), .rd_empty(txf_empty)
);

always @(posedge sample_clk) begin
    {go_s3, go_s2, go_s1} <= {go_s2, go_s1, go_toggle};
    if (!sample_resetn) begin
        s_active <= 1'b0;
        tx_select <= 1'b0;
        tx_out <= 0;
    end else begin
        if (go_s3 != go_s2) s_active <= 1'b1;
        if (fifo_rd_req) begin
            tx_select <= s_active;
            if (s_active && !txf_empty) begin
                tx_out <= {1'b1, txf_rd_data[15:0], txf_rd_data[31:16]};      // {valid, I, Q}
                if (txf_rd_data[32]) begin
                    s_active <= 1'b0;
                    done_toggle <= ~done_toggle;
                end
            end else begin
                tx_out <= 0;
                if (s_active) unf_toggle <= ~unf_toggle;
            end
        end
    end
end

// =============================================================================================
// RX, sample domain -> control domain
// =============================================================================================
wire        rxf_full, rxf_empty;
wire [31:0] rxf_rd_data;
reg         ovf_toggle = 1'b0;
always @(posedge sample_clk)
    if (rx_sample_bus[32] && rxf_full) ovf_toggle <= ~ovf_toggle;

reg  [4:0]  spacing = 0;
wire        rxf_rd = !rxf_empty && (spacing == 0);
ofdm_async_fifo #(.W(32), .AW(RX_FIFO_AW)) rx_fifo (
    .wr_clk(sample_clk), .wr_rst(!sample_resetn), .wr_en(rx_sample_bus[32]), .wr_data(rx_sample_bus[31:0]),
    .wr_full(rxf_full),
    .rd_clk(clk), .rd_rst(rst), .rd_en(rxf_rd), .rd_data(rxf_rd_data), .rd_empty(rxf_empty)
);

// level: << rx_shift with saturation (bus: I in [31:16], Q in [15:0])
reg        sx_valid = 1'b0;
reg signed [15:0] sx_re = 0, sx_im = 0;
wire signed [23:0] sh_re = $signed(rxf_rd_data[31:16]) <<< rx_shift;
wire signed [23:0] sh_im = $signed(rxf_rd_data[15:0]) <<< rx_shift;
function [15:0] sat24(input signed [23:0] v);
    begin
        if (v > 24'sd32767) sat24 = 16'h7FFF;
        else if (v < -24'sd32768) sat24 = 16'h8000;
        else sat24 = v[15:0];
    end
endfunction

reg         rx_armed = 1'b0, rx_fed = 1'b0;
reg  [31:0] rx_samples = 0;
always @(posedge clk) begin
    sx_valid <= 1'b0;
    if (rst) begin
        spacing <= 0;
    end else begin
        if (spacing != 0) spacing <= spacing - 1'b1;
        if (rxf_rd) begin
            spacing <= RX_SPACING - 1;
            sx_re <= sat24(sh_re);
            sx_im <= sat24(sh_im);
            sx_valid <= 1'b1;              // always: the DC tracker of the search keeps learning between frames
        end
    end
end

// frame search and the modem's receiver
wire        fs_valid, fs_last, fs_start;
wire signed [15:0] fs_re, fs_im;
wire [15:0] fs_found, fs_missed, fs_ovf;
wire        est_valid;
wire signed [35:0] est_re, est_im;
wire [31:0] est_r;
wire signed [15:0] est_dc_re, est_dc_im;
reg  [7:0]  fed_syms = 0;
wire        forward = rx_armed && !rx_fed;
wire        cond_ready;
ofdm_frame_sync frame_sync (
    .clk(clk), .rst(rst || rx_arm_pulse), .dc_rst(rst), .frame_symbols(data_symbols + 1'b1),
    .in_valid(sx_valid), .in_re(sx_re), .in_im(sx_im),
    .out_valid(fs_valid), .out_ready(forward ? cond_ready : 1'b1),
    .out_re(fs_re), .out_im(fs_im), .out_last(fs_last), .frame_start(fs_start),
    .frames_found(fs_found), .frames_missed(fs_missed), .overflows(fs_ovf),
    .est_valid(est_valid), .est_re(est_re), .est_im(est_im), .est_r(est_r),
    .est_dc_re(est_dc_re), .est_dc_im(est_dc_im)
);

// coarse CFO and level from the preamble (CONFIG[0], CONFIG[1])
wire signed [15:0] cond_re, cond_im, pre_theta;
wire signed [5:0]  gain_k;
wire        cond_busy;
ofdm_frame_conditioner conditioner (
    .clk(clk), .rst(rst || rx_arm_pulse), .cfo_en(cfg_cfo), .agc_en(cfg_agc),
    .est_valid(est_valid), .est_re(est_re), .est_im(est_im), .est_r(est_r),
    .est_dc_re(est_dc_re), .est_dc_im(est_dc_im),
    .in_valid(fs_valid && forward), .in_ready(cond_ready), .in_re(fs_re), .in_im(fs_im),
    .in_last(fs_last), .in_start(fs_start),
    .out_valid(mr_valid), .out_ready(mr_ready), .out_re(cond_re), .out_im(cond_im), .out_last(mr_last),
    .theta(pre_theta), .gain_k(gain_k), .busy(cond_busy)
);
assign mr_data = {cond_im, cond_re};

// RX writer: a symbol's 48 groups (order 24..47, 0..23) into 96 bits, then 3 words
reg [95:0] sym_bits = 0;
reg [1:0]  w_k = 0;
reg        w_busy = 1'b0;
reg [7:0]  rx_syms = 0;
reg [BA-1:0] w_base = 0;
always @(*) md_ready = !w_busy;

always @(posedge clk) begin
    rxbuf_we <= 1'b0;
    if (rst || rx_arm_pulse) begin
        w_busy <= 1'b0;
        rx_syms <= 0;
        w_base <= 0;
        fed_syms <= 0;
        rx_fed <= 1'b0;
        rx_samples <= 0;
    end else begin
        if (sx_valid && rx_armed) rx_samples <= rx_samples + 1'b1;
        if (mr_valid && mr_ready && mr_last) begin
            fed_syms <= fed_syms + 1'b1;
            if (fed_syms + 1'b1 == data_symbols + 1'b1) rx_fed <= 1'b1;
        end
        if (md_valid && md_ready) begin
            sym_bits[2 * md_data[7:2] +: 2] <= md_data[1:0];
            if (md_last) begin
                w_busy <= 1'b1;
                w_k <= 0;
            end
        end
        if (w_busy) begin
            if (rx_syms < MAX_SYMBOLS) begin
                rxbuf_we <= 1'b1;
                rxbuf_wa <= w_base + w_k;
                rxbuf_wd <= sym_bits[32 * w_k +: 32];
            end
            w_k <= w_k + 1'b1;
            if (w_k == 2'd2) begin
                w_busy <= 1'b0;
                w_base <= w_base + 2'd3;
                rx_syms <= rx_syms + 1'b1;
            end
        end
    end
end

always @(posedge clk) begin
    if (rxbuf_we) rxbuf[rxbuf_wa] <= rxbuf_wd;
    rxbuf_q <= rxbuf[s_axi_araddr[BA+1:2]];
end

// cross-domain event counters (events are converter samples apart, far slower than this clock)
reg [2:0]  unf_s = 0, ovf_s = 0;
reg [31:0] tx_underflows = 0, rx_overflows = 0;
reg        unf_sticky = 1'b0, ovf_sticky = 1'b0, rx_found = 1'b0;
always @(posedge clk) begin
    unf_s <= {unf_s[1:0], unf_toggle};
    ovf_s <= {ovf_s[1:0], ovf_toggle};
    if (rst) begin
        tx_underflows <= 0; rx_overflows <= 0; unf_sticky <= 1'b0; ovf_sticky <= 1'b0;
    end else begin
        if (unf_s[2] != unf_s[1]) begin tx_underflows <= tx_underflows + 1'b1; unf_sticky <= 1'b1; end
        if (ovf_s[2] != ovf_s[1]) begin rx_overflows <= rx_overflows + 1'b1; ovf_sticky <= 1'b1; end
        if (clear_pulse) begin unf_sticky <= 1'b0; ovf_sticky <= 1'b0; end
    end
end

always @(posedge clk) begin
    if (rst) begin
        rx_armed <= 1'b0;
        rx_found <= 1'b0;
    end else begin
        if (rx_arm_pulse) begin rx_armed <= 1'b1; rx_found <= 1'b0; end
        if (rx_stop_pulse) rx_armed <= 1'b0;
        if (fs_start && fs_valid && forward) rx_found <= 1'b1;
    end
end

// =============================================================================================
// AXI4-Lite slave (one transaction at a time; 0x100-0x13F passes through to the modem)
// =============================================================================================
localparam [2:0] A_IDLE = 3'd0, A_BRESP = 3'd1, A_RDATA = 3'd2, A_MW = 3'd3, A_MR = 3'd4, A_RBUF = 3'd5;
reg [2:0]  a_state = A_IDLE;
reg [11:0] a_addr = 0;
wire [31:0] status = {25'd0, ovf_sticky, unf_sticky, (rx_syms >= data_symbols) && rx_armed,
                      rx_found, rx_armed, tx_done, tx_busy};

function [31:0] reg_read(input [11:0] a);
    begin
        case (a[7:0])
        8'h00: reg_read = CORE_ID;
        8'h04: reg_read = CORE_VERSION;
        8'h0C: reg_read = status;
        8'h10: reg_read = data_symbols;
        8'h14: reg_read = tx_gain;
        8'h18: reg_read = rx_shift;
        8'h1C: reg_read = MAX_SYMBOLS;
        8'h20: reg_read = fs_found;
        8'h24: reg_read = fs_missed;
        8'h28: reg_read = fs_ovf;
        8'h2C: reg_read = rx_syms;
        8'h30: reg_read = tx_samples;
        8'h34: reg_read = tx_underflows;
        8'h38: reg_read = rx_overflows;
        8'h3C: reg_read = rx_samples;
        8'h40: reg_read = {30'd0, cfg_agc, cfg_cfo};
        8'h44: reg_read = {{16{pre_theta[15]}}, pre_theta};
        8'h48: reg_read = {{26{gain_k[5]}}, gain_k};
        default: reg_read = 32'd0;
        endcase
    end
endfunction

always @(posedge clk) begin
    s_axi_awready <= 1'b0;
    s_axi_wready <= 1'b0;
    s_axi_arready <= 1'b0;
    tx_start_pulse <= 1'b0;
    rx_arm_pulse <= 1'b0;
    rx_stop_pulse <= 1'b0;
    clear_pulse <= 1'b0;
    if (modem_rst_count != 0) modem_rst_count <= modem_rst_count - 1'b1;
    if (rst) begin
        a_state <= A_IDLE;
        s_axi_bvalid <= 1'b0;
        s_axi_rvalid <= 1'b0;
        s_axi_bresp <= 2'b00;
        s_axi_rresp <= 2'b00;
        m_awvalid <= 1'b0;
        m_wvalid <= 1'b0;
        m_arvalid <= 1'b0;
        modem_rst_count <= 0;
        data_symbols <= 8'd4;
        tx_gain <= 16'd9170;
        rx_shift <= 4'd4;
        cfg_cfo <= 1'b1;
        cfg_agc <= 1'b1;
    end else begin
        case (a_state)
        A_IDLE: begin
            if (s_axi_awvalid && s_axi_wvalid) begin
                s_axi_awready <= 1'b1;
                s_axi_wready <= 1'b1;
                if (s_axi_awaddr[11:6] == 6'b0001_00) begin           // 0x100-0x13F: the modem
                    m_awaddr <= s_axi_awaddr[5:0];
                    m_wdata <= s_axi_wdata;
                    m_awvalid <= 1'b1;
                    m_wvalid <= 1'b1;
                    a_state <= A_MW;
                end else begin
                    if (s_axi_awaddr[11:10] == 2'b01)
                        txbuf[s_axi_awaddr[BA+1:2]] <= s_axi_wdata;
                    else if (s_axi_awaddr[11:8] == 4'h0) begin
                        case (s_axi_awaddr[7:0])
                        8'h08: begin
                            if (s_axi_wdata[0]) begin rx_arm_pulse <= 1'b1; modem_rst_count <= 4'd8; end
                            if (s_axi_wdata[1]) tx_start_pulse <= 1'b1;
                            if (s_axi_wdata[2]) rx_stop_pulse <= 1'b1;
                            if (s_axi_wdata[8]) clear_pulse <= 1'b1;
                        end
                        8'h10: data_symbols <= (s_axi_wdata[7:0] == 0) ? 8'd1
                                             : (s_axi_wdata[7:0] > MAX_SYMBOLS) ? MAX_SYMBOLS[7:0] : s_axi_wdata[7:0];
                        8'h14: tx_gain <= s_axi_wdata[15:0];
                        8'h18: rx_shift <= (s_axi_wdata[3:0] > 4'd8) ? 4'd8 : s_axi_wdata[3:0];
                        8'h40: begin cfg_cfo <= s_axi_wdata[0]; cfg_agc <= s_axi_wdata[1]; end
                        default: ;
                        endcase
                    end
                    s_axi_bresp <= 2'b00;
                    s_axi_bvalid <= 1'b1;
                    a_state <= A_BRESP;
                end
            end else if (s_axi_arvalid) begin
                s_axi_arready <= 1'b1;
                a_addr <= s_axi_araddr;
                s_axi_rresp <= 2'b00;
                if (s_axi_araddr[11:6] == 6'b0001_00) begin
                    m_araddr <= s_axi_araddr[5:0];
                    m_arvalid <= 1'b1;
                    a_state <= A_MR;
                end else if (s_axi_araddr[11:10] == 2'b10) begin
                    a_state <= A_RBUF;                               // rxbuf_q holds the word next clock
                end else begin
                    s_axi_rdata <= (s_axi_araddr[11:8] == 4'h0) ? reg_read(s_axi_araddr) : 32'd0;
                    s_axi_rvalid <= 1'b1;
                    a_state <= A_RDATA;
                end
            end
        end
        A_BRESP: if (s_axi_bready) begin s_axi_bvalid <= 1'b0; a_state <= A_IDLE; end
        A_RDATA: if (s_axi_rready) begin s_axi_rvalid <= 1'b0; a_state <= A_IDLE; end
        A_RBUF: begin
            s_axi_rdata <= rxbuf_q;
            s_axi_rvalid <= 1'b1;
            a_state <= A_RDATA;
        end
        A_MW: begin
            if (m_awready) m_awvalid <= 1'b0;
            if (m_wready) m_wvalid <= 1'b0;
            if (m_bvalid) begin
                s_axi_bresp <= m_bresp;
                s_axi_bvalid <= 1'b1;
                a_state <= A_BRESP;
            end
        end
        A_MR: begin
            if (m_arready) m_arvalid <= 1'b0;
            if (m_rvalid) begin
                s_axi_rdata <= m_rdata;
                s_axi_rresp <= m_rresp;
                s_axi_rvalid <= 1'b1;
                a_state <= A_RDATA;
            end
        end
        default: a_state <= A_IDLE;
        endcase
    end
end

endmodule
