// Lab 5.10b - deterministic QPSK BER counter WITH quadrant-resolving frame-sync.
//
// QPSK is two independent BPSK axes: dibit[0] rides the I axis (frame bit 2s),
// dibit[1] the Q axis (frame bit 2s+1). Flattening each recovered dibit into the
// bit pair {dibit[0], dibit[1]} reproduces the frame ROM bit order, so we feed it
// straight into the proven `bpsk_ber_counter`, which brings a sliding preamble
// correlator (frame-sync, offset/loopback-latency independent) and 180-degree
// (invert) ambiguity handling.
//
// QUADRANT AMBIGUITY. A Costas loop has FOUR stable lock points, so after carrier
// recovery the constellation is axis-aligned but rotated by an arbitrary k*90
// degrees set by the (per-burst jittery) path phase. The 180-degree case is already
// handled inside bpsk_ber_counter by its invert detection; the 90/270-degree cases
// swap I and Q and are NOT — the preamble mismatches ~half its bits and the frame
// never locks. On real self-OTA hardware that is exactly half the bursts (measured:
// 25/40 lock, 15/40 no-lock, a coin toss on the path phase).
//
// FIX: run TWO frame-sync branches in parallel and let the one that acquires win.
//   branch A: the dibit stream as received                -> covers   0 / 180 deg
//   branch B: the dibit stream de-rotated by 90 degrees   -> covers  90 / 270 deg
// De-rotating a symbol by -90 degrees maps (I,Q) -> (Q,-I), so on the hard-decision
// bits (bit = "axis is negative") it is bit_i' = bit_q, bit_q' = ~bit_i. Each branch
// still resolves its own 180 partner via invert detection, so two branches cover all
// four rotations. This is the classic "correlate the unique word against all four
// rotations and keep the best" — collapsed to two correlators by reusing the existing
// 180-degree resolve. The loser is aborted so only one branch drives the outputs.
//
// A wrong-quadrant branch mismatches ~12 of the 24 preamble bits, far outside
// LOCK_ERR_TOL, so exactly one branch ever acquires; ties (impossible in practice)
// resolve to A.
//
// Interface matches the original fixed-alignment counter plus a preamble length,
// with received_symbols/total_bit_errors derived from the underlying bit counts.

`timescale 1ns/1ps

module qpsk_ber_counter #(
    parameter integer INDEX_W = 16,
    parameter integer MAX_FRAME_BITS = 512,
    parameter integer LOCK_PREAMBLE_BITS = 8,
    parameter integer LOCK_ERR_TOL = 0,   // >0 = OTA-robust sliding-correlation lock
    parameter MEM_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem"
) (
    input  wire                     clk,
    input  wire                     rst,
    input  wire                     start,
    input  wire                     abort,
    input  wire [INDEX_W-1:0]       symbol_count,     // QPSK symbols
    input  wire [INDEX_W-1:0]       preamble_count,   // preamble length in BITS
    input  wire                     in_valid,
    input  wire [1:0]               in_dibit,
    output wire                     busy,
    output wire                     done,
    output wire                     quadrant_swapped, // 1 = branch B won (90/270 deg)
    output reg  [INDEX_W-1:0]       received_symbols,
    output reg  [INDEX_W-1:0]       total_bit_errors,
    output reg  [INDEX_W-1:0]       payload_bit_errors,
    output reg  [31:0]              payload_error_segments,
    output reg  [INDEX_W-1:0]       first_payload_error_index,
    output reg  [INDEX_W-1:0]       last_payload_error_index
);

localparam [1:0] S_IDLE  = 2'd0;
localparam [1:0] S_EMIT1 = 2'd1;

// dibit -> serial bit flattener, emitted twice: once as received (branch A) and once
// de-rotated by 90 degrees (branch B). Branch A emits {dibit[0], dibit[1]} so the
// stream matches the frame ROM (bit 2s = I = dibit[0], bit 2s+1 = Q = dibit[1]);
// branch B emits {dibit[1], ~dibit[0]}. Recovered symbols are >= SPS cycles apart,
// so the 2-cycle emit never overruns.
reg [1:0] flat_state = S_IDLE;
reg [1:0] dibit_lat = 2'd0;
reg       bit_valid = 1'b0;
reg       bit_a = 1'b0;
reg       bit_b = 1'b0;

always @(posedge clk) begin
    if (rst || start) begin
        flat_state <= S_IDLE;
        bit_valid  <= 1'b0;
        bit_a      <= 1'b0;
        bit_b      <= 1'b0;
    end else begin
        bit_valid <= 1'b0;
        case (flat_state)
            S_IDLE: begin
                if (in_valid) begin
                    dibit_lat  <= in_dibit;
                    bit_a      <= in_dibit[0];
                    bit_b      <= in_dibit[1];
                    bit_valid  <= 1'b1;
                    flat_state <= S_EMIT1;
                end
            end
            S_EMIT1: begin
                bit_a      <= dibit_lat[1];
                bit_b      <= ~dibit_lat[0];
                bit_valid  <= 1'b1;
                flat_state <= S_IDLE;
            end
            default: flat_state <= S_IDLE;
        endcase
    end
end

wire [INDEX_W-1:0] frame_bit_count = symbol_count << 1;   // 2 bits per QPSK symbol

// --- winner arbitration -----------------------------------------------------
// The first branch to acquire the preamble owns the burst; the loser is aborted so
// it stops counting and releases `busy`. Cleared on rst/start.
wire lock_a, lock_b;
reg  winner_valid = 1'b0;
reg  winner_b     = 1'b0;   // 0 = branch A, 1 = branch B

always @(posedge clk) begin
    if (rst || start) begin
        winner_valid <= 1'b0;
        winner_b     <= 1'b0;
    end else if (!winner_valid) begin
        if (lock_a) begin
            winner_valid <= 1'b1;
            winner_b     <= 1'b0;
        end else if (lock_b) begin
            winner_valid <= 1'b1;
            winner_b     <= 1'b1;
        end
    end
end

wire abort_a = abort || (winner_valid &&  winner_b);
wire abort_b = abort || (winner_valid && !winner_b);

wire busy_a, busy_b, done_a, done_b;
wire [INDEX_W-1:0] recv_a, recv_b, err_a, err_b, payload_err_a, payload_err_b;
wire [31:0] payload_segments_a, payload_segments_b;
wire [INDEX_W-1:0] first_payload_error_a, first_payload_error_b;
wire [INDEX_W-1:0] last_payload_error_a, last_payload_error_b;

bpsk_ber_counter #(
    .INDEX_W(INDEX_W),
    .MAX_FRAME_BITS(MAX_FRAME_BITS),
    .LOCK_PREAMBLE_BITS(LOCK_PREAMBLE_BITS),
    .LOCK_ERR_TOL(LOCK_ERR_TOL),
    .MEM_FILE(MEM_FILE)
) bit_ber_a (
    .clk(clk),
    .rst(rst),
    .start(start),
    .abort(abort_a),
    .frame_bit_count(frame_bit_count),
    .preamble_count(preamble_count),
    .in_valid(bit_valid),
    .in_bit(bit_a),
    .busy(busy_a),
    .done(done_a),
    .lock_acquired(lock_a),
    .received_bits(recv_a),
    .total_errors(err_a),
    .payload_errors(payload_err_a),
    .payload_error_segments(payload_segments_a),
    .first_payload_error_index(first_payload_error_a),
    .last_payload_error_index(last_payload_error_a)
);

bpsk_ber_counter #(
    .INDEX_W(INDEX_W),
    .MAX_FRAME_BITS(MAX_FRAME_BITS),
    .LOCK_PREAMBLE_BITS(LOCK_PREAMBLE_BITS),
    .LOCK_ERR_TOL(LOCK_ERR_TOL),
    .MEM_FILE(MEM_FILE)
) bit_ber_b (
    .clk(clk),
    .rst(rst),
    .start(start),
    .abort(abort_b),
    .frame_bit_count(frame_bit_count),
    .preamble_count(preamble_count),
    .in_valid(bit_valid),
    .in_bit(bit_b),
    .busy(busy_b),
    .done(done_b),
    .lock_acquired(lock_b),
    .received_bits(recv_b),
    .total_errors(err_b),
    .payload_errors(payload_err_b),
    .payload_error_segments(payload_segments_b),
    .first_payload_error_index(first_payload_error_b),
    .last_payload_error_index(last_payload_error_b)
);

// Before a winner exists neither branch can be `done` on its own, so the only way
// both assert together is the external abort — forward that. Afterwards only the
// winner's done/busy are visible (the loser's abort-done pulse is ignored).
assign busy = winner_valid ? (winner_b ? busy_b : busy_a) : (busy_a || busy_b);
assign done = winner_valid ? (winner_b ? done_b : done_a) : (done_a && done_b);
assign quadrant_swapped = winner_valid && winner_b;

always @(*) begin
    received_symbols = (winner_b ? recv_b : recv_a) >> 1;   // 2 bits/symbol
    total_bit_errors = (winner_b ? err_b : err_a);
    payload_bit_errors = (winner_b ? payload_err_b : payload_err_a);
    payload_error_segments = (winner_b ? payload_segments_b : payload_segments_a);
    first_payload_error_index = (winner_b ? first_payload_error_b : first_payload_error_a);
    last_payload_error_index = (winner_b ? last_payload_error_b : last_payload_error_a);
end

endmodule
