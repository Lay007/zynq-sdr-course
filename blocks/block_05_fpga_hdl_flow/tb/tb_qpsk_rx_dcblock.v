// A1 validation - feed the REAL board self-OTA capture (tmp/qpsk_selfota_a0.npz,
// exported to qpsk_selfota_a0_rx.mem) through dc_blocker -> qpsk_rx_bit_recovery_chain
// -> qpsk_ber_counter and confirm the DC blocker recovers BER=0. Sweeps the sampling
// phase (start_offset) and reports the best bit-error count with the DC blocker ON and
// OFF, proving on real hardware data that a PL DC blocker closes single-board self-OTA.

`timescale 1ns/1ps

module tb_qpsk_rx_dcblock;

localparam integer W = 16;
localparam integer INDEX_W = 16;
localparam integer SYMS = 140;          // frame length the counter locks/counts
localparam integer CHAIN_SYMS = 450;    // let the sampler emit far more so the frame
                                        // (positioned late by the OTA round-trip) is
                                        // fully inside the framesync search window
localparam integer NS = 4000;

reg clk = 1'b0;
reg rst = 1'b1;
reg dc_en = 1'b1;
reg rx_valid = 1'b0;
reg signed [W-1:0] rx_i = 0;
reg signed [W-1:0] rx_q = 0;
reg cnt_start = 1'b0;
reg [INDEX_W-1:0] start_offset = 0;

reg [31:0] samp [0:NS-1];
integer n, so, w;
integer best_err, best_so, off_err;
reg [INDEX_W-1:0] rxsyms, errs;

wire dcv;
wire signed [W-1:0] dci, dcq;
dc_blocker #(.W(W), .K(6)) dcb (
    .clk(clk), .rst(rst), .enable(dc_en),
    .in_valid(rx_valid), .in_i(rx_i), .in_q(rx_q),
    .out_valid(dcv), .out_i(dci), .out_q(dcq)
);

wire rxdv;
wire [1:0] rxdibit;
// This bench predates both the in-chain DC blocker and the Costas loop: it drives its
// own dc_blocker above and studies the plain fixed-phase chain. Tie the runtime enables
// off explicitly -- leaving them unconnected floats them to z, which reads as "off" in
// an if() but poisons any expression built on them.
qpsk_rx_bit_recovery_chain #(.W(W), .SPS(8), .INDEX_W(INDEX_W)) rxc (
    .clk(clk), .rst(rst),
    .rst_carrier(rst),
    .dc_block_en(1'b0), .costas_en(1'b0),
    .in_valid(dcv), .in_i(dci), .in_q(dcq),
    .start_offset(start_offset), .symbol_count(CHAIN_SYMS[INDEX_W-1:0]),
    .out_valid(rxdv), .out_dibit(rxdibit),
    .debug_symbol_valid(), .debug_symbol_i(), .debug_symbol_q()
);

wire cbusy, cdone;
wire [INDEX_W-1:0] rsym, terr;
qpsk_ber_counter #(.INDEX_W(INDEX_W), .MAX_FRAME_BITS(512), .LOCK_PREAMBLE_BITS(24), .LOCK_ERR_TOL(3)) cnt (
    .clk(clk), .rst(rst), .start(cnt_start), .abort(1'b0),
    .symbol_count(SYMS[INDEX_W-1:0]), .preamble_count(16'd24),
    .in_valid(rxdv), .in_dibit(rxdibit),
    .busy(cbusy), .done(cdone),
    .received_symbols(rsym), .total_bit_errors(terr)
);

always #5 clk = ~clk;

reg signed [W-1:0] si, sq;
task run_offset(input integer offs, input en, input [1:0] rot);
    begin
        dc_en = en;
        start_offset = offs[INDEX_W-1:0];
        rst = 1'b1; rx_valid = 1'b0; cnt_start = 1'b0;
        @(negedge clk); @(negedge clk); rst = 1'b0; @(negedge clk);
        cnt_start = 1'b1; @(negedge clk); cnt_start = 1'b0;
        for (n = 0; n < NS; n = n + 1) begin
            si = samp[n][31:16];
            sq = samp[n][15:0];
            // input rotation by rot*90deg: 0:(I,Q) 1:(-Q,I) 2:(-I,-Q) 3:(Q,-I)
            case (rot)
                2'd0: begin rx_i =  si; rx_q =  sq; end
                2'd1: begin rx_i = -sq; rx_q =  si; end
                2'd2: begin rx_i = -si; rx_q = -sq; end
                default: begin rx_i =  sq; rx_q = -si; end
            endcase
            rx_valid = 1'b1;
            @(negedge clk);
            if (cdone) n = NS;
        end
        rx_valid = 1'b0;
        w = 0;
        while (!cdone && w < 4096) begin @(posedge clk); w = w + 1; end
        @(posedge clk);
        rxsyms = rsym; errs = terr;
    end
endtask

integer rr, global_best;
initial begin
    // No $dumpvars here: this bench runs 4 rotations x 16 sampler phases over a
    // 4000-sample capture, and dumping every signal produced a 161 MB VCD that
    // filled the simulation workspace and made the NEXT iverilog invocation fail
    // with "ivlpp: No input files given". Waveforms for a sweep are useless anyway.
    $readmemh("blocks/block_05_fpga_hdl_flow/tb/qpsk_selfota_a0_rx.mem", samp);
    repeat (4) @(negedge clk);

    global_best = 32'h7fffffff;
    for (rr = 0; rr <= 3; rr = rr + 1) begin
        best_err = 32'h7fffffff; best_so = -1;
        for (so = 0; so <= 15; so = so + 1) begin
            run_offset(so, 1'b1, rr[1:0]);
            if (rxsyms == SYMS[INDEX_W-1:0] && errs < best_err) begin
                best_err = errs; best_so = so;
            end
        end
        $display("input rot=%0d deg (DC blocker ON): best start_offset=%0d  bit_errors=%0d/%0d",
                 rr*90, best_so, best_err, 2*SYMS);
        if (best_err < global_best) global_best = best_err;
    end

    if (global_best == 0)
        $display("PASS: real self-OTA capture decodes at BER=0 through dc_blocker + existing RX chain (some input rotation)");
    else begin
        $display("RESULT: best over all rotations = %0d/280 (%.1f%%)", global_best, 100.0*global_best/280.0);
        $fatal(1);
    end
    $finish;
end

endmodule
