`timescale 1ns/1ps

`ifndef OFDM_IFFT_PIPELINED
`define OFDM_IFFT_PIPELINED 1
`endif

// Shared-clock AXI4-Stream + AXI4-Lite packaging of the Block 8 OFDM chain.
//
//   s_axis_tx  (bit pairs)  -> ofdm_tx_cp16_path                     -> m_axis_tx  (IQ)
//   s_axis_rx  (IQ)         -> ofdm_cp16_remover -> ofdm_fft64_sequential
//                           -> ofdm_subcarrier_extractor
//                           -> ofdm_pilot_phase_corrector -> ofdm_qpsk_demapper -> m_axis_rx (bits)
//
// The wrapper only renames and packs signals; the datapath modules and their
// arithmetic are unchanged. Stream formats:
//   s_axis_tx_tdata[1:0]  one QPSK bit pair; 48 pairs form one OFDM symbol.
//                         s_axis_tx_tlast is not used: framing is by count.
//   m_axis_tx_tdata       {Q[15:0], I[15:0]} Q1.15; 80 samples per symbol
//                         (CP first), tlast on the 80th.
//   s_axis_rx_tdata       {Q[15:0], I[15:0]} Q1.15; 80 samples per symbol,
//                         tlast on the 80th (a misplaced tlast sets
//                         RX_FRAME_ERROR, see ofdm_cp16_remover).
//   m_axis_rx_tdata[7:0]  {data_index[5:0], bits[1:0]}; 48 per symbol in FFT
//                         bin order (data indices 24..47, then 0..23), tlast
//                         on the 48th.
//
// AXI4-Lite register map (32-bit, byte addresses):
//   0x00 ID          "OFDM" (0x4F46444D)
//   0x04 VERSION     0x00010000
//   0x08 CONTROL     [0] datapath reset, held while 1 (clears every counter)
//                    [8] write 1: clear the sticky frame-error flags
//   0x0C STATUS      [0] datapath reset  [1] TX IFFT busy  [2] RX FFT busy
//                    [3] TX frame error (sticky)  [4] RX frame error (sticky)
//                    [5] last symbol's pilots had zero energy
//   0x10 TX_SAT      IFFT butterfly saturations
//   0x14 FFT_SAT     [31:16] conjugation saturations, [15:0] butterfly saturations
//   0x18 EQ_SAT      equalizer saturations
//   0x1C TX_SYMBOLS  OFDM symbols sent (m_axis_tx tlast handshakes)
//   0x20 RX_SYMBOLS  OFDM symbols received (m_axis_rx tlast handshakes)
//   0x24 PHASE       last pilot phase, sign-extended (pi = 2^15)
//   0x28 COEFF       [31:16] imaginary, [15:0] real part of the last Q2.14
//                    correction coefficient
// All counters count from the last reset (aresetn or CONTROL[0]).
module ofdm_axi_modem #(
    parameter integer AXI_ADDR_W = 6,
    parameter integer AXI_DATA_W = 32,
    parameter integer PIPELINED = `OFDM_IFFT_PIPELINED
) (
    input  wire                         aclk,
    input  wire                         aresetn,

    input  wire                         s_axis_tx_tvalid,
    output wire                         s_axis_tx_tready,
    input  wire [7:0]                   s_axis_tx_tdata,
    input  wire                         s_axis_tx_tlast,
    output wire                         m_axis_tx_tvalid,
    input  wire                         m_axis_tx_tready,
    output wire [31:0]                  m_axis_tx_tdata,
    output wire                         m_axis_tx_tlast,

    input  wire                         s_axis_rx_tvalid,
    output wire                         s_axis_rx_tready,
    input  wire [31:0]                  s_axis_rx_tdata,
    input  wire                         s_axis_rx_tlast,
    output wire                         m_axis_rx_tvalid,
    input  wire                         m_axis_rx_tready,
    output wire [7:0]                   m_axis_rx_tdata,
    output wire                         m_axis_rx_tlast,

    input  wire [AXI_ADDR_W-1:0]        s_axi_awaddr,
    input  wire                         s_axi_awvalid,
    output reg                          s_axi_awready,
    input  wire [AXI_DATA_W-1:0]        s_axi_wdata,
    input  wire [(AXI_DATA_W/8)-1:0]    s_axi_wstrb,
    input  wire                         s_axi_wvalid,
    output reg                          s_axi_wready,
    output reg  [1:0]                   s_axi_bresp,
    output reg                          s_axi_bvalid,
    input  wire                         s_axi_bready,
    input  wire [AXI_ADDR_W-1:0]        s_axi_araddr,
    input  wire                         s_axi_arvalid,
    output reg                          s_axi_arready,
    output reg  [AXI_DATA_W-1:0]        s_axi_rdata,
    output reg  [1:0]                   s_axi_rresp,
    output reg                          s_axi_rvalid,
    input  wire                         s_axi_rready
);

    localparam integer AXI_STRB_W = AXI_DATA_W / 8;
    localparam [AXI_ADDR_W-1:0] REG_ID = 6'h00;
    localparam [AXI_ADDR_W-1:0] REG_VERSION = 6'h04;
    localparam [AXI_ADDR_W-1:0] REG_CONTROL = 6'h08;
    localparam [AXI_ADDR_W-1:0] REG_STATUS = 6'h0C;
    localparam [AXI_ADDR_W-1:0] REG_TX_SAT = 6'h10;
    localparam [AXI_ADDR_W-1:0] REG_FFT_SAT = 6'h14;
    localparam [AXI_ADDR_W-1:0] REG_EQ_SAT = 6'h18;
    localparam [AXI_ADDR_W-1:0] REG_TX_SYMBOLS = 6'h1C;
    localparam [AXI_ADDR_W-1:0] REG_RX_SYMBOLS = 6'h20;
    localparam [AXI_ADDR_W-1:0] REG_PHASE = 6'h24;
    localparam [AXI_ADDR_W-1:0] REG_COEFF = 6'h28;
    localparam [AXI_DATA_W-1:0] CORE_ID = 32'h4F46444D; // "OFDM"
    localparam [AXI_DATA_W-1:0] CORE_VERSION = 32'h00010000;

    reg datapath_reset;
    wire core_resetn = aresetn && !datapath_reset;

    // ------------------------------------------------------------------
    // TX
    // ------------------------------------------------------------------
    wire signed [15:0] tx_re;
    wire signed [15:0] tx_im;
    wire tx_busy;
    wire [15:0] tx_saturation_count;
    wire tx_frame_error;

    ofdm_tx_cp16_path #(.PIPELINED(PIPELINED)) u_tx (
        .clk(aclk),
        .resetn(core_resetn),
        .bits_valid(s_axis_tx_tvalid),
        .bits_ready(s_axis_tx_tready),
        .bits_in(s_axis_tx_tdata[1:0]),
        .sample_valid(m_axis_tx_tvalid),
        .sample_ready(m_axis_tx_tready),
        .sample_re(tx_re),
        .sample_im(tx_im),
        .sample_index(),
        .sample_is_cp(),
        .sample_last(m_axis_tx_tlast),
        .ifft_busy(tx_busy),
        .total_saturation_count(tx_saturation_count),
        .frame_error(tx_frame_error)
    );

    assign m_axis_tx_tdata = {tx_im, tx_re};

    // ------------------------------------------------------------------
    // RX
    // ------------------------------------------------------------------
    wire useful_valid;
    wire useful_ready;
    wire signed [15:0] useful_re;
    wire signed [15:0] useful_im;
    wire useful_last;
    wire rx_frame_error;

    wire fft_bin_valid;
    wire fft_bin_ready;
    wire signed [15:0] fft_bin_re;
    wire signed [15:0] fft_bin_im;
    wire [5:0] fft_bin_index;
    wire fft_bin_last;
    wire fft_busy;
    wire [15:0] fft_saturation_count;
    wire [15:0] fft_conjugation_saturation_count;

    wire data_valid;
    wire data_ready;
    wire signed [15:0] data_re;
    wire signed [15:0] data_im;
    wire [5:0] data_index;
    wire data_last;

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
    wire signed [15:0] coeff_re;
    wire signed [15:0] coeff_im;
    wire signed [15:0] last_phase;
    wire last_zero_energy;
    wire [31:0] eq_saturation_count;

    wire [1:0] rx_bits;
    wire [5:0] rx_bits_index;

    ofdm_cp16_remover u_cp_remove (
        .clk(aclk),
        .resetn(core_resetn),
        .in_i(s_axis_rx_tdata[15:0]),
        .in_q(s_axis_rx_tdata[31:16]),
        .in_valid(s_axis_rx_tvalid),
        .in_ready(s_axis_rx_tready),
        .in_last(s_axis_rx_tlast),
        .out_i(useful_re),
        .out_q(useful_im),
        .out_valid(useful_valid),
        .out_ready(useful_ready),
        .out_last(useful_last),
        .frame_error(rx_frame_error)
    );

    ofdm_fft64_sequential #(.PIPELINED(PIPELINED)) u_fft (
        .clk(aclk),
        .resetn(core_resetn),
        .sample_valid(useful_valid),
        .sample_ready(useful_ready),
        .sample_re(useful_re),
        .sample_im(useful_im),
        .bin_valid(fft_bin_valid),
        .bin_ready(fft_bin_ready),
        .bin_re(fft_bin_re),
        .bin_im(fft_bin_im),
        .bin_index(fft_bin_index),
        .bin_last(fft_bin_last),
        .busy(fft_busy),
        .total_saturation_count(fft_saturation_count),
        .conjugation_saturation_count(fft_conjugation_saturation_count)
    );

    ofdm_subcarrier_extractor u_extract (
        .resetn(core_resetn),
        .bin_valid(fft_bin_valid),
        .bin_ready(fft_bin_ready),
        .bin_re(fft_bin_re),
        .bin_im(fft_bin_im),
        .bin_index(fft_bin_index),
        .bin_last(fft_bin_last),
        .data_valid(data_valid),
        .data_ready(data_ready),
        .data_re(data_re),
        .data_im(data_im),
        .data_bin_index(),
        .data_index(data_index),
        .data_last(data_last),
        .pilot_valid(pilot_valid),
        .pilot_ready(pilot_ready),
        .pilot_re(pilot_re),
        .pilot_im(pilot_im),
        .pilot_bin_index(),
        .pilot_slot(),
        .pilot_ref_re(pilot_ref_re)
    );

    ofdm_pilot_phase_corrector u_correct (
        .clk(aclk),
        .resetn(core_resetn),
        .data_valid(data_valid),
        .data_ready(data_ready),
        .data_re(data_re),
        .data_im(data_im),
        .data_index(data_index),
        .data_last(data_last),
        .pilot_valid(pilot_valid),
        .pilot_ready(pilot_ready),
        .pilot_re(pilot_re),
        .pilot_im(pilot_im),
        .pilot_ref_re(pilot_ref_re),
        .out_valid(eq_valid),
        .out_ready(eq_ready),
        .out_re(eq_re),
        .out_im(eq_im),
        .out_index(eq_index),
        .out_last(eq_last),
        .applied_coeff_re(coeff_re),
        .applied_coeff_im(coeff_im),
        .last_phase(last_phase),
        .last_zero_energy(last_zero_energy),
        .symbol_count(),
        .saturation_count(eq_saturation_count)
    );

    ofdm_qpsk_demapper u_demap (
        .resetn(core_resetn),
        .symbol_valid(eq_valid),
        .symbol_ready(eq_ready),
        .symbol_re(eq_re),
        .symbol_im(eq_im),
        .data_index(eq_index),
        .symbol_last(eq_last),
        .bits_valid(m_axis_rx_tvalid),
        .bits_ready(m_axis_rx_tready),
        .bits_out(rx_bits),
        .bits_index(rx_bits_index),
        .bits_last(m_axis_rx_tlast)
    );

    assign m_axis_rx_tdata = {rx_bits_index, rx_bits};

    // ------------------------------------------------------------------
    // Status counters
    // ------------------------------------------------------------------
    reg tx_frame_error_sticky;
    reg rx_frame_error_sticky;
    reg [31:0] tx_symbol_count;
    reg [31:0] rx_symbol_count;
    reg clear_sticky;

    always @(posedge aclk) begin
        if (!core_resetn) begin
            tx_frame_error_sticky <= 1'b0;
            rx_frame_error_sticky <= 1'b0;
            tx_symbol_count <= 32'd0;
            rx_symbol_count <= 32'd0;
        end else begin
            if (clear_sticky) begin
                tx_frame_error_sticky <= 1'b0;
                rx_frame_error_sticky <= 1'b0;
            end
            if (tx_frame_error)
                tx_frame_error_sticky <= 1'b1;
            if (rx_frame_error)
                rx_frame_error_sticky <= 1'b1;
            if (m_axis_tx_tvalid && m_axis_tx_tready && m_axis_tx_tlast)
                tx_symbol_count <= tx_symbol_count + 32'd1;
            if (m_axis_rx_tvalid && m_axis_rx_tready && m_axis_rx_tlast)
                rx_symbol_count <= rx_symbol_count + 32'd1;
        end
    end

    // ------------------------------------------------------------------
    // AXI4-Lite
    // ------------------------------------------------------------------
    reg [AXI_ADDR_W-1:0] awaddr_latched;
    reg awaddr_valid;
    reg [AXI_DATA_W-1:0] wdata_latched;
    reg [AXI_STRB_W-1:0] wstrb_latched;
    reg wdata_valid;
    reg [AXI_DATA_W-1:0] read_word;

    always @(*) begin
        case (s_axi_araddr)
            REG_ID: read_word = CORE_ID;
            REG_VERSION: read_word = CORE_VERSION;
            REG_CONTROL: read_word = {{(AXI_DATA_W-1){1'b0}}, datapath_reset};
            REG_STATUS: read_word = {
                {(AXI_DATA_W-6){1'b0}},
                last_zero_energy,
                rx_frame_error_sticky,
                tx_frame_error_sticky,
                fft_busy,
                tx_busy,
                datapath_reset
            };
            REG_TX_SAT: read_word = {16'd0, tx_saturation_count};
            REG_FFT_SAT: read_word = {fft_conjugation_saturation_count, fft_saturation_count};
            REG_EQ_SAT: read_word = eq_saturation_count;
            REG_TX_SYMBOLS: read_word = tx_symbol_count;
            REG_RX_SYMBOLS: read_word = rx_symbol_count;
            REG_PHASE: read_word = {{16{last_phase[15]}}, last_phase};
            REG_COEFF: read_word = {coeff_im, coeff_re};
            default: read_word = {AXI_DATA_W{1'b0}};
        endcase
    end

    always @(posedge aclk) begin
        if (!aresetn) begin
            s_axi_awready <= 1'b0;
            s_axi_wready <= 1'b0;
            s_axi_bresp <= 2'b00;
            s_axi_bvalid <= 1'b0;
            s_axi_arready <= 1'b0;
            s_axi_rdata <= {AXI_DATA_W{1'b0}};
            s_axi_rresp <= 2'b00;
            s_axi_rvalid <= 1'b0;
            datapath_reset <= 1'b0;
            clear_sticky <= 1'b0;
            awaddr_latched <= {AXI_ADDR_W{1'b0}};
            awaddr_valid <= 1'b0;
            wdata_latched <= {AXI_DATA_W{1'b0}};
            wstrb_latched <= {AXI_STRB_W{1'b0}};
            wdata_valid <= 1'b0;
        end else begin
            clear_sticky <= 1'b0;

            s_axi_awready <= (!awaddr_valid) && (!s_axi_bvalid);
            s_axi_wready <= (!wdata_valid) && (!s_axi_bvalid);
            s_axi_arready <= (!s_axi_rvalid);

            if (s_axi_awready && s_axi_awvalid) begin
                awaddr_latched <= s_axi_awaddr;
                awaddr_valid <= 1'b1;
            end
            if (s_axi_wready && s_axi_wvalid) begin
                wdata_latched <= s_axi_wdata;
                wstrb_latched <= s_axi_wstrb;
                wdata_valid <= 1'b1;
            end

            if (awaddr_valid && wdata_valid && !s_axi_bvalid) begin
                if (awaddr_latched == REG_CONTROL) begin
                    if (wstrb_latched[0])
                        datapath_reset <= wdata_latched[0];
                    if (wstrb_latched[1] && wdata_latched[8])
                        clear_sticky <= 1'b1;
                end
                awaddr_valid <= 1'b0;
                wdata_valid <= 1'b0;
                s_axi_bvalid <= 1'b1;
                s_axi_bresp <= 2'b00;
            end
            if (s_axi_bvalid && s_axi_bready)
                s_axi_bvalid <= 1'b0;

            if (s_axi_arready && s_axi_arvalid) begin
                s_axi_rdata <= read_word;
                s_axi_rresp <= 2'b00;
                s_axi_rvalid <= 1'b1;
            end
            if (s_axi_rvalid && s_axi_rready)
                s_axi_rvalid <= 1'b0;
        end
    end

endmodule
