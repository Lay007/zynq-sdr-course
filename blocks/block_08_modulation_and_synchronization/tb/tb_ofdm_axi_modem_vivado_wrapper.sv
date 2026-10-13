`timescale 1ns/1ps

// The block-design wrapper with its internal TX -> RX fabric loopback, driven the
// way the PS and the AXI DMA will drive it: AXI4-Lite reads of ID / VERSION /
// CONFIG, then a byte stream of bit pairs on S_AXIS_TX (training symbol(s), then
// data, one tlast at the very end like a DMA MM2S transfer), and the decoded
// bytes collected from M_AXIS_RX with random backpressure. Every data pair
// must come back, in order, with tlast on every 48th byte, and the modem must
// report its training done and no saturation.
module tb_ofdm_axi_modem_vivado_wrapper;
    parameter integer TRAIN_SYMBOLS = 1;
    localparam integer DATA_SYMBOLS = 4;
    localparam integer DATA_PAIRS = 48 * DATA_SYMBOLS;

    reg aclk = 1'b0;
    always #5 aclk = ~aclk;
    reg aresetn = 1'b0;

    reg  [31:0] awaddr = 0, wdata = 0, araddr = 0;
    reg         awvalid = 0, wvalid = 0, bready = 1, arvalid = 0, rready = 1;
    reg  [3:0]  wstrb = 4'hf;
    wire        awready, wready, bvalid, arready, rvalid;
    wire [1:0]  bresp, rresp;
    wire [31:0] rdata;

    reg  [7:0] tx_data = 8'd0;
    reg        tx_valid = 1'b0, tx_last = 1'b0;
    wire       tx_ready;
    wire [7:0] rx_data;
    wire       rx_valid, rx_last;
    reg        rx_ready = 1'b0;

    ofdm_axi_modem_vivado_wrapper #(.CE_TRAIN_SYMBOLS(TRAIN_SYMBOLS)) dut (
        .s_axi_awaddr(awaddr), .s_axi_awvalid(awvalid), .s_axi_awready(awready),
        .s_axi_wdata(wdata), .s_axi_wstrb(wstrb), .s_axi_wvalid(wvalid), .s_axi_wready(wready),
        .s_axi_bresp(bresp), .s_axi_bvalid(bvalid), .s_axi_bready(bready),
        .s_axi_araddr(araddr), .s_axi_arvalid(arvalid), .s_axi_arready(arready),
        .s_axi_rdata(rdata), .s_axi_rresp(rresp), .s_axi_rvalid(rvalid), .s_axi_rready(rready),
        .s_axis_tx_tdata(tx_data), .s_axis_tx_tvalid(tx_valid), .s_axis_tx_tready(tx_ready),
        .s_axis_tx_tlast(tx_last),
        .m_axis_rx_tdata(rx_data), .m_axis_rx_tvalid(rx_valid), .m_axis_rx_tready(rx_ready),
        .m_axis_rx_tlast(rx_last),
        .aclk(aclk), .aresetn(aresetn)
    );

    integer errors = 0;
    integer seed = 32'h48D5;
    integer received = 0;
    integer i, timeout;
    reg [31:0] word;
    reg [1:0] sent_bits [0:DATA_PAIRS-1];

    // Training pattern of ofdm_channel_equalizer train_bits(): {I bit, Q bit}.
    function [1:0] train_bits;
        input [5:0] d;
        train_bits = {d[0] ^ d[3], d[1] ^ d[2] ^ d[4]};
    endfunction

    task automatic axi_read(input [31:0] addr, output [31:0] value);
        begin
            @(negedge aclk); araddr = addr; arvalid = 1'b1;
            @(posedge aclk); while (!arready) @(posedge aclk);
            @(negedge aclk); arvalid = 1'b0;
            while (!rvalid) @(posedge aclk);
            value = rdata;
            @(negedge aclk);
        end
    endtask

    task automatic expect_reg(input [31:0] addr, input [31:0] expected);
        reg [31:0] got;
        begin
            axi_read(addr, got);
            if (got !== expected) begin
                $display("FAIL register 0x%02h = 0x%08h, expected 0x%08h", addr, got, expected);
                errors = errors + 1;
            end
        end
    endtask

    task automatic send_pair(input [1:0] bits, input last);
        begin
            @(negedge aclk); tx_data = {6'd0, bits}; tx_last = last; tx_valid = 1'b1;
            @(posedge aclk); while (!tx_ready) @(posedge aclk);
            @(negedge aclk); tx_valid = 1'b0; tx_last = 1'b0;
        end
    endtask

    // The data bytes come back in FFT bin order (data indices 24..47, then 0..23).
    always @(posedge aclk) begin
        if (aresetn && rx_valid && rx_ready) begin
            if (received < DATA_PAIRS) begin
                if (rx_data[1:0] !== sent_bits[(received / 48) * 48 + rx_data[7:2]]) begin
                    if (errors < 8)
                        $display("FAIL pair %0d (index %0d): got %b", received, rx_data[7:2], rx_data[1:0]);
                    errors = errors + 1;
                end
                if (rx_last !== ((received % 48) == 47)) begin
                    $display("FAIL tlast at output byte %0d", received);
                    errors = errors + 1;
                end
            end
            received = received + 1;
        end
    end

    always @(negedge aclk)
        rx_ready <= ($random(seed) & 3) != 0;

    initial begin
        for (i = 0; i < DATA_PAIRS; i = i + 1)
            sent_bits[i] = $random(seed);
        repeat (5) @(posedge aclk);
        aresetn = 1'b1;
        repeat (3) @(posedge aclk);

        expect_reg(32'h00, 32'h4F46444D);
        expect_reg(32'h04, 32'h00030100);
        expect_reg(32'h38, {23'd0, TRAIN_SYMBOLS[3:0], 5'b11111 & {(`OFDM_IFFT_BRAM != 0), 4'b1110}});

        for (i = 0; i < 48 * TRAIN_SYMBOLS; i = i + 1)
            send_pair(train_bits(i % 48), 1'b0);
        for (i = 0; i < DATA_PAIRS; i = i + 1)
            send_pair(sent_bits[i], i == DATA_PAIRS - 1);

        timeout = 0;
        while (received < DATA_PAIRS && timeout < 40000) begin
            @(posedge aclk);
            timeout = timeout + 1;
        end
        repeat (20) @(posedge aclk);
        if (received != DATA_PAIRS) begin
            $display("FAIL received %0d data pairs, expected %0d", received, DATA_PAIRS);
            errors = errors + 1;
        end
        expect_reg(32'h30, 32'd1);                    // one training completed
        expect_reg(32'h10, 32'd0);                    // TX saturations
        expect_reg(32'h2C, 32'd0);                    // channel-equalizer saturations
        axi_read(32'h0C, word);
        if (word[6] !== 1'b1 || word[4:3] !== 2'b00) begin
            $display("FAIL STATUS 0x%08h: expected trained and no frame errors", word);
            errors = errors + 1;
        end

        if (errors == 0) begin
            $display("PASS: ofdm_axi_modem_vivado_wrapper fabric loopback, %0d training symbol(s), %0d/%0d pairs back in order",
                     TRAIN_SYMBOLS, DATA_PAIRS, DATA_PAIRS);
            $finish;
        end else begin
            $display("FAIL tb_ofdm_axi_modem_vivado_wrapper errors=%0d", errors);
            $fatal(1);
        end
    end
endmodule
