// Lab 5.13b - continuous QPSK Gardner symbol timing recovery.
//
// This is the complex counterpart of bpsk_symbol_timing_recovery.  A modulo-one
// timing NCO requests two interpolated samples per symbol (centre and midpoint).
// The timing error uses both axes:
//
//   e = sign(mid.I * (on.I-prev.I) + mid.Q * (on.Q-prev.Q))
//
// The dot product is invariant to a common carrier rotation.  The earlier
// product-of-signs approximation had phase-dependent detector gain: live paired
// A/B produced only 12/400 clean attempts near zero injected CFO, but 153/400 at
// 55 kHz as carrier rotation effectively dithered the detector axes.  Two TED
// multipliers remove that axis artefact; the sign output keeps the PI update
// bounded to {-1,0,+1}.

`timescale 1ns/1ps

module qpsk_symbol_timing_recovery #(
    parameter integer W = 16,
    parameter integer SPS = 8,
    parameter integer INDEX_W = 16,
    parameter integer NCO_W = 16,
    parameter integer INTEG_W = 24,
    parameter integer K1_TERM_VALUE = ((1 <<< NCO_W) / 256),
    parameter integer K2_TERM_VALUE = 3
) (
    input  wire                     clk,
    input  wire                     rst,
    input  wire                     in_valid,
    input  wire signed [W-1:0]      in_i,
    input  wire signed [W-1:0]      in_q,
    input  wire [INDEX_W-1:0]       start_offset,
    input  wire [INDEX_W-1:0]       symbol_count,
    output reg                      out_valid,
    output reg signed [W-1:0]       out_i,
    output reg signed [W-1:0]       out_q,
    output wire [NCO_W-1:0]         timing_mu,
    output wire signed [NCO_W:0]    timing_omega,
    output reg signed [2:0]         timing_error
);

localparam integer NCO_ONE   = (1 <<< NCO_W);
localparam integer W_NOMINAL = ((2 <<< NCO_W) / SPS);
// The rotation-invariant detector is active on more symbol transitions than
// the old axis-sign approximation.  The model's carrier-phase and +/-200 ppm
// grid selects a strong proportional correction but a four-times quieter
// integral term, preventing data-dependent integral walk while keeping pull-in.
localparam integer K1_TERM   = K1_TERM_VALUE;
localparam integer K2_TERM   = K2_TERM_VALUE;
localparam integer W_MIN     = W_NOMINAL - 2048;
localparam integer W_MAX     = W_NOMINAL + 2048;
localparam signed [W-1:0] SAT_MAX = {1'b0, {(W-1){1'b1}}};
localparam signed [W-1:0] SAT_MIN = {1'b1, {(W-1){1'b0}}};

reg [INDEX_W-1:0]        in_count;
reg                      started;
reg signed [31:0]        nco;
reg signed [31:0]        w_step;
reg signed [INTEG_W-1:0] integ;
reg signed [W-1:0]       x_prev_i;
reg signed [W-1:0]       x_prev_q;
reg signed [W-1:0]       y_on_prev_i;
reg signed [W-1:0]       y_on_prev_q;
reg signed [W-1:0]       y_mid_i;
reg signed [W-1:0]       y_mid_q;
reg                      parity;
reg [INDEX_W-1:0]        emitted;

// The fixed model uses mu ~= nco/w ~= nco<<2 around the nominal 2/SPS step.
wire signed [31:0] mu_raw = nco <<< 2;
wire signed [31:0] mu = (mu_raw >= NCO_ONE) ? (NCO_ONE - 1) : mu_raw;

wire signed [31:0] di = $signed(in_i) - $signed(x_prev_i);
wire signed [31:0] dq = $signed(in_q) - $signed(x_prev_q);
wire signed [63:0] mu_di = di * mu;
wire signed [63:0] mu_dq = dq * mu;
wire signed [31:0] y_i32 = $signed(x_prev_i) + (mu_di >>> NCO_W);
wire signed [31:0] y_q32 = $signed(x_prev_q) + (mu_dq >>> NCO_W);
wire signed [W-1:0] y_i = (y_i32 > SAT_MAX) ? SAT_MAX :
                           (y_i32 < SAT_MIN) ? SAT_MIN : y_i32[W-1:0];
wire signed [W-1:0] y_q = (y_q32 > SAT_MAX) ? SAT_MAX :
                           (y_q32 < SAT_MIN) ? SAT_MIN : y_q32[W-1:0];

wire signed [W:0] dy_i = $signed(y_i) - $signed(y_on_prev_i);
wire signed [W:0] dy_q = $signed(y_q) - $signed(y_on_prev_q);
wire signed [2*W:0] ted_product_i = $signed(y_mid_i) * $signed(dy_i);
wire signed [2*W:0] ted_product_q = $signed(y_mid_q) * $signed(dy_q);
wire signed [2*W+1:0] ted_dot =
    {ted_product_i[2*W], ted_product_i} + {ted_product_q[2*W], ted_product_q};
wire signed [2:0] e_ted = (ted_dot > 0) ? 3'sd1 :
                          (ted_dot < 0) ? -3'sd1 : 3'sd0;

wire signed [INTEG_W-1:0] integ_next = integ + K2_TERM * e_ted;
wire signed [31:0] w_unclamped = W_NOMINAL + (K1_TERM * e_ted) + integ_next;
wire signed [31:0] w_clamped = (w_unclamped < W_MIN) ? W_MIN :
                               (w_unclamped > W_MAX) ? W_MAX : w_unclamped;

assign timing_mu = mu[NCO_W-1:0];
assign timing_omega = w_step[NCO_W:0];

always @(posedge clk) begin
    if (rst) begin
        in_count       <= {INDEX_W{1'b0}};
        started        <= 1'b0;
        nco            <= 32'sd0;
        w_step         <= W_NOMINAL;
        integ          <= {INTEG_W{1'b0}};
        x_prev_i       <= {W{1'b0}};
        x_prev_q       <= {W{1'b0}};
        y_on_prev_i    <= {W{1'b0}};
        y_on_prev_q    <= {W{1'b0}};
        y_mid_i        <= {W{1'b0}};
        y_mid_q        <= {W{1'b0}};
        parity         <= 1'b0;
        emitted        <= {INDEX_W{1'b0}};
        out_valid      <= 1'b0;
        out_i          <= {W{1'b0}};
        out_q          <= {W{1'b0}};
        timing_error   <= 3'sd0;
    end else begin
        out_valid <= 1'b0;
        out_i <= {W{1'b0}};
        out_q <= {W{1'b0}};

        if (in_valid) begin
            if (!started) begin
                if (in_count == start_offset) begin
                    started        <= 1'b1;
                    parity         <= 1'b1;
                    y_on_prev_i    <= x_prev_i;
                    y_on_prev_q    <= x_prev_q;
                    out_valid      <= 1'b1;
                    out_i          <= x_prev_i;
                    out_q          <= x_prev_q;
                    emitted        <= {{(INDEX_W-1){1'b0}}, 1'b1};
                    nco            <= NCO_ONE - w_step;
                    timing_error   <= 3'sd0;
                end else begin
                    in_count <= in_count + 1'b1;
                end
                x_prev_i <= in_i;
                x_prev_q <= in_q;
            end else if (emitted < symbol_count) begin
                if (nco < w_step) begin
                    if (parity == 1'b0) begin
                        integ          <= integ_next;
                        w_step         <= w_clamped;
                        y_on_prev_i    <= y_i;
                        y_on_prev_q    <= y_q;
                        out_valid      <= 1'b1;
                        out_i          <= y_i;
                        out_q          <= y_q;
                        emitted        <= emitted + 1'b1;
                        timing_error   <= e_ted;
                    end else begin
                        y_mid_i <= y_i;
                        y_mid_q <= y_q;
                    end
                    parity <= ~parity;
                    nco <= nco - w_step + NCO_ONE;
                end else begin
                    nco <= nco - w_step;
                end
                x_prev_i <= in_i;
                x_prev_q <= in_q;
            end
        end
    end
end

endmodule
