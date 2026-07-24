// Lab 5.15 - differential QPSK encoder (TX pair of qpsk_diff_decoder)
//
// Maps an info dibit stream to absolute symbol dibits by accumulating phase: the transmitted phase
// index p[n] = (p[n-1] + increment(info[n])) mod 4, so consecutive-symbol differences carry the
// information and the receiver recovers it independent of any whole-burst rotation. See
// qpsk_diff_decoder.v for the phase-index convention and lab_11_43_dqpsk_model.py for the proof.
//
// This sits in the fabric TX between the frame dibit source and qpsk_framed_tx_chain, whose s_ready
// is NOT always high (the RRC upsampler backpressures). So the transform is COMBINATIONAL and the
// handshake is passed straight through -- valid/ready/last go across unchanged, the dibit is
// remapped, and the phase accumulator advances only on an accepted symbol (s_valid && m_ready). No
// added latency, no skid buffer. On the two-board link the transmitter is host-streamed, so the same
// accumulation is done in Python; the shared phase-index convention keeps them in step.
//
// enable=0 passes the info dibit straight through as the absolute symbol (ordinary QPSK), so the
// coherent loopback is bit-identical when differential mode is off.

`timescale 1ns/1ps

module qpsk_diff_encoder (
    input  wire       clk,
    input  wire       rst,
    input  wire       enable,       // 1 = differential encode, 0 = absolute QPSK passthrough
    input  wire       s_valid,
    input  wire [1:0] s_dibit,      // info dibit from the frame source
    input  wire       s_last,
    output wire       s_ready,
    output wire       m_valid,
    output wire [1:0] m_dibit,      // absolute symbol dibit for qpsk_symbol_mapper
    output wire       m_last,
    input  wire       m_ready
);

// Gray dibit <-> phase index (binary), matching qpsk_diff_decoder / qpsk_symbol_mapper.
function [1:0] p_of_dibit;
    input [1:0] d;
    p_of_dibit = {d[1], d[0] ^ d[1]};
endfunction

function [1:0] dibit_of_p;
    input [1:0] p;
    dibit_of_p = {p[1], p[0] ^ p[1]};
endfunction

reg [1:0] p_acc;

wire [1:0] inc    = p_of_dibit(s_dibit);
wire [1:0] p_next = p_acc + inc;                 // 2-bit add = (p_acc + inc) mod 4

// Combinational, handshake-transparent.
assign s_ready = m_ready;
assign m_valid = s_valid;
assign m_last  = s_last;
assign m_dibit = enable ? dibit_of_p(p_next) : s_dibit;

always @(posedge clk) begin
    if (rst) begin
        p_acc <= 2'b00;
    end else if (enable && s_valid && m_ready) begin
        p_acc <= p_next;                         // advance only on an accepted symbol
    end
end

endmodule
