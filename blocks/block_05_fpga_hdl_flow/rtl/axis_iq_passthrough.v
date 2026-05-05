// Lab 5.4 — AXI-Stream IQ passthrough wrapper
//
// Educational AXI-Stream style wrapper for complex IQ samples.
// tdata layout:
//   s_axis_tdata[15:0]  = I sample, signed Q1.15
//   s_axis_tdata[31:16] = Q sample, signed Q1.15
//
// This is a one-stage registered pass-through with simple backpressure support.
// It demonstrates tvalid/tready/tdata/tlast behaviour before connecting DSP
// blocks to a Vivado/Zynq streaming design.

`timescale 1ns/1ps

module axis_iq_passthrough #(
    parameter integer W = 16,
    parameter integer TDW = 32
)(
    input  wire                 aclk,
    input  wire                 aresetn,

    input  wire                 s_axis_tvalid,
    output wire                 s_axis_tready,
    input  wire [TDW-1:0]       s_axis_tdata,
    input  wire                 s_axis_tlast,

    output reg                  m_axis_tvalid,
    input  wire                 m_axis_tready,
    output reg  [TDW-1:0]       m_axis_tdata,
    output reg                  m_axis_tlast
);

assign s_axis_tready = (~m_axis_tvalid) || m_axis_tready;

always @(posedge aclk) begin
    if (!aresetn) begin
        m_axis_tvalid <= 1'b0;
        m_axis_tdata  <= {TDW{1'b0}};
        m_axis_tlast  <= 1'b0;
    end else begin
        if (s_axis_tready) begin
            m_axis_tvalid <= s_axis_tvalid;
            if (s_axis_tvalid) begin
                m_axis_tdata <= s_axis_tdata;
                m_axis_tlast <= s_axis_tlast;
            end else begin
                m_axis_tlast <= 1'b0;
            end
        end
    end
end

endmodule
