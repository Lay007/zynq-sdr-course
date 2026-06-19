// Lab 5.11 - self-checking AXI-Lite wrapper testbench
//
// Programs the deterministic BPSK BER top-level through AXI-Lite registers,
// loops TX samples back into RX samples, and verifies the register contract.

`timescale 1ns/1ps

module tb_bpsk_zynq_ber_axi_lite;

localparam integer W = 16;
localparam integer INDEX_W = 16;
localparam integer AXI_ADDR_W = 6;
localparam integer AXI_DATA_W = 32;
localparam integer FLUSH_SYMBOLS = 16;
localparam integer CLK_PERIOD_NS = 10;
localparam integer MAX_POLL_READS = 4096;
localparam [AXI_ADDR_W-1:0] REG_CONTROL_STATUS = 6'h00;
localparam [AXI_ADDR_W-1:0] REG_FRAME_BIT_COUNT = 6'h04;
localparam [AXI_ADDR_W-1:0] REG_PREAMBLE_COUNT = 6'h08;
localparam [AXI_ADDR_W-1:0] REG_START_OFFSET = 6'h0C;
localparam [AXI_ADDR_W-1:0] REG_RECEIVED_BITS = 6'h10;
localparam [AXI_ADDR_W-1:0] REG_TOTAL_ERRORS = 6'h14;
localparam [AXI_ADDR_W-1:0] REG_PAYLOAD_ERRORS = 6'h18;
localparam [AXI_ADDR_W-1:0] REG_ID = 6'h1C;
localparam [AXI_DATA_W-1:0] CORE_ID = 32'h4250534B;

reg clk = 1'b0;
reg aresetn = 1'b0;
reg [AXI_ADDR_W-1:0] s_axi_awaddr = {AXI_ADDR_W{1'b0}};
reg s_axi_awvalid = 1'b0;
wire s_axi_awready;
reg [AXI_DATA_W-1:0] s_axi_wdata = {AXI_DATA_W{1'b0}};
reg [(AXI_DATA_W/8)-1:0] s_axi_wstrb = {(AXI_DATA_W/8){1'b0}};
reg s_axi_wvalid = 1'b0;
wire s_axi_wready;
wire [1:0] s_axi_bresp;
wire s_axi_bvalid;
reg s_axi_bready = 1'b0;
reg [AXI_ADDR_W-1:0] s_axi_araddr = {AXI_ADDR_W{1'b0}};
reg s_axi_arvalid = 1'b0;
wire s_axi_arready;
wire [AXI_DATA_W-1:0] s_axi_rdata;
wire [1:0] s_axi_rresp;
wire s_axi_rvalid;
reg s_axi_rready = 1'b0;
wire tx_valid;
wire signed [W-1:0] tx_i;
wire signed [W-1:0] tx_q;

integer wait_reads;
integer meta_fd;
integer scan_count;
integer tmp_start_offset;
integer tmp_sps;
integer tmp_expected_bits;
integer tmp_preamble_count;
integer tmp_flush_symbols;
reg [1023:0] line;
reg [AXI_DATA_W-1:0] readback_word = {AXI_DATA_W{1'b0}};
reg [INDEX_W-1:0] frame_bit_count_cfg = {INDEX_W{1'b0}};
reg [INDEX_W-1:0] preamble_count_cfg = {INDEX_W{1'b0}};
reg [INDEX_W-1:0] start_offset_cfg = {INDEX_W{1'b0}};
reg saw_busy = 1'b0;
reg saw_tx_valid = 1'b0;
reg done_seen = 1'b0;

bpsk_zynq_ber_axi_lite #(
    .W(W),
    .SPS(8),
    .INDEX_W(INDEX_W),
    .MAX_FRAME_BITS(512),
    .PHASE_W(3),
    .FLUSH_SYMBOLS(FLUSH_SYMBOLS),
    .AXI_ADDR_W(AXI_ADDR_W),
    .AXI_DATA_W(AXI_DATA_W)
) dut (
    .s_axi_aclk(clk),
    .s_axi_aresetn(aresetn),
    .s_axi_awaddr(s_axi_awaddr),
    .s_axi_awvalid(s_axi_awvalid),
    .s_axi_awready(s_axi_awready),
    .s_axi_wdata(s_axi_wdata),
    .s_axi_wstrb(s_axi_wstrb),
    .s_axi_wvalid(s_axi_wvalid),
    .s_axi_wready(s_axi_wready),
    .s_axi_bresp(s_axi_bresp),
    .s_axi_bvalid(s_axi_bvalid),
    .s_axi_bready(s_axi_bready),
    .s_axi_araddr(s_axi_araddr),
    .s_axi_arvalid(s_axi_arvalid),
    .s_axi_arready(s_axi_arready),
    .s_axi_rdata(s_axi_rdata),
    .s_axi_rresp(s_axi_rresp),
    .s_axi_rvalid(s_axi_rvalid),
    .s_axi_rready(s_axi_rready),
    .tx_valid(tx_valid),
    .tx_i(tx_i),
    .tx_q(tx_q),
    .rx_valid(tx_valid),
    .rx_i(tx_i),
    .rx_q(tx_q)
);

always #(CLK_PERIOD_NS/2) clk = ~clk;

task read_meta;
    input [1023:0] meta_path;
    begin
        meta_fd = $fopen(meta_path, "r");
        if (meta_fd == 0) begin
            $display("ERROR: cannot open metadata file");
            $fatal(1);
        end

        scan_count = $fgets(line, meta_fd);
        scan_count = $fscanf(
            meta_fd,
            "%d %d %d %d %d\n",
            tmp_start_offset,
            tmp_sps,
            tmp_expected_bits,
            tmp_preamble_count,
            tmp_flush_symbols
        );
        if (scan_count != 5) begin
            $display("ERROR: failed to parse metadata");
            $fatal(1);
        end
        if (tmp_sps != 8) begin
            $display("ERROR: expected SPS=8, got %0d", tmp_sps);
            $fatal(1);
        end
        if (tmp_flush_symbols != FLUSH_SYMBOLS) begin
            $display("ERROR: expected FLUSH_SYMBOLS=%0d, got %0d", FLUSH_SYMBOLS, tmp_flush_symbols);
            $fatal(1);
        end

        frame_bit_count_cfg = tmp_expected_bits[INDEX_W-1:0];
        preamble_count_cfg = tmp_preamble_count[INDEX_W-1:0];
        start_offset_cfg = tmp_start_offset[INDEX_W-1:0];

        $fclose(meta_fd);
    end
endtask

task axi_write;
    input [AXI_ADDR_W-1:0] addr;
    input [AXI_DATA_W-1:0] data;
    reg aw_done;
    reg w_done;
    begin
        aw_done = 1'b0;
        w_done = 1'b0;

        @(negedge clk);
        s_axi_awaddr = addr;
        s_axi_awvalid = 1'b1;
        s_axi_wdata = data;
        s_axi_wstrb = {(AXI_DATA_W/8){1'b1}};
        s_axi_wvalid = 1'b1;
        s_axi_bready = 1'b1;

        while (!aw_done || !w_done) begin
            @(posedge clk);
            if (s_axi_awvalid && s_axi_awready) begin
                aw_done = 1'b1;
            end
            if (s_axi_wvalid && s_axi_wready) begin
                w_done = 1'b1;
            end
            @(negedge clk);
            if (aw_done) begin
                s_axi_awvalid = 1'b0;
            end
            if (w_done) begin
                s_axi_wvalid = 1'b0;
            end
        end

        while (!s_axi_bvalid) begin
            @(posedge clk);
        end

        if (s_axi_bresp != 2'b00) begin
            $display("ERROR: AXI write response was not OKAY");
            $fatal(1);
        end

        @(negedge clk);
        s_axi_bready = 1'b0;
        s_axi_awaddr = {AXI_ADDR_W{1'b0}};
        s_axi_wdata = {AXI_DATA_W{1'b0}};
        s_axi_wstrb = {(AXI_DATA_W/8){1'b0}};
    end
endtask

task axi_read;
    input [AXI_ADDR_W-1:0] addr;
    output [AXI_DATA_W-1:0] data;
    reg ar_done;
    begin
        ar_done = 1'b0;

        @(negedge clk);
        s_axi_araddr = addr;
        s_axi_arvalid = 1'b1;
        s_axi_rready = 1'b1;

        while (!ar_done) begin
            @(posedge clk);
            if (s_axi_arvalid && s_axi_arready) begin
                ar_done = 1'b1;
            end
            @(negedge clk);
            if (ar_done) begin
                s_axi_arvalid = 1'b0;
            end
        end

        while (!s_axi_rvalid) begin
            @(posedge clk);
        end

        if (s_axi_rresp != 2'b00) begin
            $display("ERROR: AXI read response was not OKAY");
            $fatal(1);
        end

        data = s_axi_rdata;

        @(negedge clk);
        s_axi_rready = 1'b0;
        s_axi_araddr = {AXI_ADDR_W{1'b0}};
    end
endtask

initial begin
    read_meta("blocks/block_05_fpga_hdl_flow/tb/bpsk_framed_loopback_meta.txt");

    $dumpfile("blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_zynq_ber_axi_lite.vcd");
    $dumpvars(0, tb_bpsk_zynq_ber_axi_lite);

    repeat (3) @(posedge clk);
    @(negedge clk);
    aresetn = 1'b1;

    axi_read(REG_ID, readback_word);
    if (readback_word !== CORE_ID) begin
        $display("ERROR: ID register mismatch: got 0x%08x expected 0x%08x", readback_word, CORE_ID);
        $fatal(1);
    end

    axi_read(REG_CONTROL_STATUS, readback_word);
    if (readback_word[2:0] !== 3'b000) begin
        $display("ERROR: control/status register not reset to zero: 0x%08x", readback_word);
        $fatal(1);
    end

    axi_write(REG_FRAME_BIT_COUNT, {{(AXI_DATA_W-INDEX_W){1'b0}}, frame_bit_count_cfg});
    axi_write(REG_PREAMBLE_COUNT, {{(AXI_DATA_W-INDEX_W){1'b0}}, preamble_count_cfg});
    axi_write(REG_START_OFFSET, {{(AXI_DATA_W-INDEX_W){1'b0}}, start_offset_cfg});

    axi_read(REG_FRAME_BIT_COUNT, readback_word);
    if (readback_word[INDEX_W-1:0] !== frame_bit_count_cfg) begin
        $display("ERROR: frame_bit_count readback mismatch");
        $fatal(1);
    end

    axi_read(REG_PREAMBLE_COUNT, readback_word);
    if (readback_word[INDEX_W-1:0] !== preamble_count_cfg) begin
        $display("ERROR: preamble_count readback mismatch");
        $fatal(1);
    end

    axi_read(REG_START_OFFSET, readback_word);
    if (readback_word[INDEX_W-1:0] !== start_offset_cfg) begin
        $display("ERROR: start_offset readback mismatch");
        $fatal(1);
    end

    axi_write(REG_CONTROL_STATUS, 32'h0000_0001);

    done_seen = 1'b0;
    for (wait_reads = 0; wait_reads < MAX_POLL_READS; wait_reads = wait_reads + 1) begin
        axi_read(REG_CONTROL_STATUS, readback_word);
        if (readback_word[1]) begin
            saw_busy = 1'b1;
        end
        if (readback_word[2]) begin
            done_seen = 1'b1;
            wait_reads = MAX_POLL_READS;
        end
    end

    if (!done_seen) begin
        $display("ERROR: done bit was never observed during the AXI-Lite controlled run");
        $fatal(1);
    end

    if (!saw_busy) begin
        $display("ERROR: busy bit was never observed during the AXI-Lite controlled run");
        $fatal(1);
    end

    axi_read(REG_CONTROL_STATUS, readback_word);
    if (!readback_word[2] || readback_word[1]) begin
        $display("ERROR: expected done=1 and busy=0 after completion, got 0x%08x", readback_word);
        $fatal(1);
    end

    axi_read(REG_RECEIVED_BITS, readback_word);
    if (readback_word[INDEX_W-1:0] !== frame_bit_count_cfg) begin
        $display("ERROR: received_bits mismatch");
        $fatal(1);
    end

    axi_read(REG_TOTAL_ERRORS, readback_word);
    if (readback_word[INDEX_W-1:0] !== 0) begin
        $display("ERROR: total_errors was not zero");
        $fatal(1);
    end

    axi_read(REG_PAYLOAD_ERRORS, readback_word);
    if (readback_word[INDEX_W-1:0] !== 0) begin
        $display("ERROR: payload_errors was not zero");
        $fatal(1);
    end

    axi_write(REG_CONTROL_STATUS, 32'h0000_0004);
    axi_read(REG_CONTROL_STATUS, readback_word);
    if (readback_word[2] !== 1'b0) begin
        $display("ERROR: done sticky bit did not clear");
        $fatal(1);
    end

    if (!saw_tx_valid) begin
        $display("ERROR: wrapper never emitted TX samples");
        $fatal(1);
    end

    repeat (3) @(posedge clk);
    $display("PASS: bpsk_zynq_ber_axi_lite completed without errors");
    $finish;
end

always @(posedge clk) begin
    if (tx_valid) begin
        saw_tx_valid <= 1'b1;
    end
end

endmodule
