// Lab 5.8b - BPSK Gardner symbol timing recovery
//
// Drop-in alternative to bpsk_symbol_timing_sampler: instead of decimating the
// matched-filter stream at a fixed phase (which cannot follow a samples-per-symbol
// error / timing drift over a burst), this closes a digital timing-recovery loop:
//
//   * decrementing modulo-1 NCO produces 2 strobes/symbol (on-time + mid-symbol),
//   * a linear interpolator evaluates the matched-filter stream at each strobe
//     (mu ~= nco<<2, exact for the nominal step w = 2/SPS),
//   * a sign-Gardner timing-error detector  e = sgn(y_mid)*sgn(y_on[k]-y_on[k-1])
//     (amplitude-independent -> stable across RX gain / signal level),
//   * a proportional-integral loop filter steers the NCO step w.
//
// The integer datapath is a bit-exact port of a validated fixed-point model:
// e in {-1,0,+1}, so the loop uses constant +/-K steps only (no multipliers in the
// loop). The single interpolator multiply is the only product. Output is the
// on-time complex symbol; the downstream decision_mode + hard decision are
// unchanged. start_offset positions the first on-time strobe, then the loop tracks.

`timescale 1ns/1ps

module bpsk_symbol_timing_recovery #(
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
    output reg signed [W-1:0]       out_q
);

localparam integer NCO_ONE   = (1 <<< NCO_W);          // 1.0 in Q.16  (65536)
localparam integer W_NOMINAL = ((2 <<< NCO_W) / SPS);  // 2 strobes/symbol (16384 @SPS=8)
localparam integer K1_TERM   = (NCO_ONE / 256);        // proportional |step|  (256)
localparam integer K2_TERM   = (NCO_ONE / 4096);       // integral |increment| (16)
localparam integer W_MIN     = W_NOMINAL - 2048;
localparam integer W_MAX     = W_NOMINAL + 2048;
localparam signed [W-1:0] SAT_MAX = {1'b0, {(W-1){1'b1}}};   //  32767
localparam signed [W-1:0] SAT_MIN = {1'b1, {(W-1){1'b0}}};   // -32768

reg [INDEX_W-1:0]        in_count;
reg                      started;
reg signed [31:0]        nco;          // Q.16, kept in [0,1)
reg signed [31:0]        w_step;       // Q.16 NCO step
reg signed [INTEG_W-1:0] integ;        // integral accumulator (Q.16)
reg signed [W-1:0]       x_prev_i;
reg signed [W-1:0]       x_prev_q;
reg signed [W-1:0]       y_on_prev_i;
reg signed [W-1:0]       y_mid_i;
reg                      parity;       // 0 = on-time strobe, 1 = mid-symbol strobe
reg [INDEX_W-1:0]        emitted;

// mu ~= nco/w ~= nco<<2 for w ~= 2/SPS; saturate just below 1.0
wire signed [31:0] mu_raw = nco <<< 2;
wire signed [31:0] mu = (mu_raw >= NCO_ONE) ? (NCO_ONE - 1) : mu_raw;

// linear interpolation: y = x_prev + ((cur - x_prev) * mu) >>> NCO_W   (mu in [0,1))
wire signed [31:0] di    = $signed(in_i) - $signed(x_prev_i);
wire signed [31:0] dq    = $signed(in_q) - $signed(x_prev_q);
wire signed [63:0] mu_di = di * mu;
wire signed [63:0] mu_dq = dq * mu;
wire signed [31:0] y_i32 = $signed(x_prev_i) + (mu_di >>> NCO_W);
wire signed [31:0] y_q32 = $signed(x_prev_q) + (mu_dq >>> NCO_W);
wire signed [W-1:0] y_i = (y_i32 > SAT_MAX) ? SAT_MAX : (y_i32 < SAT_MIN) ? SAT_MIN : y_i32[W-1:0];
wire signed [W-1:0] y_q = (y_q32 > SAT_MAX) ? SAT_MAX : (y_q32 < SAT_MIN) ? SAT_MIN : y_q32[W-1:0];

// sign-Gardner timing error  e = sgn(y_mid) * sgn(y_on - y_on_prev)
wire signed [31:0] dy = $signed(y_i) - $signed(y_on_prev_i);
wire signed [1:0]  sgn_mid = (y_mid_i > 0) ? 2'sd1 : (y_mid_i < 0) ? -2'sd1 : 2'sd0;
wire signed [1:0]  sgn_dy  = (dy      > 0) ? 2'sd1 : (dy      < 0) ? -2'sd1 : 2'sd0;
wire signed [2:0]  e_ted   = sgn_mid * sgn_dy;   // {-1,0,+1}

wire signed [INTEG_W-1:0] integ_next = integ + K2_TERM * e_ted;
wire signed [31:0] w_unclamped = W_NOMINAL + (K1_TERM * e_ted) + integ_next;
wire signed [31:0] w_clamped   = (w_unclamped < W_MIN) ? W_MIN :
                                 (w_unclamped > W_MAX) ? W_MAX : w_unclamped;

always @(posedge clk) begin
    if (rst) begin
        in_count    <= {INDEX_W{1'b0}};
        started     <= 1'b0;
        nco         <= 32'sd0;
        w_step      <= W_NOMINAL;
        integ       <= {INTEG_W{1'b0}};
        x_prev_i    <= {W{1'b0}};
        x_prev_q    <= {W{1'b0}};
        y_on_prev_i <= {W{1'b0}};
        y_mid_i     <= {W{1'b0}};
        parity      <= 1'b0;
        emitted     <= {INDEX_W{1'b0}};
        out_valid   <= 1'b0;
        out_i       <= {W{1'b0}};
        out_q       <= {W{1'b0}};
    end else begin
        out_valid <= 1'b0;
        out_i     <= {W{1'b0}};
        out_q     <= {W{1'b0}};

        if (in_valid) begin
            if (!started) begin
                if (in_count == start_offset) begin
                    // Transition: force the first (on-time) strobe on this sample.
                    started     <= 1'b1;
                    parity      <= 1'b1;            // next strobe is mid-symbol
                    y_on_prev_i <= x_prev_i;        // mu=0 -> y = x_prev
                    out_valid   <= 1'b1;
                    out_i       <= x_prev_i;
                    out_q       <= x_prev_q;
                    emitted     <= {{(INDEX_W-1){1'b0}}, 1'b1};
                    nco         <= (NCO_ONE - w_step);   // nco - w + 1 with nco = 0
                end else begin
                    in_count <= in_count + 1'b1;
                end
                x_prev_i <= in_i;
                x_prev_q <= in_q;
            end else if (emitted < symbol_count) begin
                if (nco < w_step) begin
                    if (parity == 1'b0) begin
                        // on-time symbol: run TED + loop filter, emit
                        integ       <= integ_next;
                        w_step      <= w_clamped;
                        y_on_prev_i <= y_i;
                        out_valid   <= 1'b1;
                        out_i       <= y_i;
                        out_q       <= y_q;
                        emitted     <= emitted + 1'b1;
                    end else begin
                        // mid-symbol strobe: store for the next Gardner error
                        y_mid_i <= y_i;
                    end
                    parity <= ~parity;
                    nco    <= (nco - w_step + NCO_ONE);
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
