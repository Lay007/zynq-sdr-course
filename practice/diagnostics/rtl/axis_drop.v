// Intentionally faulty learner fixture: diagnose using accepted transactions.
`timescale 1ns/1ps
module axis_iq_passthrough (
    input wire aclk, aresetn,
    input wire s_axis_tvalid,
    output wire s_axis_tready,
    input wire [31:0] s_axis_tdata,
    input wire s_axis_tlast,
    output reg m_axis_tvalid,
    input wire m_axis_tready,
    output reg [31:0] m_axis_tdata,
    output reg m_axis_tlast
);
assign s_axis_tready = (~m_axis_tvalid) || m_axis_tready;
always @(posedge aclk) begin
    if (!aresetn) begin
        m_axis_tvalid <= 0;
        m_axis_tdata <= 0;
        m_axis_tlast <= 0;
    end else begin
        m_axis_tvalid <= s_axis_tvalid;
        if (s_axis_tvalid) begin
            m_axis_tdata <= s_axis_tdata;
            m_axis_tlast <= s_axis_tlast;
        end
    end
end
endmodule
