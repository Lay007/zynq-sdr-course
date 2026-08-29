`timescale 1ns/1ps

module tb_zynq_message_mailbox_axi_lite;

localparam [7:0] REG_ID          = 8'h00;
localparam [7:0] REG_VERSION     = 8'h04;
localparam [7:0] REG_CONTROL     = 8'h08;
localparam [7:0] REG_STATUS      = 8'h0C;
localparam [7:0] REG_TX_SEQUENCE = 8'h10;
localparam [7:0] REG_TX_LENGTH   = 8'h14;
localparam [7:0] REG_TX_DATA0    = 8'h20;
localparam [7:0] REG_RX_SEQUENCE = 8'h60;
localparam [7:0] REG_RX_LENGTH   = 8'h64;
localparam [7:0] REG_RX_META     = 8'h68;
localparam [7:0] REG_RX_DATA0    = 8'h70;

reg clk = 1'b0;
reg resetn = 1'b0;
always #5 clk = ~clk;

reg [7:0] awaddr = 8'd0;
reg awvalid = 1'b0;
wire awready;
reg [31:0] wdata = 32'd0;
reg [3:0] wstrb = 4'd0;
reg wvalid = 1'b0;
wire wready;
wire [1:0] bresp;
wire bvalid;
reg bready = 1'b0;
reg [7:0] araddr = 8'd0;
reg arvalid = 1'b0;
wire arready;
wire [31:0] rdata;
wire [1:0] rresp;
wire rvalid;
reg rready = 1'b0;

integer failures = 0;
reg [31:0] value;

zynq_message_mailbox_axi_lite dut (
    .s_axi_aclk(clk),
    .s_axi_aresetn(resetn),
    .s_axi_awaddr(awaddr),
    .s_axi_awvalid(awvalid),
    .s_axi_awready(awready),
    .s_axi_wdata(wdata),
    .s_axi_wstrb(wstrb),
    .s_axi_wvalid(wvalid),
    .s_axi_wready(wready),
    .s_axi_bresp(bresp),
    .s_axi_bvalid(bvalid),
    .s_axi_bready(bready),
    .s_axi_araddr(araddr),
    .s_axi_arvalid(arvalid),
    .s_axi_arready(arready),
    .s_axi_rdata(rdata),
    .s_axi_rresp(rresp),
    .s_axi_rvalid(rvalid),
    .s_axi_rready(rready)
);

// Keep address and data channels independent, as AXI-Lite permits.
task automatic axi_write;
    input [7:0] addr;
    input [31:0] data;
    input [3:0] strb;
    reg aw_done;
    reg w_done;
    begin
        aw_done = 1'b0;
        w_done = 1'b0;
        @(negedge clk);
        awaddr = addr;
        awvalid = 1'b1;
        wdata = data;
        wstrb = strb;
        wvalid = 1'b1;
        bready = 1'b1;

        while (!(aw_done && w_done)) begin
            @(posedge clk);
            if (!aw_done && awvalid && awready)
                aw_done = 1'b1;
            if (!w_done && wvalid && wready)
                w_done = 1'b1;
            @(negedge clk);
            if (aw_done)
                awvalid = 1'b0;
            if (w_done)
                wvalid = 1'b0;
        end

        while (!bvalid)
            @(posedge clk);
        if (bresp !== 2'b00) begin
            $display("FAIL AXI write response addr=0x%02x bresp=%b", addr, bresp);
            failures = failures + 1;
        end
        @(negedge clk);
        bready = 1'b0;
    end
endtask

task automatic axi_read;
    input [7:0] addr;
    output [31:0] data;
    reg address_done;
    begin
        address_done = 1'b0;
        @(negedge clk);
        araddr = addr;
        arvalid = 1'b1;
        rready = 1'b1;

        while (!address_done) begin
            @(posedge clk);
            if (arvalid && arready)
                address_done = 1'b1;
            @(negedge clk);
            if (address_done)
                arvalid = 1'b0;
        end

        while (!rvalid)
            @(posedge clk);
        data = rdata;
        if (rresp !== 2'b00) begin
            $display("FAIL AXI read response addr=0x%02x rresp=%b", addr, rresp);
            failures = failures + 1;
        end
        @(negedge clk);
        rready = 1'b0;
    end
endtask

task automatic expect32;
    input [8*80-1:0] label;
    input [31:0] actual;
    input [31:0] expected;
    begin
        if (actual !== expected) begin
            $display("FAIL %-60s actual=0x%08x expected=0x%08x", label, actual, expected);
            failures = failures + 1;
        end else begin
            $display("PASS %-60s value=0x%08x", label, actual);
        end
    end
endtask

initial begin
    repeat (3) @(posedge clk);
    @(negedge clk);
    resetn = 1'b1;
    repeat (2) @(posedge clk);

    axi_read(REG_ID, value);
    expect32("mailbox core ID", value, 32'h4D424F58);
    axi_read(REG_VERSION, value);
    expect32("mailbox version", value, 32'h00010000);
    axi_read(REG_STATUS, value);
    expect32("status reset", value, 32'h00000000);

    // Build "ABCD" from two byte-strobed writes.  This makes WSTRB and
    // little-endian packing visible in the first PS/PL exercise.
    axi_write(REG_TX_DATA0, 32'h44430000, 4'b1100);
    axi_write(REG_TX_DATA0, 32'h00004241, 4'b0011);
    axi_read(REG_TX_DATA0, value);
    expect32("WSTRB composes little-endian ABCD", value, 32'h44434241);

    axi_write(REG_TX_SEQUENCE, 32'd17, 4'hF);
    axi_write(REG_TX_LENGTH, 32'd4, 4'hF);
    axi_write(REG_CONTROL, 32'h00000001, 4'h1);

    // By the time the AXI write response completes, the one-cycle PL echo has
    // also committed an RX snapshot.
    axi_read(REG_STATUS, value);
    expect32("TX done plus RX valid after PL echo", value, 32'h00000006);
    axi_read(REG_RX_SEQUENCE, value);
    expect32("RX sequence echoes TX sequence", value, 32'd17);
    axi_read(REG_RX_LENGTH, value);
    expect32("RX length echoes TX length", value, 32'd4);
    axi_read(REG_RX_META, value);
    expect32("valid PL echo marks integrity OK", value, 32'h00000001);
    axi_read(REG_RX_DATA0, value);
    expect32("RX payload echoes ABCD", value, 32'h44434241);

    // An unread RX snapshot must not be torn by a later message.
    axi_write(REG_TX_SEQUENCE, 32'd18, 4'hF);
    axi_write(REG_TX_LENGTH, 32'd6, 4'hF);
    axi_write(REG_TX_DATA0, 32'h6F636573, 4'hF); // "seco" little-endian
    axi_write(REG_CONTROL, 32'h00000001, 4'h1);
    axi_read(REG_STATUS, value);
    expect32("occupied RX mailbox reports overflow", value, 32'h0000000E);
    axi_read(REG_RX_SEQUENCE, value);
    expect32("overflow preserves unread RX sequence", value, 32'd17);
    axi_read(REG_RX_DATA0, value);
    expect32("overflow preserves unread RX payload", value, 32'h44434241);

    axi_write(REG_CONTROL, 32'h00000002, 4'h1);
    axi_read(REG_STATUS, value);
    expect32("RX ACK clears valid and overflow but keeps TX done", value, 32'h00000002);

    // The software helper rejects >64 bytes.  Hardware still defends the
    // register contract: it clamps the visible length and marks frame_error.
    axi_write(REG_TX_SEQUENCE, 32'd19, 4'hF);
    axi_write(REG_TX_LENGTH, 32'd65, 4'hF);
    axi_write(REG_CONTROL, 32'h00000001, 4'h1);
    axi_read(REG_STATUS, value);
    expect32("invalid length still produces inspectable RX snapshot", value, 32'h00000006);
    axi_read(REG_RX_LENGTH, value);
    expect32("invalid length clamps to mailbox capacity", value, 32'd64);
    axi_read(REG_RX_META, value);
    expect32("invalid length is marked frame error", value, 32'h00000002);

    // Synchronous active-low reset discards mailbox state, but the ID/version
    // remain fixed combinational register values after reset is released.
    @(negedge clk);
    resetn = 1'b0;
    repeat (2) @(posedge clk);
    @(negedge clk);
    resetn = 1'b1;
    repeat (2) @(posedge clk);

    axi_read(REG_STATUS, value);
    expect32("reset clears status", value, 32'h00000000);
    axi_read(REG_TX_DATA0, value);
    expect32("reset clears TX payload storage", value, 32'h00000000);
    axi_read(REG_RX_DATA0, value);
    expect32("reset clears RX payload storage", value, 32'h00000000);
    axi_read(REG_ID, value);
    expect32("ID remains readable after reset", value, 32'h4D424F58);

    if (failures == 0) begin
        $display("PASS tb_zynq_message_mailbox_axi_lite");
        $finish;
    end

    $fatal(1, "FAIL tb_zynq_message_mailbox_axi_lite failures=%0d", failures);
end

endmodule
