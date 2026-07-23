// Bridge-level QPSK loopback: drives the real course sample-domain bridge
// (bpsk_zynq_ber_gpreg_bridge, now dual-modem) exactly like the runtime PS does
// — quasi-static gp_* control words, a start pulse, and the DAC->ADC digital
// loopback wired burst_out -> capture_in — but with gp_ctrl[4]=1 selecting the
// QPSK core. Sweeps gp_start_offset and passes if any sampling phase recovers a
// full frame at BER=0. This proves the QPSK path end-to-end through the gpreg
// plumbing / mode mux before spending a bitstream build.

`timescale 1ns/1ps

module tb_qpsk_bridge_loopback;

localparam integer W = 16;
localparam integer INDEX_W = 16;
localparam integer SYMS = 140;               // QPSK symbols (280 payload bits)
localparam [31:0]  CTRL_MODE_QPSK = 32'h0000_8010;  // QPSK + payload-position readout
localparam [31:0]  SIGNATURE_BPSK = 32'h4250_534B;  // overlay identity unchanged

reg ctrl_clk = 1'b0;
reg sample_clk = 1'b0;
reg ctrl_resetn = 1'b0;
reg sample_resetn = 1'b0;

reg [31:0] gp_ctrl = 32'd0;
// --- decoded-bit readout check (gp_ctrl[16]) -------------------------------
// The QPSK path exposes no decoded bits without this, so the readout itself needs a
// test: on the clean loopback the captured window must CONTAIN the frame ROM exactly.
reg [0:0] rom_bits [0:511];
reg [287:0] cap_bits = 288'd0;
reg [9:0]  cap_count = 10'd0;
integer wi, off, bi, mism;
integer match_off;

reg [31:0] gp_frame_bit_count = 32'd0;
reg [31:0] gp_preamble_count = 32'd0;
reg [31:0] gp_start_offset = 32'd0;

wire [31:0] gp_status;
wire [31:0] gp_received_bits;
wire [31:0] gp_total_errors;
wire [31:0] gp_signature;
wire [31:0] gp_tx_valid_count;
wire [31:0] gp_rx_valid_count;
wire [31:0] gp_adc_input_debug;
wire [31:0] gp_capture_debug;
wire        tx_path_active;
wire        burst_out_valid;
wire signed [W-1:0] burst_out_i;
wire signed [W-1:0] burst_out_q;

integer so, w;
integer best_err = 32'h7fffffff;
integer best_so = -1;
integer best_rx = 0;
reg [31:0] best_segments = 32'hffff_ffff;
reg [31:0] best_position = 32'd0;

// The bridge samples gp_* on sample_clk and reports counters on ctrl_clk.
bpsk_zynq_ber_gpreg_bridge #(
    .W(W),
    .SPS(8),
    .INDEX_W(INDEX_W),
    .MAX_FRAME_BITS(512),
    .PHASE_W(3),
    .FLUSH_SYMBOLS(16),
    .MEM_FILE("blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem"),
    .COEF_FILE("blocks/block_05_fpga_hdl_flow/rtl/bpsk_rrc_tx_fir_taps.mem")
) dut (
    .ctrl_clk(ctrl_clk),
    .ctrl_resetn(ctrl_resetn),
    .adc_input_clk(sample_clk),
    .adc_input_reset(1'b0),
    .adc_input_enable(1'b0),
    .adc_input_valid(1'b0),
    .adc_input_i({W{1'b0}}),
    .adc_input_q({W{1'b0}}),
    .adc_input2_valid(1'b0),
    .adc_input2_i({W{1'b0}}),
    .adc_input2_q({W{1'b0}}),
    .sample_clk(sample_clk),
    .sample_resetn(sample_resetn),
    .gp_ctrl(gp_ctrl),
    .gp_frame_bit_count(gp_frame_bit_count),
    .gp_preamble_count(gp_preamble_count),
    .gp_start_offset(gp_start_offset),
    .gp_status(gp_status),
    .gp_received_bits(gp_received_bits),
    .gp_total_errors(gp_total_errors),
    .gp_signature(gp_signature),
    .gp_tx_valid_count(gp_tx_valid_count),
    .gp_rx_valid_count(gp_rx_valid_count),
    .gp_adc_input_debug(gp_adc_input_debug),
    .gp_capture_debug(gp_capture_debug),
    .tx_path_active(tx_path_active),
    .burst_out_valid(burst_out_valid),
    .burst_out_i(burst_out_i),
    .burst_out_q(burst_out_q),
    // digital loopback: DAC stream straight back into the ADC capture tap
    .capture_in_valid(burst_out_valid),
    .capture_in_i(burst_out_i),
    .capture_in_q(burst_out_q)
);

always #5 ctrl_clk = ~ctrl_clk;      // 100 MHz control
always #4 sample_clk = ~sample_clk;  // ~125 MHz sample (async to ctrl)

initial begin
    $dumpfile("blocks/block_05_fpga_hdl_flow/tb/tb_qpsk_bridge_loopback.vcd");
    $dumpvars(0, tb_qpsk_bridge_loopback);

    repeat (8) @(posedge sample_clk);
    @(negedge sample_clk); ctrl_resetn = 1'b1; sample_resetn = 1'b1;
    repeat (8) @(posedge sample_clk);

    gp_frame_bit_count = SYMS;                // reinterpreted as QPSK symbol count
    gp_preamble_count = 32'd24;               // enable preamble frame-sync in the QPSK counter

    for (so = 55; so <= 70; so = so + 1) begin
        gp_start_offset = so;
        gp_ctrl = CTRL_MODE_QPSK;             // QPSK mode, start low
        repeat (6) @(posedge sample_clk);     // let mode select settle
        gp_ctrl = CTRL_MODE_QPSK | 32'h1;     // rising edge on start bit
        repeat (4) @(posedge sample_clk);
        gp_ctrl = CTRL_MODE_QPSK;             // release start

        // wait for done (status[2]) or timeout (status[3])
        w = 0;
        while (!gp_status[2] && !gp_status[3] && w < 40000) begin
            @(posedge ctrl_clk); w = w + 1;
        end
        repeat (4) @(posedge ctrl_clk);       // let counters cross to ctrl domain

        if (gp_received_bits[INDEX_W-1:0] == SYMS[INDEX_W-1:0] &&
            gp_total_errors[INDEX_W-1:0] < best_err) begin
            best_err = gp_total_errors[INDEX_W-1:0];
            best_so  = so;
            best_rx  = gp_received_bits[INDEX_W-1:0];
            best_segments = gp_tx_valid_count;
            best_position = gp_rx_valid_count;
        end

        // clear sticky done and let the core return to idle before next offset
        gp_ctrl = CTRL_MODE_QPSK | 32'h2;     // clear_done edge
        repeat (4) @(posedge sample_clk);
        gp_ctrl = CTRL_MODE_QPSK;
        w = 0;
        while (gp_status[1] && w < 40000) begin @(posedge sample_clk); w = w + 1; end
        repeat (8) @(posedge sample_clk);
    end

    // Re-run the winning offset, then read the decoded bits back out.
    $readmemh("blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem", rom_bits);
    gp_start_offset = best_so;
    gp_ctrl = CTRL_MODE_QPSK;
    repeat (6) @(posedge sample_clk);
    gp_ctrl = CTRL_MODE_QPSK | 32'h1;
    repeat (4) @(posedge sample_clk);
    gp_ctrl = CTRL_MODE_QPSK;
    w = 0;
    while (!gp_status[2] && !gp_status[3] && w < 40000) begin @(posedge ctrl_clk); w = w + 1; end
    repeat (4) @(posedge ctrl_clk);

    for (wi = 0; wi <= 9; wi = wi + 1) begin
        gp_start_offset = wi;
        gp_ctrl = CTRL_MODE_QPSK | 32'h1_0000;   // gp_ctrl[16] = decoded-bit readout
        repeat (4) @(posedge ctrl_clk);
        if (wi == 9) cap_count = gp_capture_debug[9:0];
        else cap_bits[32*wi +: 32] = gp_capture_debug;
    end
    gp_ctrl = CTRL_MODE_QPSK;

    // The shift reverses SYMBOL order but keeps I in the lower bit of each pair, so frame
    // bit i (symbol s = i>>1, axis = i&1) lands at 2*((SYMS-1-s) + soff) + axis, where soff
    // counts the symbols captured after the frame's last one. Accept any small soff.
    match_off = -1;
    for (off = 0; off <= 4; off = off + 1) begin
        mism = 0;
        for (bi = 0; bi < 2*SYMS; bi = bi + 1)
            if (cap_bits[2*((SYMS-1-(bi>>1)) + off) + (bi & 1)] !== rom_bits[bi])
                mism = mism + 1;
        if (mism == 0 && match_off < 0) match_off = off;
    end
    if (match_off >= 0)
        $display("PASS: decoded-bit readout reproduced all %0d frame bits (count=%0d, offset=%0d)",
                 2*SYMS, cap_count, match_off);
    else begin
        $display("FAIL: decoded-bit readout did not reproduce the frame (count=%0d)", cap_count);
        $fatal(1);
    end

    if (gp_signature !== SIGNATURE_BPSK)
        $display("WARN: unexpected signature %08x (expected %08x)", gp_signature, SIGNATURE_BPSK);

    $display("QPSK bridge loopback sweep: best start_offset=%0d received=%0d/%0d symbols, bit_errors=%0d/%0d",
             best_so, best_rx, SYMS, best_err, 2*SYMS);
    if (best_so >= 0 && best_err == 0 &&
        best_segments == 32'd0 && best_position == 32'hffff_ffff)
        $display("PASS: qpsk bridge loopback recovered %0d QPSK symbols at BER=0 (start_offset=%0d)",
                 SYMS, best_so);
    else begin
        $display("FAIL: no clean QPSK result with empty payload-position telemetry (best bit_errors=%0d segments=%08x position=%08x)",
                 best_err, best_segments, best_position);
        $fatal(1);
    end
    $finish;
end

endmodule
