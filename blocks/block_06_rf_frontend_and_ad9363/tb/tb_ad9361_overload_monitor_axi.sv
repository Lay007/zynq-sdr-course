// Deterministic simulation for rising edges, sticky bits, timestamps and AXI-Lite.
module tb_ad9361_overload_monitor_axi;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;
    reg [7:0] pins = 0;
    reg [7:0] awaddr = 0, araddr = 0;
    reg [2:0] awprot = 0, arprot = 0;
    reg awvalid = 0, wvalid = 0, bready = 0, arvalid = 0, rready = 0;
    reg [31:0] wdata = 0;
    reg [3:0] wstrb = 0;
    wire awready, wready, bvalid, arready, rvalid;
    wire [1:0] bresp, rresp;
    wire [31:0] rdata;
    reg [31:0] got;

    ad9361_overload_monitor_axi dut (
        .clk(clk), .rst_n(rst_n), .ctrl_out_async(pins),
        .s_axi_awaddr(awaddr), .s_axi_awprot(awprot),
        .s_axi_awvalid(awvalid), .s_axi_awready(awready),
        .s_axi_wdata(wdata), .s_axi_wstrb(wstrb),
        .s_axi_wvalid(wvalid), .s_axi_wready(wready),
        .s_axi_bresp(bresp), .s_axi_bvalid(bvalid), .s_axi_bready(bready),
        .s_axi_araddr(araddr), .s_axi_arprot(arprot),
        .s_axi_arvalid(arvalid), .s_axi_arready(arready),
        .s_axi_rdata(rdata), .s_axi_rresp(rresp),
        .s_axi_rvalid(rvalid), .s_axi_rready(rready)
    );

    task automatic rd(input [7:0] addr, output [31:0] value);
        begin
            @(negedge clk);
            araddr = addr; arvalid = 1'b1; rready = 1'b0;
            do @(posedge clk); while (!arready);
            @(negedge clk);
            arvalid = 1'b0; rready = 1'b1;
            do @(posedge clk); while (!rvalid);
            value = rdata;
            @(negedge clk);
            rready = 1'b0;
        end
    endtask

    task automatic wr_clear;
        begin
            @(negedge clk);
            awaddr = 8'h08; awvalid = 1'b1;
            do @(posedge clk); while (!awready);
            @(negedge clk);
            awvalid = 1'b0;
            // Exercise W after AW rather than simultaneous acceptance.
            wdata = 32'h1; wstrb = 4'hF; wvalid = 1'b1;
            do @(posedge clk); while (!wready);
            @(negedge clk);
            wvalid = 1'b0; bready = 1'b1;
            do @(posedge clk); while (!bvalid);
            if (bresp !== 2'b00) $fatal(1, "AXI write error");
            @(negedge clk);
            bready = 1'b0;
        end
    endtask

    initial begin
        repeat (4) @(negedge clk);
        rst_n = 1;
        repeat (4) @(negedge clk);
        // CTRL_OUT6: large LMT; CTRL_OUT5: large ADC.
        pins[6] = 1;
        repeat (6) @(negedge clk);
        pins[5] = 1;
        repeat (6) @(negedge clk);
        pins[6] = 0;
        pins[5] = 0;
        repeat (6) @(negedge clk);
        rd(8'h00, got);
        if (got[7:0] !== 8'h60) $fatal(1, "sticky bits: %h", got);
        rd(8'h38, got); // count bit 6 = 0x20 + 6*4
        if (got !== 1) $fatal(1, "LMT count: %d", got);
        rd(8'h34, got); // count bit 5
        if (got !== 1) $fatal(1, "ADC count: %d", got);
        rd(8'h58, got); // last tick for bit 6
        if (got === 0) $fatal(1, "missing timestamp");
        wr_clear();
        repeat (3) @(negedge clk);
        rd(8'h00, got);
        if (got !== 0) $fatal(1, "sticky clear");
        rd(8'h38, got);
        if (got !== 0) $fatal(1, "counter clear");
        pins[6] = 1;
        repeat (6) @(negedge clk);
        rd(8'h38, got);
        if (got !== 1) $fatal(1, "re-arm after clear");
        $display("PASS: Lab 6.12 AXI-Lite overload monitor");
        $finish;
    end
    initial begin
        #100000;
        $fatal(1, "timeout");
    end
endmodule
