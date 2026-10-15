// Lab 11.49 (issue #55): a message through the PS/PL mailbox and the QPSK modem, end to end.
//
// Drives the bridge's block-design wrapper (bpsk_zynq_ber_bridge_bd: the gpreg bridge plus the
// message mailbox, MODE = 1) the way the PS does: AXI-Lite writes at the board address 0x79050000
// (the interconnect passes the full address), gp_* words for the modem mode, then TX_START. The
// DAC stream is looped straight back into the RX tap (tx_sample_bus -> rx_sample_bus), so the
// burst the modem sends from the mailbox comes back to its own receiver, is decoded, de-whitened,
// CRC-checked and lands in the RX registers. Checks: a 18-byte message arrives with CRC_OK and the
// same sequence, length and bytes; a 30-byte message (over the 27-byte limit) completes at once
// with FRAME_ERROR; the echo-mode ID/version registers read the modem version.

`timescale 1ns/1ps

module tb_message_modem_loopback;

localparam integer W = 16;
localparam [31:0] BASE = 32'h7905_0000;
localparam [31:0] MODE = 32'h0002_0010;   // QPSK (bit 4) + differential (bit 17), coherent loopback

reg ctrl_clk = 1'b0, sample_clk = 1'b0, ctrl_resetn = 1'b0, sample_resetn = 1'b0;
always #5 ctrl_clk = ~ctrl_clk;           // 100 MHz CPU / AXI
always #4 sample_clk = ~sample_clk;       // 125 MHz sample domain (asynchronous)

reg [31:0] gp_ctrl = 32'd0, gp_frame_bit_count = 32'd0, gp_preamble_count = 32'd0, gp_start_offset = 32'd0;
wire [31:0] gp_status, gp_received_bits, gp_total_errors, gp_signature;
wire [31:0] gp_tx_valid_count, gp_rx_valid_count, gp_adc_input_debug, gp_capture_debug;
wire tx_path_active;
wire [2*W:0] tx_sample_bus;

reg  [31:0] awaddr = 0, wdata = 0, araddr = 0;
reg         awvalid = 0, wvalid = 0, bready = 1, arvalid = 0, rready = 1;
wire        awready, wready, bvalid, arready, rvalid;
wire [1:0]  bresp, rresp;
wire [31:0] rdata;

bpsk_zynq_ber_bridge_bd #(
    .MEM_FILE("blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem"),
    .COEF_FILE("blocks/block_05_fpga_hdl_flow/rtl/bpsk_rrc_tx_fir_taps.mem")
) dut (
    .ctrl_clk(ctrl_clk), .ctrl_resetn(ctrl_resetn),
    .adc_input_clk(sample_clk), .adc_input_reset(1'b0), .adc_input_enable(1'b0),
    .adc_input_i({W{1'b0}}), .adc_input_q({W{1'b0}}), .adc_input_valid(1'b0),
    .adc_input2_i({W{1'b0}}), .adc_input2_q({W{1'b0}}), .adc_input2_valid(1'b0),
    .sample_clk(sample_clk), .sample_resetn(sample_resetn),
    .gp_ctrl(gp_ctrl), .gp_frame_bit_count(gp_frame_bit_count), .gp_preamble_count(gp_preamble_count),
    .gp_start_offset(gp_start_offset),
    .gp_status(gp_status), .gp_received_bits(gp_received_bits), .gp_total_errors(gp_total_errors),
    .gp_signature(gp_signature), .gp_tx_valid_count(gp_tx_valid_count), .gp_rx_valid_count(gp_rx_valid_count),
    .gp_adc_input_debug(gp_adc_input_debug), .gp_capture_debug(gp_capture_debug),
    .tx_path_active(tx_path_active), .tx_sample_bus(tx_sample_bus), .rx_sample_bus(tx_sample_bus),
    .s_axi_aclk(ctrl_clk), .s_axi_aresetn(ctrl_resetn),
    .s_axi_awaddr(awaddr), .s_axi_awprot(3'd0), .s_axi_awvalid(awvalid), .s_axi_awready(awready),
    .s_axi_wdata(wdata), .s_axi_wstrb(4'hF), .s_axi_wvalid(wvalid), .s_axi_wready(wready),
    .s_axi_bresp(bresp), .s_axi_bvalid(bvalid), .s_axi_bready(bready),
    .s_axi_araddr(araddr), .s_axi_arprot(3'd0), .s_axi_arvalid(arvalid), .s_axi_arready(arready),
    .s_axi_rdata(rdata), .s_axi_rresp(rresp), .s_axi_rvalid(rvalid), .s_axi_rready(rready)
);

task axi_write(input [31:0] off, input [31:0] value);
    begin
        @(negedge ctrl_clk);
        awaddr = BASE + off; wdata = value; awvalid = 1; wvalid = 1;
        while (awvalid || wvalid) begin
            @(posedge ctrl_clk);
            if (awready) awvalid <= 0;
            if (wready) wvalid <= 0;
            @(negedge ctrl_clk);
        end
        while (!bvalid) @(negedge ctrl_clk);
        @(negedge ctrl_clk);
    end
endtask

reg [31:0] rd;
task axi_read(input [31:0] off);
    begin
        @(negedge ctrl_clk);
        araddr = BASE + off; arvalid = 1;
        @(posedge ctrl_clk);
        while (!arready) @(posedge ctrl_clk);
        @(negedge ctrl_clk); arvalid = 0;
        while (!rvalid) @(negedge ctrl_clk);
        rd = rdata;
        @(negedge ctrl_clk);
    end
endtask

integer errors = 0, so, waited, k, ok_offsets;
reg [31:0] meta;
reg [8*18-1:0] text = "Hello from board A";
reg [31:0] word;
reg [7:0] msg [0:17];

task check(input [8*48-1:0] what, input [31:0] got, input [31:0] want);
    begin
        if (got !== want) begin
            errors = errors + 1;
            $display("FAIL %0s: got 0x%08x want 0x%08x", what, got, want);
        end
    end
endtask

task send_and_wait(output [31:0] status);
    begin
        axi_write(32'h08, 32'h1);                     // TX_START
        waited = 0;
        axi_read(32'h0C);
        while (!rd[2] && waited < 200000) begin       // RX_VALID
            repeat (20) @(posedge ctrl_clk);
            waited = waited + 20;
            axi_read(32'h0C);
        end
        status = rd;
    end
endtask

initial begin
    for (k = 0; k < 18; k = k + 1)
        msg[k] = text[8*(17 - k) +: 8];
    repeat (10) @(posedge ctrl_clk);
    ctrl_resetn = 1; sample_resetn = 1;
    repeat (10) @(posedge ctrl_clk);

    axi_read(32'h00); check("ID", rd, 32'h4D424F58);
    axi_read(32'h04); check("VERSION (modem)", rd, 32'h0002_0000);

    // modem mode words, as the PS sets them before using the mailbox
    gp_ctrl = MODE;
    gp_frame_bit_count = 152;
    gp_preamble_count = 48;

    axi_write(32'h10, 32'h0000_1234);                 // TX_SEQUENCE
    axi_write(32'h14, 32'd18);                        // TX_LENGTH
    for (k = 0; k < 5; k = k + 1) begin
        word = {k*4+3 < 18 ? msg[k*4+3] : 8'h00, k*4+2 < 18 ? msg[k*4+2] : 8'h00,
                k*4+1 < 18 ? msg[k*4+1] : 8'h00, msg[k*4]};
        axi_write(32'h20 + 4*k, word);
    end

    // the fixed-phase sampler needs the right start_offset on a coherent loopback: sweep it
    ok_offsets = 0;
    for (so = 56; so <= 68; so = so + 1) begin
        gp_start_offset = so;
        repeat (20) @(posedge sample_clk);
        send_and_wait(word);
        axi_read(32'h68);
        meta = rd;
        if (meta == 32'h1) begin
            ok_offsets = ok_offsets + 1;
            axi_read(32'h60); check("RX_SEQUENCE", rd, 32'h1234);
            axi_read(32'h64); check("RX_LENGTH", rd, 32'd18);
            for (k = 0; k < 5; k = k + 1) begin
                axi_read(32'h70 + 4*k);
                check("RX_DATA", rd, {k*4+3 < 18 ? msg[k*4+3] : 8'h00, k*4+2 < 18 ? msg[k*4+2] : 8'h00,
                                      k*4+1 < 18 ? msg[k*4+1] : 8'h00, msg[k*4]});
            end
        end
        $display("start_offset %0d: status 0x%x RX_META 0x%x", so, word, meta);
        axi_write(32'h08, 32'h2);                     // RX_ACK
    end
    if (ok_offsets == 0) begin
        errors = errors + 1;
        $display("FAIL: no start_offset delivered the message with CRC_OK");
    end

    axi_write(32'h14, 32'd30);                        // over the 27-byte limit
    send_and_wait(word);
    axi_read(32'h68); check("RX_META for 30 bytes", rd, 32'h2);
    if (waited > 100) begin
        errors = errors + 1;
        $display("FAIL: a 30-byte message did not complete at once (%0d clocks)", waited);
    end
    axi_write(32'h08, 32'h2);

    if (errors == 0)
        $display("PASS tb_message_modem_loopback: message delivered with CRC_OK at %0d of 13 sampling phases", ok_offsets);
    else
        $display("FAIL tb_message_modem_loopback: %0d errors", errors);
    $finish;
end

endmodule
