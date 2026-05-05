// Lab 5.4 — self-checking testbench for axis_iq_passthrough
//
// Verifies basic AXI-Stream behaviour:
// - reset clears output valid
// - tvalid/tready handshake transfers samples
// - backpressure stalls output without data loss
// - tlast is preserved

`timescale 1ns/1ps

module tb_axis_iq_passthrough;

localparam integer TDW = 32;
localparam integer NUM_SAMPLES = 6;
localparam integer CLK_PERIOD_NS = 10;

reg aclk = 1'b0;
reg aresetn = 1'b0;

reg                 s_axis_tvalid = 1'b0;
wire                s_axis_tready;
reg  [TDW-1:0]      s_axis_tdata = 0;
reg                 s_axis_tlast = 1'b0;

wire                m_axis_tvalid;
reg                 m_axis_tready = 1'b1;
wire [TDW-1:0]      m_axis_tdata;
wire                m_axis_tlast;

reg [TDW-1:0] samples [0:NUM_SAMPLES-1];
reg          lasts   [0:NUM_SAMPLES-1];

integer send_idx = 0;
integer recv_idx = 0;
integer errors = 0;
integer cycle_count = 0;

axis_iq_passthrough dut (
    .aclk(aclk),
    .aresetn(aresetn),
    .s_axis_tvalid(s_axis_tvalid),
    .s_axis_tready(s_axis_tready),
    .s_axis_tdata(s_axis_tdata),
    .s_axis_tlast(s_axis_tlast),
    .m_axis_tvalid(m_axis_tvalid),
    .m_axis_tready(m_axis_tready),
    .m_axis_tdata(m_axis_tdata),
    .m_axis_tlast(m_axis_tlast)
);

always #(CLK_PERIOD_NS/2) aclk = ~aclk;

initial begin
    samples[0] = {16'sd0,      16'sd32767};
    samples[1] = {16'sd32767,  16'sd0};
    samples[2] = {-16'sd1,     16'sd1234};
    samples[3] = {16'sd3333,  -16'sd2222};
    samples[4] = {-16'sd12000, 16'sd8000};
    samples[5] = {16'sd42,    -16'sd42};

    lasts[0] = 1'b0;
    lasts[1] = 1'b0;
    lasts[2] = 1'b0;
    lasts[3] = 1'b0;
    lasts[4] = 1'b0;
    lasts[5] = 1'b1;
end

initial begin
    $dumpfile("tb_axis_iq_passthrough.vcd");
    $dumpvars(0, tb_axis_iq_passthrough);

    repeat (4) @(posedge aclk);
    @(negedge aclk);
    aresetn = 1'b1;

    while (recv_idx < NUM_SAMPLES && cycle_count < 100) begin
        @(negedge aclk);
        cycle_count = cycle_count + 1;

        // Deterministic backpressure pattern.
        if (cycle_count == 5 || cycle_count == 6 || cycle_count == 12)
            m_axis_tready = 1'b0;
        else
            m_axis_tready = 1'b1;

        if (send_idx < NUM_SAMPLES) begin
            s_axis_tvalid = 1'b1;
            s_axis_tdata = samples[send_idx];
            s_axis_tlast = lasts[send_idx];
            if (s_axis_tready) begin
                send_idx = send_idx + 1;
            end
        end else begin
            s_axis_tvalid = 1'b0;
            s_axis_tdata = 0;
            s_axis_tlast = 1'b0;
        end
    end

    repeat (4) @(posedge aclk);

    if (recv_idx != NUM_SAMPLES) begin
        $display("ERROR: received %0d samples, expected %0d", recv_idx, NUM_SAMPLES);
        errors = errors + 1;
    end

    if (errors == 0) begin
        $display("PASS: axis_iq_passthrough test completed without errors");
        $finish;
    end else begin
        $display("FAIL: axis_iq_passthrough test completed with %0d errors", errors);
        $fatal(1);
    end
end

always @(posedge aclk) begin
    if (!aresetn) begin
        if (m_axis_tvalid !== 1'b0) begin
            $display("ERROR at %0t: m_axis_tvalid must be 0 during reset", $time);
            errors = errors + 1;
        end
    end else begin
        if (m_axis_tvalid && m_axis_tready) begin
            if (recv_idx >= NUM_SAMPLES) begin
                $display("ERROR at %0t: unexpected extra output sample", $time);
                errors = errors + 1;
            end else begin
                if (m_axis_tdata !== samples[recv_idx]) begin
                    $display("ERROR at %0t: data mismatch idx=%0d got=0x%08x expected=0x%08x",
                             $time, recv_idx, m_axis_tdata, samples[recv_idx]);
                    errors = errors + 1;
                end
                if (m_axis_tlast !== lasts[recv_idx]) begin
                    $display("ERROR at %0t: tlast mismatch idx=%0d got=%0b expected=%0b",
                             $time, recv_idx, m_axis_tlast, lasts[recv_idx]);
                    errors = errors + 1;
                end
                recv_idx = recv_idx + 1;
            end
        end
    end
end

endmodule
