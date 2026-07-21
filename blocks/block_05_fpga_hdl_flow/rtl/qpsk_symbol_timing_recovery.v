// Lab 5.13b - continuous QPSK Gardner symbol timing recovery.
//
// This is the complex counterpart of bpsk_symbol_timing_recovery.  A modulo-one
// timing NCO requests two interpolated samples per symbol (centre and midpoint).
// The timing error uses both axes:
//
//   e = sign(sign(mid.I) * sign(on.I-prev.I)
//          + sign(mid.Q) * sign(on.Q-prev.Q))
//
// so the loop is amplitude independent and needs no TED multipliers.  The two
// linear-interpolator products are the only multipliers.  The PI filter adjusts
// the NCO step around 2/SPS and therefore follows sample-clock mismatch instead
// of selecting one fixed phase for the whole burst.

`timescale 1ns/1ps

module qpsk_symbol_timing_recovery #(
    parameter integer W = 16,
    parameter integer SPS = 8,
    parameter integer INDEX_W = 16,
    parameter integer NCO_W = 16,
    parameter integer INTEG_W = 24
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
localparam integer K1_TERM   = (NCO_ONE / 256);
localparam integer K2_TERM   = (NCO_ONE / 4096);
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
wire signed [1:0] sign_mid_i = (y_mid_i > 0) ? 2'sd1 : (y_mid_i < 0) ? -2'sd1 : 2'sd0;
wire signed [1:0] sign_mid_q = (y_mid_q > 0) ? 2'sd1 : (y_mid_q < 0) ? -2'sd1 : 2'sd0;
wire signed [1:0] sign_dy_i = (dy_i > 0) ? 2'sd1 : (dy_i < 0) ? -2'sd1 : 2'sd0;
wire signed [1:0] sign_dy_q = (dy_q > 0) ? 2'sd1 : (dy_q < 0) ? -2'sd1 : 2'sd0;
wire signed [2:0] axis_i = sign_mid_i * sign_dy_i;
wire signed [2:0] axis_q = sign_mid_q * sign_dy_q;
wire signed [3:0] axis_sum = axis_i + axis_q;
wire signed [2:0] e_ted = (axis_sum > 0) ? 3'sd1 :
                          (axis_sum < 0) ? -3'sd1 : 3'sd0;

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
