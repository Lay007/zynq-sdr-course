// Scoreboard uses only accepted transactions. Stimulus changes on falling edges;
// checks on rising edges observe pre-NBA values, as in the Lab 5.4 contract.
`timescale 1ns/1ps
module tb_axis_diagnostic;
reg clk = 0;
always #5 clk = ~clk;
reg resetn = 0;
reg s_valid = 0, s_last = 0, m_ready = 0;
reg [31:0] s_data = 0;
wire s_ready, m_valid, m_last;
wire [31:0] m_data;
integer cycle = 0, sent = 0, received = 0, epoch = 0;
integer total_stalls = 0, total_bubbles = 0, total_simultaneous = 0;
integer reset_edges = 0;
reg [31:0] queue_data [0:127];
reg queue_last [0:127];
reg held = 0;
reg input_accepted = 0;
reg [31:0] held_data;
reg held_last;

axis_iq_passthrough dut (
    .aclk(clk), .aresetn(resetn),
    .s_axis_tvalid(s_valid), .s_axis_tready(s_ready),
    .s_axis_tdata(s_data), .s_axis_tlast(s_last),
    .m_axis_tvalid(m_valid), .m_axis_tready(m_ready),
    .m_axis_tdata(m_data), .m_axis_tlast(m_last)
);

always @(negedge clk) begin
    if (!resetn) begin
        s_valid = 0;
        s_last = 0;
        m_ready = 0;
    end else begin
        // sent advances only on an accepted input, so a stalled source holds
        // its data and valid even when the bubble schedule would say otherwise.
        if (!s_valid || input_accepted) begin
            s_valid = (sent < 64) && (cycle % 7 != 2) && (cycle % 7 != 3);
            s_data = (32'h80107ff0 ^ (sent * 32'h1020301)) + epoch;
            s_last = (sent % 8 == 7);
        end
        m_ready = (cycle % 11 > 3);
        if (epoch == 0 && cycle >= 15) m_ready = 0;
    end
end

always @(posedge clk) begin
    if (!resetn) begin
        if (reset_edges > 0 && m_valid !== 0)
            $fatal(1, "DIAGNOSTIC_FAIL: reset did not clear output valid");
        reset_edges = reset_edges + 1;
        cycle = 0;
        sent = 0;
        received = 0;
        held = 0;
        input_accepted = 0;
    end else begin
        reset_edges = 0;
        cycle = cycle + 1;
        input_accepted = s_valid && s_ready;
        if (held && (m_valid !== 1 || m_data !== held_data || m_last !== held_last))
            $fatal(1, "DIAGNOSTIC_FAIL: stalled output changed at cycle %0d", cycle);
        held = m_valid && !m_ready;
        held_data = m_data;
        held_last = m_last;
        if (held) total_stalls = total_stalls + 1;
        if (!s_valid) total_bubbles = total_bubbles + 1;
        if (m_valid && m_ready) begin
            if (received >= sent)
                $fatal(1, "DIAGNOSTIC_FAIL: output without accepted input (duplicate), cycle %0d", cycle);
            if (m_data !== queue_data[received] || m_last !== queue_last[received])
                $fatal(1, "DIAGNOSTIC_FAIL: sample order/data/last mismatch at output %0d cycle %0d", received, cycle);
            received = received + 1;
        end
        if (s_valid && s_ready) begin
            if (sent >= 64) $fatal(1, "DIAGNOSTIC_FAIL: unexpected input count");
            queue_data[sent] = s_data;
            queue_last[sent] = s_last;
            sent = sent + 1;
            if (m_valid && m_ready) total_simultaneous = total_simultaneous + 1;
        end
    end
end

initial begin
    // Offset reset transitions from both sampling and driving edges.
    repeat (3) @(negedge clk);
    #1 resetn = 1;
    wait (cycle == 20);
    @(negedge clk);
    #1;
    if (!(m_valid && !m_ready))
        $fatal(1, "STIMULUS_ERROR: reset must interrupt a pending output");
    resetn = 0;
    repeat (3) @(negedge clk);
    #1;
    epoch = 1;
    resetn = 1;
    repeat (200) @(negedge clk);
    #1;
    if (sent != 64 || received != 64)
        $fatal(1, "DIAGNOSTIC_FAIL: missing transfers sent=%0d received=%0d", sent, received);
    if (total_stalls == 0 || total_bubbles == 0 || total_simultaneous == 0)
        $fatal(1, "STIMULUS_ERROR: incomplete handshake coverage");
    $display("DIAGNOSTIC_PASS: received=%0d stalls=%0d bubbles=%0d simultaneous=%0d; reset flushed pending output",
             received, total_stalls, total_bubbles, total_simultaneous);
    $finish;
end

initial begin
    #10000;
    $fatal(1, "DIAGNOSTIC_FAIL: transfer timeout");
end
endmodule
