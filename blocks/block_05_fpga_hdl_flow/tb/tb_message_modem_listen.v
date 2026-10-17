// Lab 11.49 (issue #55): one mailbox sends, another one listens, as two boards would.
//
// Two copies of the bridge's block-design wrapper (gpreg bridge + message mailbox, MODE = 1): T
// sends a message with TX_START; R has been told RX_LISTEN and keeps listening. R's RX tap gets a
// continuous sample stream, as from an ADC: T's burst while T transmits, small pseudo-random noise
// otherwise (the packet detector of the listen mode needs the noise to learn its level). Checks: R
// delivers the message with CRC_OK, sequence, length and bytes; R keeps listening and also delivers
// a second message after RX_ACK; RX_STOP ends listening; TX_START is refused while listening; R
// puts nothing on its DAC stream while it listens (on the bench a listening board sent a frame
// at every re-armed attempt, every 136 ms); after RX_STOP, R takes TX_START within microseconds
// instead of at the end of its listening window (issue #71).

`timescale 1ns/1ps

`ifndef NOISE_WAIT
`define NOISE_WAIT 20000
`endif

module tb_message_modem_listen;

localparam integer W = 16;
localparam [31:0] BASE = 32'h7905_0000;
localparam [31:0] MODE = 32'h0002_4010;   // QPSK (4) + Gardner (14) + differential (17)

reg ctrl_clk = 1'b0, sample_clk = 1'b0, ctrl_resetn = 1'b0, sample_resetn = 1'b0;
always #5 ctrl_clk = ~ctrl_clk;
always #4 sample_clk = ~sample_clk;

reg [31:0] gp_ctrl = 32'd0, gp_frame = 32'd152, gp_pre = 32'd48, gp_off = 32'd0;

// --- AXI-Lite masters for T (index 0) and R (index 1) --------------------------------------------
reg  [31:0] awaddr [0:1], wdata [0:1], araddr [0:1];
reg         awvalid [0:1], wvalid [0:1], arvalid [0:1];
wire        awready [0:1], wready [0:1], bvalid [0:1], arready [0:1], rvalid [0:1];
wire [31:0] rdata [0:1];
wire [2*W:0] t_tx_bus, r_tx_bus;

// R's ADC: T's burst when valid, else noise; one sample per sample_clk.
reg [15:0] lfsr = 16'hACE1;
always @(posedge sample_clk) lfsr <= {lfsr[14:0], lfsr[15] ^ lfsr[13] ^ lfsr[12] ^ lfsr[10]};
wire signed [W-1:0] noise_i = {{(W-2){lfsr[2]}}, lfsr[1:0]};   // -4..3
wire signed [W-1:0] noise_q = {{(W-2){lfsr[7]}}, lfsr[6:5]};
wire [2*W:0] r_rx_bus = t_tx_bus[2*W] ? t_tx_bus : {1'b1, noise_i, noise_q};

// R only listens: count what it sends to its DAC.
integer r_tx_samples = 0;
always @(posedge sample_clk) if (r_tx_bus[2*W]) r_tx_samples = r_tx_samples + 1;

genvar gi;
generate
for (gi = 0; gi < 2; gi = gi + 1) begin : g_dut
    wire [2*W:0] rx_bus = (gi == 0) ? t_tx_bus : r_rx_bus;
    wire [2*W:0] tx_bus;
    wire [31:0] st, rb, te, sg, tv, rv, ai, cd;
    wire tpa;
    wire [1:0] bresp, rresp;
    bpsk_zynq_ber_bridge_bd #(
        .MEM_FILE("blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem"),
        .COEF_FILE("blocks/block_05_fpga_hdl_flow/rtl/bpsk_rrc_tx_fir_taps.mem")
    ) dut (
        .ctrl_clk(ctrl_clk), .ctrl_resetn(ctrl_resetn),
        .adc_input_clk(sample_clk), .adc_input_reset(1'b0), .adc_input_enable(1'b0),
        .adc_input_i({W{1'b0}}), .adc_input_q({W{1'b0}}), .adc_input_valid(1'b0),
        .adc_input2_i({W{1'b0}}), .adc_input2_q({W{1'b0}}), .adc_input2_valid(1'b0),
        .sample_clk(sample_clk), .sample_resetn(sample_resetn),
        .gp_ctrl(gp_ctrl), .gp_frame_bit_count(gp_frame), .gp_preamble_count(gp_pre), .gp_start_offset(gp_off),
        .gp_status(st), .gp_received_bits(rb), .gp_total_errors(te), .gp_signature(sg),
        .gp_tx_valid_count(tv), .gp_rx_valid_count(rv), .gp_adc_input_debug(ai), .gp_capture_debug(cd),
        .tx_path_active(tpa), .tx_sample_bus(tx_bus), .rx_sample_bus(rx_bus),
        .s_axi_aclk(ctrl_clk), .s_axi_aresetn(ctrl_resetn),
        .s_axi_awaddr(awaddr[gi]), .s_axi_awprot(3'd0), .s_axi_awvalid(awvalid[gi]), .s_axi_awready(awready[gi]),
        .s_axi_wdata(wdata[gi]), .s_axi_wstrb(4'hF), .s_axi_wvalid(wvalid[gi]), .s_axi_wready(wready[gi]),
        .s_axi_bresp(bresp), .s_axi_bvalid(bvalid[gi]), .s_axi_bready(1'b1),
        .s_axi_araddr(araddr[gi]), .s_axi_arprot(3'd0), .s_axi_arvalid(arvalid[gi]), .s_axi_arready(arready[gi]),
        .s_axi_rdata(rdata[gi]), .s_axi_rresp(rresp), .s_axi_rvalid(rvalid[gi]), .s_axi_rready(1'b1)
    );
end
endgenerate
assign t_tx_bus = g_dut[0].tx_bus;
assign r_tx_bus = g_dut[1].tx_bus;

`ifdef TRACE
always @(posedge sample_clk) begin
    if (g_dut[1].dut.inst.msg_listen_edge)
        $display("%0t R listen start (core busy %0d)", $time, g_dut[1].dut.inst.qpsk_busy);
    if (g_dut[1].dut.inst.qpsk_done || g_dut[1].dut.inst.qpsk_timed_out)
        $display("%0t R core done %0d timeout %0d recv %0d", $time, g_dut[1].dut.inst.qpsk_done,
                 g_dut[1].dut.inst.qpsk_timed_out, g_dut[1].dut.inst.received_bits);
    if (g_dut[0].dut.inst.msg_start_edge)
        $display("%0t T message start", $time);
    if (g_dut[0].dut.inst.qpsk_done || g_dut[0].dut.inst.qpsk_timed_out)
        $display("%0t T core done %0d timeout %0d recv %0d tx_path_active %0d", $time, g_dut[0].dut.inst.qpsk_done,
                 g_dut[0].dut.inst.qpsk_timed_out, g_dut[0].dut.inst.received_bits, g_dut[0].dut.inst.tx_path_active_sample);
    if (g_dut[0].dut.inst.msg_start_edge)
        $display("%0t T core busy at start %0d", $time, g_dut[0].dut.inst.qpsk_busy);
    if (g_dut[1].dut.inst.msg_cap_delay == 3'd7)
        $display("%0t R capture: rx_bits_count %0d done_sticky %0d shift[63:0] %h", $time,
                 g_dut[1].dut.inst.rx_bits_count, g_dut[1].dut.inst.done_sticky_sample,
                 g_dut[1].dut.inst.rx_bits_shift[63:0]);
end
integer dib_fd;
initial dib_fd = $fopen("tmp/listen/r_dibits.txt", "w");
always @(posedge sample_clk) begin
    if (g_dut[1].dut.inst.qpsk_recovered_valid_debug)
        $fwrite(dib_fd, "%0t %0d %0d %0d\n", $time, g_dut[1].dut.inst.qpsk_recovered_dibit_debug,
                g_dut[1].dut.inst.qpsk_core_i.ber_counter_i.winner_valid, g_dut[1].dut.inst.qpsk_core_i.rx_chain_i.pkt_present);
end
reg [2*W-1:0] t_prev = 0;
integer t_same = 0;
always @(posedge sample_clk) begin
    if (t_tx_bus[2*W]) begin
        if (t_tx_bus[2*W-1:0] == t_prev && t_tx_bus[2*W-1:0] != 0) t_same = t_same + 1; else begin
            if (t_same > 50) $display("%0t T output held at %h for %0d samples", $time, t_prev, t_same);
            t_same = 0;
        end
        t_prev = t_tx_bus[2*W-1:0];
    end
end
integer det_n = 0;
always @(posedge sample_clk) begin
    if (g_dut[1].dut.inst.qpsk_core_i.rx_chain_i.sym_valid) begin
        det_n = det_n + 1;
        if (det_n % 200 == 0 || (g_dut[0].dut.inst.tx_path_active_sample && det_n % 20 == 0))
            $display("%0t DET short %0d long %0d present %0d seeded %0d sym_valid_rate T_active %0d", $time,
                     g_dut[1].dut.inst.qpsk_core_i.rx_chain_i.packet_detect_i.short_mean,
                     g_dut[1].dut.inst.qpsk_core_i.rx_chain_i.packet_detect_i.long_mean,
                     g_dut[1].dut.inst.qpsk_core_i.rx_chain_i.pkt_present,
                     g_dut[1].dut.inst.qpsk_core_i.rx_chain_i.packet_detect_i.seeded,
                     g_dut[0].dut.inst.tx_path_active_sample);
    end
end
integer r_dec = 0;
always @(posedge sample_clk) begin
    if (g_dut[1].dut.inst.msg_listen_edge) r_dec = 0;
    if (g_dut[1].dut.inst.qpsk_recovered_valid_debug) r_dec = r_dec + 1;
    if (g_dut[1].dut.inst.qpsk_done) $display("%0t R decisions passed this attempt: %0d", $time, r_dec);
end
always @(posedge ctrl_clk)
    if (g_dut[1].dut.mailbox_i.rx_toggle_edge)
        $display("%0t R mailbox: locked %0d crc_ok %0d len %0d packet %h", $time, g_dut[1].dut.mailbox_i.modem_rx_locked,
                 g_dut[1].dut.mailbox_i.rx_crc_ok, g_dut[1].dut.mailbox_i.rx_len, g_dut[1].dut.mailbox_i.rx_packet);
`endif

task axi_write(input integer who, input [31:0] off, input [31:0] value);
    begin
        @(negedge ctrl_clk);
        awaddr[who] = BASE + off; wdata[who] = value; awvalid[who] = 1; wvalid[who] = 1;
        while (awvalid[who] || wvalid[who]) begin
            @(posedge ctrl_clk);
            if (awready[who]) awvalid[who] <= 0;
            if (wready[who]) wvalid[who] <= 0;
            @(negedge ctrl_clk);
        end
        while (!bvalid[who]) @(negedge ctrl_clk);
        @(negedge ctrl_clk);
    end
endtask

reg [31:0] rd;
task axi_read(input integer who, input [31:0] off);
    begin
        @(negedge ctrl_clk);
        araddr[who] = BASE + off; arvalid[who] = 1;
        @(posedge ctrl_clk);
        while (!arready[who]) @(posedge ctrl_clk);
        @(negedge ctrl_clk); arvalid[who] = 0;
        while (!rvalid[who]) @(negedge ctrl_clk);
        rd = rdata[who];
        @(negedge ctrl_clk);
    end
endtask

integer errors = 0, k, waited, r_tx_listening = 0;
reg [63:0] t_stop;
reg [8*16-1:0] text1 = "listen to this 1";
reg [8*16-1:0] text2 = "and to this one!";

task check(input [8*40-1:0] what, input [31:0] got, input [31:0] want);
    begin
        if (got !== want) begin
            errors = errors + 1;
            $display("FAIL %0s: got 0x%08x want 0x%08x", what, got, want);
        end
    end
endtask

function [31:0] word_of(input [8*16-1:0] s, input integer w);
    word_of = {s[8*(15 - (4*w+3)) +: 8], s[8*(15 - (4*w+2)) +: 8], s[8*(15 - (4*w+1)) +: 8], s[8*(15 - 4*w) +: 8]};
endfunction

task send_from_t(input [31:0] seq, input [8*16-1:0] s);
    begin
        axi_write(0, 32'h10, seq);
        axi_write(0, 32'h14, 32'd16);
        for (k = 0; k < 4; k = k + 1) axi_write(0, 32'h20 + 4*k, word_of(s, k));
        axi_write(0, 32'h08, 32'h1);
    end
endtask

task expect_at_r(input [31:0] seq, input [8*16-1:0] s);
    begin
        waited = 0;
        axi_read(1, 32'h0C);
        while (!rd[2] && waited < 400000) begin
            repeat (50) @(posedge ctrl_clk);
            waited = waited + 50;
            axi_read(1, 32'h0C);
        end
        if (!rd[2]) begin
            errors = errors + 1;
            $display("FAIL: R delivered nothing (status 0x%x)", rd);
        end else begin
            check("R listening while delivering", {31'd0, rd[4]}, 32'd1);
            axi_read(1, 32'h68); check("R RX_META", rd, 32'h1);
            axi_read(1, 32'h60); check("R RX_SEQUENCE", rd, seq);
            axi_read(1, 32'h64); check("R RX_LENGTH", rd, 32'd16);
            for (k = 0; k < 4; k = k + 1) begin
                axi_read(1, 32'h70 + 4*k); check("R RX_DATA", rd, word_of(s, k));
            end
            $display("R delivered sequence 0x%x", seq);
        end
        axi_write(1, 32'h08, 32'h2);       // RX_ACK
    end
endtask

initial begin
    for (k = 0; k < 2; k = k + 1) begin
        awaddr[k] = 0; wdata[k] = 0; araddr[k] = 0; awvalid[k] = 0; wvalid[k] = 0; arvalid[k] = 0;
    end
    repeat (10) @(posedge ctrl_clk);
    ctrl_resetn = 1; sample_resetn = 1;
    gp_ctrl = MODE;
    repeat (20) @(posedge ctrl_clk);

    axi_write(1, 32'h08, 32'h4);                       // R: RX_LISTEN
    axi_read(1, 32'h0C); check("R STATUS.listening", {31'd0, rd[4]}, 32'd1);
    axi_write(1, 32'h08, 32'h1);                       // TX_START on R must be refused while listening
    axi_read(1, 32'h0C); check("R TX_START refused (tx_busy)", {31'd0, rd[0]}, 32'd0);

    repeat (`NOISE_WAIT) @(posedge sample_clk);        // let R learn the noise level
    send_from_t(32'h0000_0A01, text1);
    expect_at_r(32'h0000_0A01, text1);

    repeat (5000) @(posedge sample_clk);
    send_from_t(32'h0000_0A02, text2);
    expect_at_r(32'h0000_0A02, text2);

    repeat (2000) @(posedge sample_clk);                // R is in a fresh listening attempt by now
    r_tx_listening = r_tx_samples;                      // what R sent while it listened
    axi_write(1, 32'h08, 32'h8);                       // RX_STOP
    axi_read(1, 32'h0C); check("R STATUS after RX_STOP", {31'd0, rd[4]}, 32'd0);
    // #71: the listening attempt in flight ends at once, so TX_START is taken right away
    t_stop = $time;
    waited = 0;
    rd = 0;
    while (!rd[0] && waited < 20000) begin
        axi_write(1, 32'h08, 32'h1);                   // TX_START
        axi_read(1, 32'h0C);
        waited = waited + 1;
    end
    if (!rd[0]) begin
        errors = errors + 1;
        $display("FAIL: R did not take TX_START after RX_STOP");
    end else begin
        $display("R took TX_START %0d ns after RX_STOP", $time - t_stop);
        if ($time - t_stop > 64'd100_000) begin           // 100 us (time unit ns); a listening window is 4.2 ms here
            errors = errors + 1;
            $display("FAIL: TX_START waited for the listening window instead of ending it");
        end
    end

    if (r_tx_listening != 0) begin
        errors = errors + 1;
        $display("FAIL: the listening R put %0d samples on its DAC stream", r_tx_listening);
    end
    if (errors == 0)
        $display("PASS tb_message_modem_listen: two messages from T delivered to the listening R");
    else
        $display("FAIL tb_message_modem_listen: %0d errors", errors);
    $finish;
end

endmodule
