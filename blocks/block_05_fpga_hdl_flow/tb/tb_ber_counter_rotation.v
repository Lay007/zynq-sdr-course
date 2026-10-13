// Issue #64 - the BER counters must tell the PS which polarity / rotation they resolved.
//
// BPSK: the frame ROM bits are fed straight and inverted; the counter must lock both
// times with zero payload errors and report lock_inverted = 0 / 1.
// QPSK: the same ROM bits are paired into dibits (bit 2s on I, 2s+1 on Q) and rotated by
// k*90 degrees on the hard decisions (bit = 1 means a negative axis):
//   90: (I,Q) -> (-Q, I)   180: (I,Q) -> (-I,-Q)   270: (I,Q) -> (Q,-I)
// The counter must decode each with zero errors and report rotation_index = k, for the
// exact lock (LOCK_PREAMBLE_BITS 8, LOCK_ERR_TOL 0) and the OTA lock (24, 3).
`timescale 1ns/1ps
module tb_ber_counter_rotation;
    localparam integer INDEX_W = 16;
    localparam integer BPSK_BITS = 281;
    localparam integer BPSK_PREAMBLE = 25;
    localparam integer QPSK_SYMS = 140;
    localparam integer QPSK_PREAMBLE = 24;

    reg clk = 1'b0;
    reg rst = 1'b1;
    always #5 clk = ~clk;

    reg [0:0] rom [0:511];
    initial $readmemh("blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem", rom);

    integer errors = 0;
    integer n, k, cfg;

    // ---------------- BPSK ----------------
    reg b_start = 1'b0, b_valid = 1'b0, b_bit = 1'b0;
    wire b_busy, b_done, b_inv;
    wire [INDEX_W-1:0] b_recv, b_err, b_perr;
    bpsk_ber_counter #(.INDEX_W(INDEX_W), .MAX_FRAME_BITS(512)) bcnt (
        .clk(clk), .rst(rst), .start(b_start), .abort(1'b0),
        .frame_bit_count(BPSK_BITS[INDEX_W-1:0]), .preamble_count(BPSK_PREAMBLE[INDEX_W-1:0]),
        .in_valid(b_valid), .in_bit(b_bit),
        .busy(b_busy), .done(b_done), .lock_acquired(), .lock_inverted(b_inv),
        .payload_out_valid(), .payload_out_bit(),
        .received_bits(b_recv), .total_errors(b_err), .payload_errors(b_perr),
        .payload_error_segments(), .first_payload_error_index(), .last_payload_error_index());

    task run_bpsk(input invert);
        begin
            @(negedge clk); b_start = 1'b1; @(negedge clk); b_start = 1'b0;
            for (n = 0; n < BPSK_BITS; n = n + 1) begin
                b_bit = rom[n][0] ^ invert;
                b_valid = 1'b1; @(negedge clk);
                b_valid = 1'b0; @(negedge clk);
            end
            repeat (4) @(negedge clk);
            if (b_recv !== BPSK_BITS || b_perr !== 0 || b_inv !== invert) begin
                $display("FAIL bpsk invert=%0d: received %0d payload errors %0d lock_inverted %0b",
                         invert, b_recv, b_perr, b_inv);
                errors = errors + 1;
            end else begin
                $display("  bpsk invert=%0d: %0d bits, payload errors 0, lock_inverted=%0b", invert, b_recv, b_inv);
            end
        end
    endtask

    // ---------------- QPSK (two lock configurations) ----------------
    reg q_start = 1'b0, q_valid = 1'b0;
    reg [1:0] q_dibit = 2'b00;
    wire [1:0] rot_exact, rot_ota;
    wire [INDEX_W-1:0] sym_exact, sym_ota, err_exact, err_ota;

    qpsk_ber_counter #(.INDEX_W(INDEX_W), .MAX_FRAME_BITS(512),
                       .LOCK_PREAMBLE_BITS(8), .LOCK_ERR_TOL(0)) qexact (
        .clk(clk), .rst(rst), .start(q_start), .abort(1'b0),
        .symbol_count(QPSK_SYMS[INDEX_W-1:0]), .preamble_count(QPSK_PREAMBLE[INDEX_W-1:0]),
        .in_valid(q_valid), .in_dibit(q_dibit),
        .busy(), .done(), .quadrant_swapped(), .rotation_index(rot_exact),
        .received_symbols(sym_exact), .total_bit_errors(err_exact));
    qpsk_ber_counter #(.INDEX_W(INDEX_W), .MAX_FRAME_BITS(512),
                       .LOCK_PREAMBLE_BITS(24), .LOCK_ERR_TOL(3)) qota (
        .clk(clk), .rst(rst), .start(q_start), .abort(1'b0),
        .symbol_count(QPSK_SYMS[INDEX_W-1:0]), .preamble_count(QPSK_PREAMBLE[INDEX_W-1:0]),
        .in_valid(q_valid), .in_dibit(q_dibit),
        .busy(), .done(), .quadrant_swapped(), .rotation_index(rot_ota),
        .received_symbols(sym_ota), .total_bit_errors(err_ota));

    reg bi, bq;
    task run_qpsk(input [1:0] rot);
        begin
            @(negedge clk); q_start = 1'b1; @(negedge clk); q_start = 1'b0;
            for (n = 0; n < QPSK_SYMS; n = n + 1) begin
                bi = rom[2 * n][0];
                bq = rom[2 * n + 1][0];
                case (rot)
                    2'd0: q_dibit = {bq, bi};
                    2'd1: q_dibit = {bi, ~bq};       // I' = -Q, Q' = I
                    2'd2: q_dibit = {~bq, ~bi};      // I' = -I, Q' = -Q
                    default: q_dibit = {~bi, bq};    // I' = Q,  Q' = -I
                endcase
                q_valid = 1'b1; @(negedge clk);
                q_valid = 1'b0; repeat (3) @(negedge clk);
            end
            repeat (8) @(negedge clk);
            if (sym_exact !== QPSK_SYMS || err_exact !== 0 || rot_exact !== rot) begin
                $display("FAIL qpsk exact lock, rotation %0d deg: symbols %0d errors %0d rotation_index %0d",
                         rot * 90, sym_exact, err_exact, rot_exact);
                errors = errors + 1;
            end
            if (sym_ota !== QPSK_SYMS || err_ota !== 0 || rot_ota !== rot) begin
                $display("FAIL qpsk OTA lock, rotation %0d deg: symbols %0d errors %0d rotation_index %0d",
                         rot * 90, sym_ota, err_ota, rot_ota);
                errors = errors + 1;
            end
            if (rot_exact === rot && rot_ota === rot && err_exact === 0 && err_ota === 0)
                $display("  qpsk rotation %0d deg: 0 bit errors, rotation_index=%0d (exact and OTA lock)",
                         rot * 90, rot);
        end
    endtask

    initial begin
        repeat (4) @(negedge clk);
        rst = 1'b0;
        run_bpsk(1'b0);
        run_bpsk(1'b1);
        for (k = 0; k < 4; k = k + 1)
            run_qpsk(k[1:0]);
        if (errors == 0)
            $display("PASS: tb_ber_counter_rotation - polarity and k*90 rotation reported for BPSK and QPSK");
        else
            $display("FAIL: tb_ber_counter_rotation completed with %0d errors", errors);
        $finish;
    end
endmodule
