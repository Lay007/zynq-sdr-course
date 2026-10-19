`timescale 1ns/1ps

// Issue #48, stage 4b: ofdm_radio_core as on one board with TX1 cabled to RX1. 100 MHz control
// clock, a sample clock at 2.083 MHz with one DAC request per clock (one sample per request, as
// course_dac_fifo_source_mux writes the DAC FIFO), and a channel from the DAC words to the ADC: the
// mux's selection, a delay, DC, a little noise and 12 bits. Through AXI4-Lite the bench writes the
// TX buffer, arms the receiver, starts the transmitter and reads the RX buffer back, twice, with new
// data and a new RX_ARM the second time. It checks every bit, one frame found per arm, no TX
// underflow, no RX overflow, and reads the modem's CE_TRAINED through the core's window.
module tb_ofdm_radio_core;
    localparam integer SYMBOLS = 4;
    localparam integer WORDS = 3 * SYMBOLS;
    localparam integer CHANNEL_DELAY = 37;

    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg sclk = 1'b0;
    always #240 sclk = ~sclk;                // 2.083 MHz
    reg resetn = 1'b0, sresetn = 1'b0;

    reg  [11:0] awaddr = 0, araddr = 0;
    reg         awvalid = 1'b0, wvalid = 1'b0, arvalid = 1'b0;
    reg  [31:0] wdata = 0;
    wire        awready, wready, bvalid, arready, rvalid;
    wire [1:0]  bresp, rresp;
    wire [31:0] rdata;
    wire        tx_select;
    wire [32:0] tx_bus;
    reg  [32:0] rx_bus = 0;

    ofdm_radio_core dut (
        .s_axi_aclk(clk), .s_axi_aresetn(resetn),
        .s_axi_awaddr(awaddr), .s_axi_awvalid(awvalid), .s_axi_awready(awready),
        .s_axi_wdata(wdata), .s_axi_wstrb(4'hF), .s_axi_wvalid(wvalid), .s_axi_wready(wready),
        .s_axi_bresp(bresp), .s_axi_bvalid(bvalid), .s_axi_bready(1'b1),
        .s_axi_araddr(araddr), .s_axi_arvalid(arvalid), .s_axi_arready(arready),
        .s_axi_rdata(rdata), .s_axi_rresp(rresp), .s_axi_rvalid(rvalid), .s_axi_rready(1'b1),
        .sample_clk(sclk), .sample_resetn(sresetn), .fifo_rd_req(1'b1),
        .tx_select(tx_select), .tx_sample_bus(tx_bus), .rx_sample_bus(rx_bus)
    );

    // channel: what the mux writes into the DAC FIFO, delayed, to 12 bits, with DC and noise
    reg signed [15:0] dl_i [0:CHANNEL_DELAY-1];
    reg signed [15:0] dl_q [0:CHANNEL_DELAY-1];
    integer seed = 11, j, n_tx_samples = 0;
    reg signed [15:0] dac_i, dac_q;
    integer ni, nq;
    initial for (j = 0; j < CHANNEL_DELAY; j = j + 1) begin dl_i[j] = 0; dl_q[j] = 0; end
    always @(posedge sclk) begin
        dac_i = (tx_select && tx_bus[32]) ? $signed(tx_bus[31:16]) : 16'sd0;
        dac_q = (tx_select && tx_bus[32]) ? $signed(tx_bus[15:0]) : 16'sd0;
        if (tx_select && tx_bus[32]) n_tx_samples = n_tx_samples + 1;
        for (j = CHANNEL_DELAY - 1; j > 0; j = j - 1) begin dl_i[j] = dl_i[j - 1]; dl_q[j] = dl_q[j - 1]; end
        dl_i[0] = dac_i;
        dl_q[0] = dac_q;
        ni = ($random(seed) % 3);
        nq = ($random(seed) % 3);
        rx_bus <= {1'b1, 16'(($signed(dl_i[CHANNEL_DELAY - 1]) >>> 4) + 5 + ni),
                         16'(($signed(dl_q[CHANNEL_DELAY - 1]) >>> 4) - 3 + nq)};
    end

    task automatic axi_write(input [11:0] a, input [31:0] d);
        begin
            @(posedge clk);
            awaddr <= a; wdata <= d; awvalid <= 1'b1; wvalid <= 1'b1;
            @(posedge clk);
            while (!(awready && wready)) @(posedge clk);
            awvalid <= 1'b0; wvalid <= 1'b0;
            while (!bvalid) @(posedge clk);
        end
    endtask

    task automatic axi_read(input [11:0] a, output [31:0] d);
        begin
            @(posedge clk);
            araddr <= a; arvalid <= 1'b1;
            @(posedge clk);
            while (!arready) @(posedge clk);
            arvalid <= 1'b0;
            while (!rvalid) @(posedge clk);
            d = rdata;
        end
    endtask

    reg [31:0] sent [0:WORDS-1];
    reg [31:0] v;
    integer k, frame, errors = 0, waited;

    task automatic fail(input [8*80-1:0] what);
        begin
            $display("FAIL tb_ofdm_radio_core: %0s", what);
            $display("  tx: state %0d feeder %0d queued %0d played %0d active %0d; rx: armed %0d samples %0d found %0d missed %0d fed %0d symbols %0d",
                     dut.t_state, dut.f_state, dut.tx_samples, n_tx_samples, dut.s_active, dut.rx_armed, dut.rx_samples,
                     dut.fs_found, dut.fs_missed, dut.fed_syms, dut.rx_syms);
            $fatal(1);
        end
    endtask

    initial begin
        repeat (10) @(posedge clk);
        resetn = 1'b1;
        sresetn = 1'b1;
        repeat (10) @(posedge clk);
        axi_read(12'h000, v);
        if (v !== 32'h4F464452) fail("ID");
        axi_write(12'h010, SYMBOLS);
        axi_write(12'h018, 3);                       // the ADC's 12 bits to about the modem's level
        for (frame = 0; frame < 2; frame = frame + 1) begin
            for (k = 0; k < WORDS; k = k + 1) begin
                sent[k] = $random(seed);
                axi_write(12'h400 + 4 * k, sent[k]);
            end
            axi_write(12'h008, 32'h1);               // RX_ARM
            axi_write(12'h008, 32'h2);               // TX_START
            waited = 0;
            v = 0;
            while (!v[4] && waited < 4000) begin     // RX done
                repeat (100) @(posedge clk);
                axi_read(12'h00C, v);
                waited = waited + 1;
            end
            if (!v[4]) fail("no frame decided");
            waited = 0;
            while (v[0] && waited < 1000) begin      // TX busy until the last sample has been played
                repeat (100) @(posedge clk);
                axi_read(12'h00C, v);
                waited = waited + 1;
            end
            if (v[0] || !v[1]) fail("TX did not finish");
            if (v[5] || v[6]) fail("TX underflow or RX overflow");
            for (k = 0; k < WORDS; k = k + 1) begin
                axi_read(12'h800 + 4 * k, v);
                if (v !== sent[k]) begin
                    errors = errors + 1;
                    $display("  frame %0d word %0d: got %08x, sent %08x", frame, k, v, sent[k]);
                end
            end
            axi_read(12'h020, v);
            if (v != 1) fail("frames found != 1");
            axi_read(12'h028, v);
            if (v != 0) fail("frame search FIFO overflow");
            axi_read(12'h130, v);                    // the modem's CE_TRAINED
            if (v != 1) fail("modem not trained once");
            axi_read(12'h030, v);
            $display("frame %0d: %0d samples queued, %0d played; modem CE_TRAINED 1", frame, v, n_tx_samples);
            if (v != 80 * (SYMBOLS + 2)) fail("TX sample count");
            n_tx_samples = 0;
        end
        if (errors != 0) fail("bit errors");
        $display("PASS tb_ofdm_radio_core: 2 frames of %0d data symbols through DAC -> channel -> ADC, %0d bits each right, one frame found per RX_ARM",
                 SYMBOLS, 96 * SYMBOLS);
        $finish;
    end
endmodule
