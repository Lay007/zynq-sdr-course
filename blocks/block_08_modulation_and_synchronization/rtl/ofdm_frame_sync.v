`timescale 1ns/1ps

// Issue #48, stage 4b: find an OFDM frame in a continuous sample stream and hand the modem its
// symbols, 80 samples each with `last` on the 80th, as ofdm_axi_modem's receiver expects.
//
// The frame starts with a Schmidl & Cox preamble (CP + a 64-sample body of two equal halves, see
// tools/ofdm_rf_link.py). Bit-exact model: tools/ofdm_frame_sync_fixed.py.
//
//   x       = DC-tracked input >> 4 (12 bits, as from the AD9361): m += (x - m) >> 8, x - m
//   p[n]    = conj(x[n-32]) * x[n],     P = sum of the last 32 p
//   e[n]    = |x[n]|^2,                  E = sum of the last 64 e,  R = E >> 1
//   above   = R > E_MIN  and  4 * |P >> SHIFT|^2 > 3 * (R >> SHIFT)^2         (M > 0.75)
//
// A run of `above` of at least MIN_RUN samples is the preamble's plateau; when it ends, its centre
// c (window start index) gives the first symbol after the preamble at c + 8 + 64 - BACKOFF. The
// input is delayed by DELAY samples, so that symbol is still ahead when the plateau has ended, and
// from there FRAME_SYMBOLS * 80 delayed samples go out. The output is the input itself, delayed,
// without the DC tracking (the modem's subcarrier 0 is unused). The input has no back-pressure (a
// converter at a few MS/s); the output goes through a FIFO_DEPTH-sample FIFO with `out_ready`,
// because the modem's receiver is not ready for about 107 clocks after every symbol (its sequential
// FFT): at 2.083 MS/s and 100 MHz (48 clocks per sample) that cost 2 samples per symbol without the
// FIFO. On average the receiver needs between 9 and 12 clocks per sample (in simulation 8 overflowed
// this FIFO, 12 did not), so the board's 48 leave a wide margin. Samples that find the FIFO full are
// counted in `overflows`. A plateau that ends while a
// frame is going out is ignored and counted.
module ofdm_frame_sync #(
    parameter integer E_MIN = 2000,
    parameter integer SHIFT = 8,
    parameter integer MIN_RUN = 8,
    parameter integer BACKOFF = 4,
    parameter integer DELAY = 128,       // power of two, > the decision latency (~70 samples)
    parameter integer FIFO_DEPTH = 16    // power of two
) (
    input  wire               clk,
    input  wire               rst,
    input  wire [7:0]         frame_symbols,     // symbols per frame after the preamble (training + data)
    input  wire               in_valid,
    input  wire signed [15:0] in_re,
    input  wire signed [15:0] in_im,
    output wire               out_valid,
    input  wire               out_ready,
    output wire signed [15:0] out_re,
    output wire signed [15:0] out_im,
    output wire               out_last,
    output wire               frame_start,       // with the first sample of a frame
    output reg  [15:0]        frames_found,
    output reg  [15:0]        frames_missed,     // plateaus that ended while a frame was going out
    output reg  [15:0]        overflows          // samples lost because the output FIFO was full
);

localparam integer H = 32, N = 64, CP = 16;
localparam integer DA = $clog2(DELAY);

// ---------------------------------------------------------------------------------------------
// DC tracker and 12-bit samples
// ---------------------------------------------------------------------------------------------
reg signed [27:0] m_re = 0, m_im = 0;              // DC estimate, 8 fraction bits
wire signed [11:0] s_re = in_re >>> 4;
wire signed [11:0] s_im = in_im >>> 4;
wire signed [27:0] y_re = ($signed({{16{s_re[11]}}, s_re}) <<< 8) - m_re;
wire signed [27:0] y_im = ($signed({{16{s_im[11]}}, s_im}) <<< 8) - m_im;
wire signed [19:0] x_re = y_re >>> 8;
wire signed [19:0] x_im = y_im >>> 8;

// ---------------------------------------------------------------------------------------------
// Delay lines (rings) and running sums
// ---------------------------------------------------------------------------------------------
reg signed [19:0] xr_ring [0:H-1];
reg signed [19:0] xi_ring [0:H-1];
reg signed [47:0] pr_ring [0:H-1];
reg signed [47:0] pi_ring [0:H-1];
reg        [47:0] e_ring  [0:N-1];
reg [4:0] a32 = 0;
reg [5:0] a64 = 0;
reg signed [55:0] P_re = 0, P_im = 0;
reg        [55:0] E = 0;

wire signed [19:0] xo_re = xr_ring[a32];            // x[n-32]
wire signed [19:0] xo_im = xi_ring[a32];
wire signed [47:0] p_re = xo_re * x_re + xo_im * x_im;
wire signed [47:0] p_im = xo_re * x_im - xo_im * x_re;
wire        [47:0] e_n  = x_re * x_re + x_im * x_im;
wire signed [55:0] P_re_n = P_re + p_re - pr_ring[a32];
wire signed [55:0] P_im_n = P_im + p_im - pi_ring[a32];
wire        [55:0] E_n    = E + e_n - e_ring[a64];
wire        [55:0] R_n    = E_n >> 1;
wire signed [55:0] ps_re  = P_re_n >>> SHIFT;
wire signed [55:0] ps_im  = P_im_n >>> SHIFT;
wire        [55:0] rs     = R_n >> SHIFT;
wire               above  = (R_n > E_MIN) &&
                            (4 * (ps_re * ps_re + ps_im * ps_im) > 3 * rs * rs);

// ---------------------------------------------------------------------------------------------
// Plateau, decision, delayed output
// ---------------------------------------------------------------------------------------------
reg [31:0] n = 0;                                   // index of the current input sample
reg        in_run = 1'b0;
reg [31:0] run_start = 0, run_last = 0;
reg        active = 1'b0;
reg [31:0] first = 0;
reg [15:0] count = 0, total = 0;
reg [6:0]  pos = 0;
reg signed [15:0] dl_re [0:DELAY-1];
reg signed [15:0] dl_im [0:DELAY-1];
wire [31:0] d = n - (N - 1);                        // window start of this metric value
wire [31:0] k = n - DELAY;                          // index of the delayed sample read now
wire [31:0] run_c = (run_start + run_last) >> 1;

integer i;
initial begin
    for (i = 0; i < H; i = i + 1) begin
        xr_ring[i] = 0; xi_ring[i] = 0; pr_ring[i] = 0; pi_ring[i] = 0;
    end
    for (i = 0; i < N; i = i + 1) e_ring[i] = 0;
    for (i = 0; i < DELAY; i = i + 1) begin dl_re[i] = 0; dl_im[i] = 0; end
end

// Output FIFO: {frame_start, last, im, re}
localparam integer FA = $clog2(FIFO_DEPTH);
reg [33:0] fifo [0:FIFO_DEPTH-1];
reg [FA:0] wr_ptr = 0, rd_ptr = 0;
wire       fifo_empty = (wr_ptr == rd_ptr);
wire       fifo_full  = (wr_ptr[FA-1:0] == rd_ptr[FA-1:0]) && (wr_ptr[FA] != rd_ptr[FA]);
assign out_valid   = !fifo_empty;
assign {frame_start, out_last, out_im, out_re} = fifo[rd_ptr[FA-1:0]];
reg        push = 1'b0;
reg [33:0] push_word = 0;

always @(posedge clk) begin
    if (rst) begin
        rd_ptr <= 0;
        wr_ptr <= 0;
        overflows <= 0;
    end else begin
        if (out_valid && out_ready)
            rd_ptr <= rd_ptr + 1'b1;
        if (push) begin
            if (fifo_full) begin
                overflows <= overflows + 1'b1;
            end else begin
                fifo[wr_ptr[FA-1:0]] <= push_word;
                wr_ptr <= wr_ptr + 1'b1;
            end
        end
    end
end

always @(posedge clk) begin
    push <= 1'b0;
    if (rst) begin
        m_re <= 0; m_im <= 0; P_re <= 0; P_im <= 0; E <= 0; a32 <= 0; a64 <= 0; n <= 0;
        in_run <= 1'b0; active <= 1'b0; frames_found <= 0; frames_missed <= 0;
        for (i = 0; i < H; i = i + 1) begin
            xr_ring[i] <= 0; xi_ring[i] <= 0; pr_ring[i] <= 0; pi_ring[i] <= 0;
        end
        for (i = 0; i < N; i = i + 1) e_ring[i] <= 0;
    end else if (in_valid) begin
        // DC tracker
        m_re <= m_re + (y_re >>> 8);
        m_im <= m_im + (y_im >>> 8);
        // rings and running sums
        xr_ring[a32] <= x_re;  xi_ring[a32] <= x_im;
        pr_ring[a32] <= p_re;  pi_ring[a32] <= p_im;
        e_ring[a64]  <= e_n;
        P_re <= P_re_n; P_im <= P_im_n; E <= E_n;
        a32 <= a32 + 1'b1;
        a64 <= a64 + 1'b1;
        // plateau of the metric
        if (above) begin
            if (!in_run) begin
                in_run <= 1'b1;
                run_start <= d;
            end
            run_last <= d;
        end else if (in_run) begin
            in_run <= 1'b0;
            if (run_last - run_start + 1 >= MIN_RUN) begin
                if (active) begin
                    frames_missed <= frames_missed + 1'b1;
                end else begin
                    active <= 1'b1;
                    first <= run_c + CP / 2 + N - BACKOFF;
                    count <= 0;
                    total <= frame_symbols * 80;
                    pos <= 0;
                    frames_found <= frames_found + 1'b1;
                end
            end
        end
        // delayed output: sample k, read before this sample overwrites its slot
        dl_re[n[DA-1:0]] <= in_re;
        dl_im[n[DA-1:0]] <= in_im;
        if (active && n >= DELAY && k >= first) begin
            push <= 1'b1;
            push_word <= {(count == 0), (pos == 7'd79), dl_im[n[DA-1:0]], dl_re[n[DA-1:0]]};
            pos <= (pos == 7'd79) ? 7'd0 : pos + 1'b1;
            count <= count + 1'b1;
            if (count + 1'b1 == total)
                active <= 1'b0;
        end
        n <= n + 1'b1;
    end
end

endmodule
