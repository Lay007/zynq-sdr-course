// Self-checking async-FIFO CDC test: write a ramp on wr_clk, read on a different
// rd_clk, verify samples come out in order with no loss/dup (rates matched).
`timescale 1ns/1ps

module tb_bridge_rx_lclk_fifo;

localparam integer W = 16;
localparam integer N = 500;

reg wr_clk = 0, rd_clk = 0, wr_rst = 1, rd_rst = 1;
reg wr_en = 0;
reg signed [W-1:0] wr_i = 0, wr_q = 0;
wire rd_valid;
wire signed [W-1:0] rd_i, rd_q;

integer wsent = 0, rgot = 0, errors = 0;

bridge_rx_lclk_fifo #(.W(W), .AW(5)) dut (
    .wr_clk(wr_clk), .wr_rst(wr_rst), .wr_en(wr_en), .wr_i(wr_i), .wr_q(wr_q),
    .rd_clk(rd_clk), .rd_rst(rd_rst), .rd_valid(rd_valid), .rd_i(rd_i), .rd_q(rd_q)
);

// wr ~ 27 MHz, rd ~ 25 MHz (rd slightly slower so FIFO never starves; both near sample rate)
always #18 wr_clk = ~wr_clk;
always #20 rd_clk = ~rd_clk;

// write a ramp: one sample every other wr_clk (mimics adc_valid at the sample rate)
reg phase = 0;
always @(posedge wr_clk) begin
    if (wr_rst) begin wr_en <= 0; phase <= 0; end
    else begin
        phase <= ~phase;
        wr_en <= 1'b0;
        if (phase && wsent < N) begin
            wr_en <= 1'b1;
            wr_i  <= wsent[W-1:0];
            wr_q  <= (-wsent) & {W{1'b1}};
            wsent <= wsent + 1;
        end
    end
end

// read side: check ordering
always @(posedge rd_clk) begin
    if (!rd_rst && rd_valid) begin
        if (rd_i !== rgot[W-1:0]) begin
            $display("FAIL @%0d: rd_i=%0d expected=%0d", rgot, rd_i, rgot[W-1:0]);
            errors = errors + 1;
        end
        rgot = rgot + 1;
    end
end

initial begin
    repeat (5) @(posedge wr_clk); wr_rst = 0;
    repeat (5) @(posedge rd_clk); rd_rst = 0;
    // run long enough to drain N samples
    repeat (4000) @(posedge rd_clk);
    if (rgot < N) begin
        $display("FAIL: only read %0d of %0d samples", rgot, N);
        $fatal(1);
    end
    if (errors != 0) begin
        $display("FAIL: %0d ordering errors", errors);
        $fatal(1);
    end
    $display("PASS: bridge_rx_lclk_fifo crossed %0d samples in order across async clocks", rgot);
    $finish;
end

endmodule
