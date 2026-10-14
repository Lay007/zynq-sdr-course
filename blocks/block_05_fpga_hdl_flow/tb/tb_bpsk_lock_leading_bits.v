// Issue #65 - the exact preamble lock must find the frame behind extra leading bits.
//
// The preamble starts with 0,0,0,0,0,1,1,0. The old sequential matcher restarted from the
// current bit on a mismatch and never backed up, so leading 0 bits walked it past the true
// frame start and it locked misaligned (140 of 281 bits wrong, also seen on silicon when the
// start offset was early). The counter now uses the sliding correlator with an exact match.
//
// This bench feeds the frame ROM preceded by 0..12 zero bits and by 0..12 random bits, in both
// polarities, with the course default lock (8 bits, LOCK_ERR_TOL 0). Every run must receive
// 281 bits with zero errors and report the right polarity.
`timescale 1ns/1ps
module tb_bpsk_lock_leading_bits;
    reg clk = 1'b0, rst = 1'b1, start = 1'b0, v = 1'b0, b = 1'b0;
    always #5 clk = ~clk;
    reg [0:0] rom [0:511];
    initial $readmemh("blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem", rom);
    wire busy, done, inv;
    wire [15:0] recv, terr, perr;
    bpsk_ber_counter #(.INDEX_W(16), .MAX_FRAME_BITS(512)) dut (
        .clk(clk), .rst(rst), .start(start), .abort(1'b0), .frame_bit_count(16'd281), .preamble_count(16'd24),
        .in_valid(v), .in_bit(b), .busy(busy), .done(done), .lock_acquired(), .lock_inverted(inv),
        .payload_out_valid(), .payload_out_bit(), .received_bits(recv), .total_errors(terr),
        .payload_errors(perr), .payload_error_segments(), .first_payload_error_index(), .last_payload_error_index());

    integer n, lead, invert, kind, errors = 0, runs = 0, seed = 65;
    reg lead_bit;
    task run(input integer lead_bits, input integer random_lead, input integer inverted);
        begin
            @(negedge clk); start = 1'b1; @(negedge clk); start = 1'b0;
            for (n = 0; n < lead_bits + 281 + 16; n = n + 1) begin
                lead_bit = random_lead ? $random(seed) : 1'b0;
                b = (n < lead_bits) ? lead_bit : (n < lead_bits + 281) ? (rom[n - lead_bits][0] ^ inverted[0]) : 1'b0;
                v = 1'b1; @(negedge clk); v = 1'b0; @(negedge clk);
            end
            repeat (4) @(negedge clk);
            runs = runs + 1;
            if (recv !== 16'd281 || terr !== 0 || perr !== 0 || inv !== inverted[0] || busy) begin
                $display("FAIL %0d %0s leading bits, inverted %0d: received %0d, total errors %0d, payload errors %0d, lock_inverted %0b",
                         lead_bits, random_lead ? "random" : "zero", inverted, recv, terr, perr, inv);
                errors = errors + 1;
                if (busy) begin rst = 1'b1; @(negedge clk); rst = 1'b0; end
            end
        end
    endtask

    initial begin
        repeat (3) @(negedge clk); rst = 1'b0;
        for (kind = 0; kind < 2; kind = kind + 1)
            for (invert = 0; invert < 2; invert = invert + 1)
                for (lead = 0; lead <= 12; lead = lead + 1)
                    run(lead, kind, invert);
        if (errors == 0)
            $display("PASS: tb_bpsk_lock_leading_bits - %0d runs, frame found behind 0-12 zero or random leading bits, both polarities", runs);
        else
            $display("FAIL: tb_bpsk_lock_leading_bits - %0d of %0d runs failed", errors, runs);
        $finish;
    end
endmodule
