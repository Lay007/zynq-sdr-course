// Lab 5.10 - deterministic BER counter against the shared Block 11 frame bits
//
// Reuses the same ROM image as the bit source and counts total/payload errors.

`timescale 1ns/1ps

module bpsk_ber_counter #(
    parameter integer INDEX_W = 16,
    parameter integer MAX_FRAME_BITS = 512,
    // Frame-sync acquisition window. The preamble begins with five identical bits
    // (0,0,0,0,0,1,1,...), so a 4-bit lock pattern (frame_bits[0..3] = 0,0,0,0) is
    // AMBIGUOUS: it matches one or two samples early on the leading zeros (or on a
    // pre-frame transient bit), which shifts the whole payload comparison and floors
    // the BER near 50% even on a clean signal. An 8-bit window (0,0,0,0,0,1,1,0)
    // spans past the leading zeros to the distinctive 1,1, so the sliding correlator
    // locks at exactly one alignment = the true frame start, independent of the
    // pre-frame transient / loopback-latency jitter (and overrides start_offset).
    parameter integer LOCK_PREAMBLE_BITS = 8,
    // OTA robustness: LOCK_ERR_TOL = 0 keeps the exact sequential match (bit-identical
    // to the original clean-loopback behaviour, zero regression). LOCK_ERR_TOL > 0
    // switches to a sliding LOCK_PREAMBLE_BITS-wide correlation lock that fires at the
    // first window whose match count >= LOCK_PREAMBLE_BITS - LOCK_ERR_TOL, tolerating a
    // few over-the-air preamble bit errors instead of resetting and false-locking on
    // the leading-zeros run (which floored real self-OTA captures at ~44%). Use a wide
    // window (e.g. 24) + small tolerance (e.g. 3) for OTA; noise never reaches the
    // threshold, so it does not false-trigger.
    parameter integer LOCK_ERR_TOL = 0,
    parameter MEM_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem"
) (
    input  wire                     clk,
    input  wire                     rst,
    input  wire                     start,
    input  wire                     abort,
    input  wire [INDEX_W-1:0]       frame_bit_count,
    input  wire [INDEX_W-1:0]       preamble_count,
    input  wire                     in_valid,
    input  wire                     in_bit,
    output reg                      busy,
    output reg                      done,
    // High from preamble lock until the frame completes. Lets a parent run several
    // of these in parallel on differently-rotated bit streams and pick the branch
    // that actually acquired the frame (see qpsk_ber_counter's quadrant resolve).
    output wire                     lock_acquired,
    output reg [INDEX_W-1:0]        received_bits,
    output reg [INDEX_W-1:0]        total_errors,
    output reg [INDEX_W-1:0]        payload_errors,
    // Payload-relative localization. Four byte counters cover consecutive
    // quarters of the configured payload; 0xffff means that no payload error
    // has been observed. These diagnostics do not participate in BER control.
    output reg [31:0]               payload_error_segments,
    output reg [INDEX_W-1:0]        first_payload_error_index,
    output reg [INDEX_W-1:0]        last_payload_error_index
);

localparam integer WIN = (LOCK_PREAMBLE_BITS < 1) ? 1 : LOCK_PREAMBLE_BITS;

reg [0:0] frame_bits [0:MAX_FRAME_BITS-1];
reg [INDEX_W-1:0] frame_limit_reg = {INDEX_W{1'b0}};
reg [INDEX_W-1:0] preamble_limit_reg = {INDEX_W{1'b0}};
reg [INDEX_W-1:0] lock_preamble_limit_reg = {INDEX_W{1'b0}};
reg [INDEX_W-1:0] acq_index = {INDEX_W{1'b0}};
reg acquisition_enabled_reg = 1'b0;
reg locked = 1'b0;
reg invert_bits = 1'b0;
reg compare_bit = 1'b0;
reg acq_invert_bits = 1'b0;
reg expected_preamble_bit = 1'b0;
reg start_invert = 1'b0;
reg [INDEX_W-1:0] next_preamble_limit = {INDEX_W{1'b0}};
reg [INDEX_W-1:0] next_payload_length = {INDEX_W{1'b0}};
reg [INDEX_W-1:0] payload_quarter1_reg = {INDEX_W{1'b0}};
reg [INDEX_W-1:0] payload_quarter2_reg = {INDEX_W{1'b0}};
reg [INDEX_W-1:0] payload_quarter3_reg = {INDEX_W{1'b0}};
reg [INDEX_W-1:0] payload_index = {INDEX_W{1'b0}};
integer idx;

// --- sliding-window correlation lock state (used only when LOCK_ERR_TOL > 0) ---
reg [WIN-1:0] win_sr = {WIN{1'b0}};
reg [INDEX_W-1:0] win_fill = {INDEX_W{1'b0}};

// Count matches of a WIN-bit window against the first WIN frame bits (oldest window
// bit w[WIN-1] aligns with frame_bits[0]); inv selects the 180-degree polarity.
function [INDEX_W-1:0] count_matches(input [WIN-1:0] w, input inv);
    integer j;
    reg exp_bit;
    begin
        count_matches = {INDEX_W{1'b0}};
        for (j = 0; j < WIN; j = j + 1) begin
            exp_bit = inv ? ~frame_bits[WIN-1-j][0] : frame_bits[WIN-1-j][0];
            if (w[j] == exp_bit) count_matches = count_matches + 1'b1;
        end
    end
endfunction

assign lock_acquired = locked;

wire [WIN-1:0] next_win = {win_sr[WIN-2:0], in_bit};
wire [INDEX_W-1:0] m_noninv = count_matches(next_win, 1'b0);
wire [INDEX_W-1:0] m_inv    = count_matches(next_win, 1'b1);
wire [INDEX_W-1:0] lock_thresh = WIN[INDEX_W-1:0] - LOCK_ERR_TOL[INDEX_W-1:0];
wire corr_full = (win_fill >= (WIN[INDEX_W-1:0] - 1'b1));   // this bit fills the window
wire corr_hit_noninv = corr_full && (m_noninv >= lock_thresh);
wire corr_hit_inv    = corr_full && (m_inv    >= lock_thresh) && (m_inv > m_noninv);
wire corr_hit = corr_hit_noninv || corr_hit_inv;
wire corr_inv_sel = corr_hit_inv;
wire [INDEX_W-1:0] corr_matches = corr_hit_inv ? m_inv : m_noninv;
wire [INDEX_W-1:0] corr_pre_err = WIN[INDEX_W-1:0] - corr_matches;

initial begin
    for (idx = 0; idx < MAX_FRAME_BITS; idx = idx + 1) begin
        frame_bits[idx] = 1'b0;
    end
    $readmemh(MEM_FILE, frame_bits);
end

always @(posedge clk) begin
    if (rst) begin
        busy <= 1'b0;
        done <= 1'b0;
        received_bits <= {INDEX_W{1'b0}};
        total_errors <= {INDEX_W{1'b0}};
        payload_errors <= {INDEX_W{1'b0}};
        payload_error_segments <= 32'd0;
        first_payload_error_index <= {INDEX_W{1'b1}};
        last_payload_error_index <= {INDEX_W{1'b1}};
        frame_limit_reg <= {INDEX_W{1'b0}};
        preamble_limit_reg <= {INDEX_W{1'b0}};
        payload_quarter1_reg <= {INDEX_W{1'b0}};
        payload_quarter2_reg <= {INDEX_W{1'b0}};
        payload_quarter3_reg <= {INDEX_W{1'b0}};
        lock_preamble_limit_reg <= {INDEX_W{1'b0}};
        acq_index <= {INDEX_W{1'b0}};
        acquisition_enabled_reg <= 1'b0;
        locked <= 1'b0;
        invert_bits <= 1'b0;
        acq_invert_bits <= 1'b0;
        win_sr <= {WIN{1'b0}};
        win_fill <= {INDEX_W{1'b0}};
    end else begin
        done <= 1'b0;
        compare_bit = in_bit;
        expected_preamble_bit = frame_bits[0];
        start_invert = in_bit ^ frame_bits[0];
        next_preamble_limit = preamble_count;
        next_payload_length = {INDEX_W{1'b0}};
        payload_index = {INDEX_W{1'b0}};

        if (start && !busy && (frame_bit_count != 0)) begin
            if (preamble_count > frame_bit_count) begin
                next_preamble_limit = frame_bit_count;
            end
            next_payload_length = frame_bit_count - next_preamble_limit;
            busy <= 1'b1;
            received_bits <= {INDEX_W{1'b0}};
            total_errors <= {INDEX_W{1'b0}};
            payload_errors <= {INDEX_W{1'b0}};
            payload_error_segments <= 32'd0;
            first_payload_error_index <= {INDEX_W{1'b1}};
            last_payload_error_index <= {INDEX_W{1'b1}};
            frame_limit_reg <= frame_bit_count;
            preamble_limit_reg <= next_preamble_limit;
            payload_quarter1_reg <= next_payload_length >> 2;
            payload_quarter2_reg <= next_payload_length >> 1;
            payload_quarter3_reg <= (next_payload_length >> 1) + (next_payload_length >> 2);
            if (next_preamble_limit > LOCK_PREAMBLE_BITS) begin
                lock_preamble_limit_reg <= LOCK_PREAMBLE_BITS;
            end else begin
                lock_preamble_limit_reg <= next_preamble_limit;
            end
            acq_index <= {INDEX_W{1'b0}};
            acquisition_enabled_reg <= (next_preamble_limit != 0);
            locked <= (next_preamble_limit == 0);
            invert_bits <= 1'b0;
            acq_invert_bits <= 1'b0;
            win_sr <= {WIN{1'b0}};
            win_fill <= {INDEX_W{1'b0}};
        end else if (busy && abort) begin
            busy <= 1'b0;
            done <= 1'b1;
            frame_limit_reg <= {INDEX_W{1'b0}};
            preamble_limit_reg <= {INDEX_W{1'b0}};
            lock_preamble_limit_reg <= {INDEX_W{1'b0}};
            acq_index <= {INDEX_W{1'b0}};
            acquisition_enabled_reg <= 1'b0;
            locked <= 1'b0;
            invert_bits <= 1'b0;
            acq_invert_bits <= 1'b0;
            win_sr <= {WIN{1'b0}};
            win_fill <= {INDEX_W{1'b0}};
        end else if (busy && in_valid) begin
            if (!locked && acquisition_enabled_reg && (LOCK_ERR_TOL > 0)) begin
                // ---- sliding-window correlation lock (OTA-robust) ----
                win_sr <= next_win;
                if (win_fill < WIN[INDEX_W-1:0]) win_fill <= win_fill + 1'b1;
                if (corr_hit) begin
                    locked <= 1'b1;
                    invert_bits <= corr_inv_sel;
                    received_bits <= WIN[INDEX_W-1:0];
                    total_errors <= corr_pre_err;
                    payload_errors <= {INDEX_W{1'b0}};  // WIN preamble bits are pre-payload
                    acq_index <= {INDEX_W{1'b0}};
                    acq_invert_bits <= 1'b0;
                    if (WIN[INDEX_W-1:0] >= frame_limit_reg) begin
                        received_bits <= frame_limit_reg;
                        busy <= 1'b0;
                        done <= 1'b1;
                        frame_limit_reg <= {INDEX_W{1'b0}};
                        preamble_limit_reg <= {INDEX_W{1'b0}};
                        lock_preamble_limit_reg <= {INDEX_W{1'b0}};
                        acquisition_enabled_reg <= 1'b0;
                        locked <= 1'b0;
                        invert_bits <= 1'b0;
                    end
                end
            end else if (!locked && acquisition_enabled_reg) begin
                // ---- original exact sequential match (LOCK_ERR_TOL == 0) ----
                if (acq_index == {INDEX_W{1'b0}}) begin
                    if (lock_preamble_limit_reg == {{(INDEX_W-1){1'b0}}, 1'b1}) begin
                        locked <= 1'b1;
                        invert_bits <= start_invert;
                        received_bits <= lock_preamble_limit_reg;
                        total_errors <= {INDEX_W{1'b0}};
                        payload_errors <= {INDEX_W{1'b0}};
                        acq_index <= {INDEX_W{1'b0}};
                        acq_invert_bits <= 1'b0;
                        if (lock_preamble_limit_reg == frame_limit_reg) begin
                            busy <= 1'b0;
                            done <= 1'b1;
                            frame_limit_reg <= {INDEX_W{1'b0}};
                            preamble_limit_reg <= {INDEX_W{1'b0}};
                            lock_preamble_limit_reg <= {INDEX_W{1'b0}};
                            acquisition_enabled_reg <= 1'b0;
                            locked <= 1'b0;
                            invert_bits <= 1'b0;
                        end
                    end else begin
                        acq_index <= {{(INDEX_W-1){1'b0}}, 1'b1};
                        acq_invert_bits <= start_invert;
                    end
                end else begin
                    expected_preamble_bit = acq_invert_bits ? ~frame_bits[acq_index] : frame_bits[acq_index];
                    if (in_bit === expected_preamble_bit) begin
                        if ((acq_index + 1'b1) == lock_preamble_limit_reg) begin
                            locked <= 1'b1;
                            invert_bits <= acq_invert_bits;
                            received_bits <= lock_preamble_limit_reg;
                            total_errors <= {INDEX_W{1'b0}};
                            payload_errors <= {INDEX_W{1'b0}};
                            acq_index <= {INDEX_W{1'b0}};
                            acq_invert_bits <= 1'b0;
                            if (lock_preamble_limit_reg == frame_limit_reg) begin
                                busy <= 1'b0;
                                done <= 1'b1;
                                frame_limit_reg <= {INDEX_W{1'b0}};
                                preamble_limit_reg <= {INDEX_W{1'b0}};
                                lock_preamble_limit_reg <= {INDEX_W{1'b0}};
                                acquisition_enabled_reg <= 1'b0;
                                locked <= 1'b0;
                                invert_bits <= 1'b0;
                            end
                        end else begin
                            acq_index <= acq_index + 1'b1;
                        end
                    end else if (lock_preamble_limit_reg == {{(INDEX_W-1){1'b0}}, 1'b1}) begin
                        locked <= 1'b1;
                        invert_bits <= start_invert;
                        received_bits <= lock_preamble_limit_reg;
                        total_errors <= {INDEX_W{1'b0}};
                        payload_errors <= {INDEX_W{1'b0}};
                        acq_index <= {INDEX_W{1'b0}};
                        acq_invert_bits <= 1'b0;
                        if (lock_preamble_limit_reg == frame_limit_reg) begin
                            busy <= 1'b0;
                            done <= 1'b1;
                            frame_limit_reg <= {INDEX_W{1'b0}};
                            preamble_limit_reg <= {INDEX_W{1'b0}};
                            lock_preamble_limit_reg <= {INDEX_W{1'b0}};
                            acquisition_enabled_reg <= 1'b0;
                            locked <= 1'b0;
                            invert_bits <= 1'b0;
                        end
                    end else begin
                        acq_index <= {{(INDEX_W-1){1'b0}}, 1'b1};
                        acq_invert_bits <= start_invert;
                    end
                end
            end else begin
                compare_bit = invert_bits ? ~in_bit : in_bit;
                if (compare_bit !== frame_bits[received_bits]) begin
                    total_errors <= total_errors + 1'b1;
                    if (received_bits >= preamble_limit_reg) begin
                        payload_errors <= payload_errors + 1'b1;
                        payload_index = received_bits - preamble_limit_reg;
                        if (payload_errors == {INDEX_W{1'b0}}) begin
                            first_payload_error_index <= payload_index;
                        end
                        last_payload_error_index <= payload_index;
                        if (payload_index < payload_quarter1_reg) begin
                            if (payload_error_segments[7:0] != 8'hff)
                                payload_error_segments[7:0] <= payload_error_segments[7:0] + 1'b1;
                        end else if (payload_index < payload_quarter2_reg) begin
                            if (payload_error_segments[15:8] != 8'hff)
                                payload_error_segments[15:8] <= payload_error_segments[15:8] + 1'b1;
                        end else if (payload_index < payload_quarter3_reg) begin
                            if (payload_error_segments[23:16] != 8'hff)
                                payload_error_segments[23:16] <= payload_error_segments[23:16] + 1'b1;
                        end else begin
                            if (payload_error_segments[31:24] != 8'hff)
                                payload_error_segments[31:24] <= payload_error_segments[31:24] + 1'b1;
                        end
                    end
                end

                if (received_bits == frame_limit_reg - 1'b1) begin
                    received_bits <= frame_limit_reg;
                    busy <= 1'b0;
                    done <= 1'b1;
                    frame_limit_reg <= {INDEX_W{1'b0}};
                    preamble_limit_reg <= {INDEX_W{1'b0}};
                    lock_preamble_limit_reg <= {INDEX_W{1'b0}};
                    acq_index <= {INDEX_W{1'b0}};
                    acquisition_enabled_reg <= 1'b0;
                    locked <= 1'b0;
                    invert_bits <= 1'b0;
                    acq_invert_bits <= 1'b0;
                end else begin
                    received_bits <= received_bits + 1'b1;
                end
            end
        end else if (!busy) begin
            frame_limit_reg <= {INDEX_W{1'b0}};
            preamble_limit_reg <= {INDEX_W{1'b0}};
            lock_preamble_limit_reg <= {INDEX_W{1'b0}};
            acq_index <= {INDEX_W{1'b0}};
            acquisition_enabled_reg <= 1'b0;
            locked <= 1'b0;
            invert_bits <= 1'b0;
            acq_invert_bits <= 1'b0;
            win_sr <= {WIN{1'b0}};
            win_fill <= {INDEX_W{1'b0}};
        end
    end
end

endmodule
