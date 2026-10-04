// Lab 5.7b - BPSK 8x upsampler + RRC TX FIR as one polyphase filter
//
// Drop-in replacement for the pair
//     bpsk_upsampler_8x -> bpsk_rrc_tx_fir
// with the same ports as that pair (symbol-rate input with in_ready, sample-rate
// output) and the same output samples on the same clocks.
//
// Why it is cheaper: after the 8x upsampler seven of every eight FIR inputs are
// zero, so for output phase p (0..SPS-1) only the taps p, p+SPS, p+2*SPS, ...
// meet a non-zero sample:
//     y[SPS*n + p] = sum_m h[p + SPS*m] * s[n - m],   m = 0 .. ceil(NTAPS/SPS)-1
// One output per clock therefore needs ceil(65/8) = 9 multipliers per channel
// whose coefficients change with p, instead of the 33 (pre-added symmetric)
// fixed-coefficient multipliers of bpsk_rrc_tx_fir.
//
// Bit-exactness: the products are the same integers the direct filter adds
// (its zero inputs contribute nothing), the sum is exact in ACC_W bits, and
// rounding/saturation are the same functions. bpsk_rrc_tx_fir reads the pair
// coefficients from the first half of the tap table (it assumes symmetry), so
// tap j here uses h[min(j, NTAPS-1-j)] as well.
//
// Timing: an internal phase counter reproduces the upsampler's output
// handshake (in_ready = not busy, SPS events per symbol); the products, a
// registered adder tree and the round/saturate register follow, and a short
// delay line pads the latency to the direct filter's 9 clocks.

`timescale 1ns/1ps

module bpsk_rrc_tx_polyphase #(
    parameter integer W = 16,
    parameter integer CW = 16,
    parameter integer NTAPS = 65,
    parameter integer SPS = 8,
    parameter integer PHASE_W = 3,
    parameter integer ACC_W = 40,
    parameter integer SHIFT = 15,
    parameter COEF_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_rrc_tx_fir_taps.mem"
) (
    input  wire                 clk,
    input  wire                 rst,
    input  wire                 in_valid,
    input  wire signed [W-1:0]  in_i,
    input  wire signed [W-1:0]  in_q,
    output wire                 in_ready,
    output reg                  out_valid,
    output reg  signed [W-1:0]  out_i,
    output reg  signed [W-1:0]  out_q
);

localparam integer M = (NTAPS + SPS - 1) / SPS;          // taps per phase (9)
localparam integer S1 = (M + 1) / 2;                     // adder tree: 9 -> 5
localparam integer S2 = (S1 + 1) / 2;                    //            5 -> 3
localparam integer S3 = (S2 + 1) / 2;                    //            3 -> 2
localparam integer S4 = (S3 + 1) / 2;                    //            2 -> 1
localparam integer PAD = 2;                              // events -> products -> 4 sums -> round -> 2 pad -> out = 9 clocks
localparam signed [ACC_W-1:0] ROUND_BIAS = {{(ACC_W-1){1'b0}}, 1'b1} <<< (SHIFT - 1);

generate
    if (S4 != 1) begin : g_tree_too_small
        initial begin
            $display("ERROR: bpsk_rrc_tx_polyphase supports up to 16 taps per phase (NTAPS=%0d SPS=%0d)", NTAPS, SPS);
            $finish;
        end
    end
endgenerate

reg signed [CW-1:0] coeff_mem [0:NTAPS-1];

// Symbol history: hist[0] is the newest symbol.
reg signed [W-1:0] hist_i [0:M-1];
reg signed [W-1:0] hist_q [0:M-1];

// Event generator: same handshake and timing as bpsk_upsampler_8x.
reg active;
reg [PHASE_W-1:0] phase;
reg ev_valid;
reg [PHASE_W-1:0] ev_phase;

reg signed [ACC_W-1:0] prod_i [0:M-1];
reg signed [ACC_W-1:0] prod_q [0:M-1];
reg signed [ACC_W-1:0] sum1_i [0:S1-1];
reg signed [ACC_W-1:0] sum1_q [0:S1-1];
reg signed [ACC_W-1:0] sum2_i [0:S2-1];
reg signed [ACC_W-1:0] sum2_q [0:S2-1];
reg signed [ACC_W-1:0] sum3_i [0:S3-1];
reg signed [ACC_W-1:0] sum3_q [0:S3-1];
reg signed [ACC_W-1:0] sum4_i;
reg signed [ACC_W-1:0] sum4_q;
reg [5:0] valid_pipe;                // prod, sum1..sum4, rounded
reg signed [W-1:0] rounded_i;
reg signed [W-1:0] rounded_q;
reg [PAD-1:0] pad_valid;
reg signed [W-1:0] pad_i [0:PAD-1];
reg signed [W-1:0] pad_q [0:PAD-1];

integer k;

function signed [ACC_W-1:0] round_q15;
    input signed [ACC_W-1:0] value;
    begin
        round_q15 = (value + ROUND_BIAS) >>> SHIFT;
    end
endfunction

function signed [W-1:0] sat_q15;
    input signed [ACC_W-1:0] value;
    begin
        if (value > 32767)
            sat_q15 = 16'sd32767;
        else if (value < -32768)
            sat_q15 = -16'sd32768;
        else
            sat_q15 = value[W-1:0];
    end
endfunction

// Coefficient of tap j as the direct filter uses it (first half of the table).
function signed [CW-1:0] tap_coeff;
    input integer j;
    begin
        if (j >= NTAPS)
            tap_coeff = {CW{1'b0}};
        else if (j <= (NTAPS - 1) / 2)
            tap_coeff = coeff_mem[j];
        else
            tap_coeff = coeff_mem[NTAPS - 1 - j];
    end
endfunction

initial begin
    for (k = 0; k < NTAPS; k = k + 1)
        coeff_mem[k] = {CW{1'b0}};
    $readmemh(COEF_FILE, coeff_mem);
end

assign in_ready = ~active;

always @(posedge clk) begin
    if (rst) begin
        active <= 1'b0;
        phase <= {PHASE_W{1'b0}};
        ev_valid <= 1'b0;
        ev_phase <= {PHASE_W{1'b0}};
        for (k = 0; k < M; k = k + 1) begin
            hist_i[k] <= {W{1'b0}};
            hist_q[k] <= {W{1'b0}};
            prod_i[k] <= {ACC_W{1'b0}};
            prod_q[k] <= {ACC_W{1'b0}};
        end
        valid_pipe <= 6'd0;
        pad_valid <= {PAD{1'b0}};
        out_valid <= 1'b0;
        out_i <= {W{1'b0}};
        out_q <= {W{1'b0}};
    end else begin
        // Event generator (one output sample per event).
        ev_valid <= 1'b0;
        if (!active) begin
            if (in_valid) begin
                for (k = M - 1; k > 0; k = k - 1) begin
                    hist_i[k] <= hist_i[k-1];
                    hist_q[k] <= hist_q[k-1];
                end
                hist_i[0] <= in_i;
                hist_q[0] <= in_q;
                ev_valid <= 1'b1;
                ev_phase <= {PHASE_W{1'b0}};
                if (SPS > 1) begin
                    active <= 1'b1;
                    phase <= {{(PHASE_W-1){1'b0}}, 1'b1};
                end
            end
        end else begin
            ev_valid <= 1'b1;
            ev_phase <= phase;
            if (phase == SPS - 1) begin
                active <= 1'b0;
                phase <= {PHASE_W{1'b0}};
            end else begin
                phase <= phase + 1'b1;
            end
        end

        // Products: tap ev_phase + SPS*m meets symbol n - m.
        valid_pipe[0] <= ev_valid;
        if (ev_valid) begin
            for (k = 0; k < M; k = k + 1) begin
                prod_i[k] <= $signed(hist_i[k]) * $signed(tap_coeff(ev_phase + SPS * k));
                prod_q[k] <= $signed(hist_q[k]) * $signed(tap_coeff(ev_phase + SPS * k));
            end
        end

        // Registered adder tree.
        valid_pipe[1] <= valid_pipe[0];
        if (valid_pipe[0])
            for (k = 0; k < S1; k = k + 1) begin
                sum1_i[k] <= prod_i[2*k] + ((2*k + 1 < M) ? prod_i[2*k + 1] : {ACC_W{1'b0}});
                sum1_q[k] <= prod_q[2*k] + ((2*k + 1 < M) ? prod_q[2*k + 1] : {ACC_W{1'b0}});
            end
        valid_pipe[2] <= valid_pipe[1];
        if (valid_pipe[1])
            for (k = 0; k < S2; k = k + 1) begin
                sum2_i[k] <= sum1_i[2*k] + ((2*k + 1 < S1) ? sum1_i[2*k + 1] : {ACC_W{1'b0}});
                sum2_q[k] <= sum1_q[2*k] + ((2*k + 1 < S1) ? sum1_q[2*k + 1] : {ACC_W{1'b0}});
            end
        valid_pipe[3] <= valid_pipe[2];
        if (valid_pipe[2])
            for (k = 0; k < S3; k = k + 1) begin
                sum3_i[k] <= sum2_i[2*k] + ((2*k + 1 < S2) ? sum2_i[2*k + 1] : {ACC_W{1'b0}});
                sum3_q[k] <= sum2_q[2*k] + ((2*k + 1 < S2) ? sum2_q[2*k + 1] : {ACC_W{1'b0}});
            end
        valid_pipe[4] <= valid_pipe[3];
        if (valid_pipe[3]) begin
            sum4_i <= sum3_i[0] + ((S3 > 1) ? sum3_i[1] : {ACC_W{1'b0}});
            sum4_q <= sum3_q[0] + ((S3 > 1) ? sum3_q[1] : {ACC_W{1'b0}});
        end

        // Round and saturate exactly like bpsk_rrc_tx_fir.
        valid_pipe[5] <= valid_pipe[4];
        if (valid_pipe[4]) begin
            rounded_i <= sat_q15(round_q15(sum4_i));
            rounded_q <= sat_q15(round_q15(sum4_q));
        end

        // Pad to the direct filter's latency.
        pad_valid[0] <= valid_pipe[5];
        pad_i[0] <= valid_pipe[5] ? rounded_i : {W{1'b0}};
        pad_q[0] <= valid_pipe[5] ? rounded_q : {W{1'b0}};
        for (k = 1; k < PAD; k = k + 1) begin
            pad_valid[k] <= pad_valid[k-1];
            pad_i[k] <= pad_i[k-1];
            pad_q[k] <= pad_q[k-1];
        end
        out_valid <= pad_valid[PAD-1];
        out_i <= pad_valid[PAD-1] ? pad_i[PAD-1] : out_i;
        out_q <= pad_valid[PAD-1] ? pad_q[PAD-1] : out_q;
    end
end

endmodule
