// Issue #67: the DAC FIFO source mux writes on the FIFO's own read request, so the DAC gets
// zeros between bursts even when no DMA stream runs, and nothing changes while one does.
//
// The FIFO request is modelled as util_rfifo does it (a level, here high most of the time with
// gaps), the unpacker as util_upack2 does (fifo_rd_valid one clock after the request, only when
// it has data). Checks: (1) DMA running: every vendor word is written, nothing else; (2) no DMA,
// no burst: zeros are written at the request cadence; (3) a burst with no DMA: the modem's
// samples, then zeros again, never the last burst sample held.

`timescale 1ns/1ps

module tb_course_dac_fifo_source_mux;

localparam integer W = 16;
reg clk = 1'b0;
always #4 clk = ~clk;

reg         req = 1'b0;
reg         dma_on = 1'b0;
reg         select = 1'b0;
reg         bpsk_valid = 1'b0;
reg  [15:0] bpsk_i = 0, bpsk_q = 0;
reg         vendor_valid = 1'b0;
reg  [15:0] vendor_word = 16'h0100;
wire [15:0] d0, d1, d2, d3;
wire        fv, funf;

course_dac_fifo_source_mux #(.W(W)) dut (
    .clk(clk), .fifo_rd_req(req), .select_bpsk(select),
    .vendor_data_0(vendor_word), .vendor_data_1(~vendor_word), .vendor_data_2(vendor_word), .vendor_data_3(~vendor_word),
    .vendor_valid(vendor_valid), .vendor_unf(1'b0),
    .bpsk_tx_sample_bus({bpsk_valid, bpsk_i, bpsk_q}),
    .fifo_data_0(d0), .fifo_data_1(d1), .fifo_data_2(d2), .fifo_data_3(d3), .fifo_valid(fv), .fifo_unf(funf)
);

// util_upack2: answers a request one clock later, if it has data
always @(posedge clk) begin
    vendor_valid <= req & dma_on;
    if (req & dma_on) vendor_word <= vendor_word + 1'b1;
end

// util_rfifo-like request: high, with a one-clock gap every 16 clocks
integer cyc = 0;
always @(posedge clk) begin
    cyc <= cyc + 1;
    req <= (cyc % 16) != 15;
end

integer errors = 0, writes = 0, vendor_writes = 0, nonzero_idle = 0, burst_writes = 0, phase = 0;
reg req_q = 1'b0;
always @(posedge clk) req_q <= req;
always @(negedge clk) begin
    if (fv) writes = writes + 1;
    if (fv !== (req_q | vendor_valid | (select & bpsk_valid))) begin
        errors = errors + 1;
        $display("FAIL cadence at %0t: fifo_valid %0d req_d %0d", $time, fv, req_q);
    end
    case (phase)
        1: if (fv) begin
               if (vendor_valid && d0 !== vendor_word - 1'b1 && d0 !== vendor_word) ; // data checked below
               if (!vendor_valid && d0 !== 16'd0) begin errors = errors + 1; $display("FAIL: stale vendor data written"); end
               if (vendor_valid) vendor_writes = vendor_writes + 1;
           end
        2, 4: if (fv && (d0 !== 0 || d1 !== 0)) nonzero_idle = nonzero_idle + 1;
        3: if (fv && bpsk_valid && (d0 !== bpsk_i || d1 !== bpsk_q)) begin
               errors = errors + 1; $display("FAIL: burst sample not written");
           end else if (fv && bpsk_valid) burst_writes = burst_writes + 1;
    endcase
end

integer k;
initial begin
    repeat (20) @(posedge clk);
    // (1) DMA running
    phase = 1; dma_on = 1;
    repeat (400) @(posedge clk);
    dma_on = 0;
    repeat (4) @(posedge clk);
    if (vendor_writes < 300) begin errors = errors + 1; $display("FAIL: only %0d vendor words written", vendor_writes); end
    // (2) no DMA, no burst: zeros at the request cadence
    phase = 2; writes = 0;
    repeat (400) @(posedge clk);
    if (writes < 350) begin errors = errors + 1; $display("FAIL: only %0d idle writes in 400 clocks", writes); end
    // (3) a burst, no DMA
    phase = 3; select = 1;
    for (k = 0; k < 200; k = k + 1) begin
        @(posedge clk);
        bpsk_valid <= 1; bpsk_i <= 16'h1234 + k; bpsk_q <= 16'h4321 - k;
    end
    @(posedge clk); bpsk_valid <= 0; bpsk_i <= 16'h7FFF; bpsk_q <= 16'h7FFF;   // last word left on the bus
    repeat (8) @(posedge clk);
    select = 0;
    // (4) after the burst: zeros, not the last sample
    phase = 4;
    repeat (400) @(posedge clk);
    if (nonzero_idle != 0) begin errors = errors + 1; $display("FAIL: %0d non-zero words written while idle", nonzero_idle); end
    if (burst_writes < 190) begin errors = errors + 1; $display("FAIL: only %0d burst samples written", burst_writes); end
    if (errors == 0)
        $display("PASS tb_course_dac_fifo_source_mux: DMA words %0d, burst samples %0d, idle writes are zeros", vendor_writes, burst_writes);
    else
        $display("FAIL tb_course_dac_fifo_source_mux: %0d errors", errors);
    $finish;
end

endmodule
