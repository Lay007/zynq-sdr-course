`timescale 1ns/1ps

// Issue #48, verification stage 4: the OFDM modem of the board (ofdm_axi_modem, the parameters of
// the stage-3 DMA bitstream) driven from files, so that real radio samples can be pushed through
// the exact RTL receiver in simulation, and the transmitter's samples can be sent through a radio.
//
//   MODE = 0 (TX)  +BITS=<file> one bit group per line (hex: a QPSK bit pair, or a 16-QAM nibble),
//                  48 per OFDM symbol;  +OUT=<file> gets every TX sample as "re im" (Q1.15), 80 per
//                  symbol, cyclic prefix first.
//   MODE = 1 (RX)  +IQ=<file> received samples "re im" (Q1.15), already aligned so that every 80
//                  samples are one symbol, cyclic prefix first (the frame synchronization happens
//                  before this bench, see tools/ofdm_rf_link.py); the first CE_TRAIN_SYMBOLS of them
//                  are training symbols.  +OUT=<file> gets "data_index bits" per decided carrier.
//
// After reset the modem expects the training symbol(s) first, both ways. The bench prints one
// RESULT line with the symbol counts, the frame-error flags and the modem's CFO estimate.
//
// Without +OUT the bench checks itself (CI): it sends the training symbol and 4 random data symbols,
// keeps the transmitter's samples, feeds them back to the receiver one every 12 clocks, and
// requires every data bit pair back.
module tb_ofdm_modem_file;
    parameter integer MODE = 0;
    parameter integer MODULATION = 0;
    parameter integer CE_TRAIN_SYMBOLS = 1;
    localparam integer RX_W = (MODULATION != 0) ? 16 : 8;

    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg resetn = 1'b0;

    reg         tx_valid = 1'b0;
    wire        tx_ready;
    reg  [7:0]  tx_data = 8'd0;
    wire        txo_valid;
    wire [31:0] txo_data;
    wire        txo_last;
    reg         rx_valid = 1'b0;
    wire        rx_ready;
    reg  [31:0] rx_data = 32'd0;
    reg         rx_last = 1'b0;
    wire        rxo_valid;
    wire [RX_W-1:0] rxo_data;
    wire        rxo_last;
    wire        awready, wready, bvalid, arready, rvalid;
    wire [1:0]  bresp, rresp;
    wire [31:0] rdata;

    ofdm_axi_modem #(.MODULATION(MODULATION), .CE_TRAIN_SYMBOLS(CE_TRAIN_SYMBOLS)) dut (
        .aclk(clk), .aresetn(resetn),
        .s_axis_tx_tvalid(tx_valid), .s_axis_tx_tready(tx_ready), .s_axis_tx_tdata(tx_data), .s_axis_tx_tlast(1'b0),
        .m_axis_tx_tvalid(txo_valid), .m_axis_tx_tready(1'b1), .m_axis_tx_tdata(txo_data), .m_axis_tx_tlast(txo_last),
        .s_axis_rx_tvalid(rx_valid), .s_axis_rx_tready(rx_ready), .s_axis_rx_tdata(rx_data), .s_axis_rx_tlast(rx_last),
        .m_axis_rx_tvalid(rxo_valid), .m_axis_rx_tready(1'b1), .m_axis_rx_tdata(rxo_data), .m_axis_rx_tlast(rxo_last),
        .s_axi_awaddr(6'd0), .s_axi_awvalid(1'b0), .s_axi_awready(awready),
        .s_axi_wdata(32'd0), .s_axi_wstrb(4'd0), .s_axi_wvalid(1'b0), .s_axi_wready(wready),
        .s_axi_bresp(bresp), .s_axi_bvalid(bvalid), .s_axi_bready(1'b1),
        .s_axi_araddr(6'd0), .s_axi_arvalid(1'b0), .s_axi_arready(arready),
        .s_axi_rdata(rdata), .s_axi_rresp(rresp), .s_axi_rvalid(rvalid), .s_axi_rready(1'b1)
    );

    integer in_fd, out_fd = 0, r, v, re, im, n_in = 0, n_out = 0, n_tx_symbols = 0, n_rx_symbols = 0, idle = 0;
    integer k, errors = 0, seed = 7;
    reg selfcheck = 1'b0;
    reg [1023:0] in_name, out_name;
    reg [31:0] tx_mem [0:399];
    reg [1:0] sent [0:191];
    reg [1:0] got [0:191];
    reg [191:0] seen;

    // One always block for every counter: the self-check stores by n_out / n_rx_symbols before they move.
    always @(posedge clk) begin
        if (rxo_valid && selfcheck && MODULATION == 0) begin
            if (n_rx_symbols * 48 + rxo_data[7:2] < 192) begin
                got[n_rx_symbols * 48 + rxo_data[7:2]] = rxo_data[1:0];
                seen[n_rx_symbols * 48 + rxo_data[7:2]] = 1'b1;
            end
        end
        if (txo_valid) begin
            if (!selfcheck) $fwrite(out_fd, "%0d %0d\n", $signed(txo_data[15:0]), $signed(txo_data[31:16]));
            else if (n_out < 400) tx_mem[n_out] = txo_data;
            n_out = n_out + 1;
            if (txo_last) n_tx_symbols = n_tx_symbols + 1;
        end
        if (rxo_valid && !selfcheck) begin
            if (MODULATION != 0)
                $fwrite(out_fd, "%0d %0d\n", rxo_data[13:8], rxo_data[3:0]);
            else
                $fwrite(out_fd, "%0d %0d\n", rxo_data[7:2], rxo_data[1:0]);
            n_out = n_out + 1;
        end
        if (rxo_valid && rxo_last) n_rx_symbols = n_rx_symbols + 1;
    end

    task automatic send_group(input [7:0] value);
        begin
            tx_data <= value;
            tx_valid <= 1'b1;
            @(posedge clk);
            while (!tx_ready) @(posedge clk);
            tx_valid <= 1'b0;
        end
    endtask

    task automatic run_selfcheck;
        reg [5:0] d;
        begin
            seen = 0;
            for (k = 0; k < 48; k = k + 1) begin                  // training symbol (train_bits())
                d = k;
                send_group({6'd0, d[0] ^ d[3], d[1] ^ d[2] ^ d[4]});
            end
            for (k = 0; k < 192; k = k + 1) begin                 // 4 data symbols
                sent[k] = $random(seed);
                send_group({6'd0, sent[k]});
            end
            while (n_out < 400 && idle < 40000) begin @(posedge clk); idle = idle + 1; end
            for (k = 0; k < 400; k = k + 1) begin
                rx_data <= tx_mem[k];
                rx_last <= ((k % 80) == 79);
                rx_valid <= 1'b1;
                @(posedge clk);
                while (!rx_ready) @(posedge clk);
                rx_valid <= 1'b0;
                rx_last <= 1'b0;
                repeat (11) @(posedge clk);
            end
            idle = 0;
            while (n_rx_symbols < 4 && idle < 40000) begin @(posedge clk); idle = idle + 1; end
            for (k = 0; k < 192; k = k + 1)
                if (!seen[k] || got[k] !== sent[k]) errors = errors + 1;
            if (n_out == 400 && n_rx_symbols == 4 && errors == 0 && !dut.tx_frame_error_sticky && !dut.rx_frame_error_sticky)
                $display("PASS tb_ofdm_modem_file: 5 symbols out, 4 data symbols back, 192 bit pairs right");
            else begin
                $display("FAIL tb_ofdm_modem_file: tx samples %0d, rx symbols %0d, %0d wrong bit pairs", n_out, n_rx_symbols, errors);
                $fatal(1);
            end
        end
    endtask

    initial begin
        if (!$value$plusargs("OUT=%s", out_name)) begin
            selfcheck = 1'b1;
            repeat (5) @(posedge clk);
            resetn = 1'b1;
            repeat (5) @(posedge clk);
            run_selfcheck();
            $finish;
        end
        out_fd = $fopen(out_name, "w");
        repeat (5) @(posedge clk);
        resetn = 1'b1;
        repeat (5) @(posedge clk);
        if (MODE == 0) begin
            if (!$value$plusargs("BITS=%s", in_name)) begin $display("FAIL: +BITS=<file> missing"); $finish; end
            in_fd = $fopen(in_name, "r");
            r = $fscanf(in_fd, "%h\n", v);
            while (r == 1) begin
                tx_data <= v[7:0];
                tx_valid <= 1'b1;
                @(posedge clk);
                while (!tx_ready) @(posedge clk);
                n_in = n_in + 1;
                r = $fscanf(in_fd, "%h\n", v);
            end
            tx_valid <= 1'b0;
            // wait until every symbol has left the transmitter
            while (n_tx_symbols < n_in / 48 && idle < 20000) begin
                @(posedge clk);
                idle = idle + 1;
            end
        end else begin
            if (!$value$plusargs("IQ=%s", in_name)) begin $display("FAIL: +IQ=<file> missing"); $finish; end
            in_fd = $fopen(in_name, "r");
            r = $fscanf(in_fd, "%d %d\n", re, im);
            while (r == 2) begin
                rx_data <= {im[15:0], re[15:0]};
                rx_last <= ((n_in % 80) == 79);
                rx_valid <= 1'b1;
                @(posedge clk);
                while (!rx_ready) @(posedge clk);
                n_in = n_in + 1;
                r = $fscanf(in_fd, "%d %d\n", re, im);
            end
            rx_valid <= 1'b0;
            rx_last <= 1'b0;
            while (n_rx_symbols < n_in / 80 - CE_TRAIN_SYMBOLS && idle < 50000) begin
                @(posedge clk);
                idle = idle + 1;
            end
            repeat (200) @(posedge clk);
        end
        $fclose(out_fd);
        $display("RESULT mode=%0d inputs=%0d outputs=%0d tx_symbols=%0d rx_symbols=%0d tx_frame_error=%0d rx_frame_error=%0d trained=%0d cfo_theta=%0d",
                 MODE, n_in, n_out, n_tx_symbols, n_rx_symbols, dut.tx_frame_error_sticky, dut.rx_frame_error_sticky,
                 dut.ce_trained, $signed(dut.cfo_theta));
        $finish;
    end
endmodule
