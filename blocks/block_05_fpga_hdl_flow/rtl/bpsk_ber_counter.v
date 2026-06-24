// Lab 5.10 - deterministic BER counter against the shared Block 11 frame bits
//
// Reuses the same ROM image as the bit source and counts total/payload errors.

`timescale 1ns/1ps

module bpsk_ber_counter #(
    parameter integer INDEX_W = 16,
    parameter integer MAX_FRAME_BITS = 512,
    parameter integer LOCK_PREAMBLE_BITS = 4,
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
    output reg [INDEX_W-1:0]        received_bits,
    output reg [INDEX_W-1:0]        total_errors,
    output reg [INDEX_W-1:0]        payload_errors
);

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
integer idx;

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
        frame_limit_reg <= {INDEX_W{1'b0}};
        preamble_limit_reg <= {INDEX_W{1'b0}};
        lock_preamble_limit_reg <= {INDEX_W{1'b0}};
        acq_index <= {INDEX_W{1'b0}};
        acquisition_enabled_reg <= 1'b0;
        locked <= 1'b0;
        invert_bits <= 1'b0;
        acq_invert_bits <= 1'b0;
    end else begin
        done <= 1'b0;
        compare_bit = in_bit;
        expected_preamble_bit = frame_bits[0];
        start_invert = in_bit ^ frame_bits[0];
        next_preamble_limit = preamble_count;

        if (start && !busy && (frame_bit_count != 0)) begin
            if (preamble_count > frame_bit_count) begin
                next_preamble_limit = frame_bit_count;
            end
            busy <= 1'b1;
            received_bits <= {INDEX_W{1'b0}};
            total_errors <= {INDEX_W{1'b0}};
            payload_errors <= {INDEX_W{1'b0}};
            frame_limit_reg <= frame_bit_count;
            preamble_limit_reg <= next_preamble_limit;
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
        end else if (busy && in_valid) begin
            if (!locked && acquisition_enabled_reg) begin
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
        end
    end
end

endmodule
