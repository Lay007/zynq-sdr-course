`timescale 1ns/1ps

// Block 8 OFDM RTL: complete baseline transmitter for one CP-protected symbol.
//
//   48 QPSK bit pairs
//       -> Q1.15 mapper
//       -> Lab 8.5 subcarrier/pilot allocator
//       -> normalized sequential 64-point IFFT
//       -> CP=16 inserter
//       -> 80 complex output samples
//
// Frame contract:
//   * exactly 48 accepted bit pairs form one OFDM symbol;
//   * no bit pair from the next symbol is accepted until output sample 79 of
//     the current CP-protected symbol is consumed;
//   * output samples are x[48..63], x[0..63];
//   * valid/data/index/CP/last/error are held by the CP block under
//     downstream backpressure;
//   * all logic is in one clk domain; no CDC is hidden in this wrapper;
//   * synchronous active-low reset discards every partial frame.
//
// The inner mapper/IFFT path becomes ready again as soon as IFFT sample 63 is
// handed to the CP buffer. frame_locked deliberately extends that lock until
// CP output sample 79 is accepted, preventing implicit next-frame prefetch.
module ofdm_tx_cp16_path (
    input  wire                clk,
    input  wire                resetn,

    input  wire                bits_valid,
    output wire                bits_ready,
    input  wire [1:0]          bits_in,

    output wire                sample_valid,
    input  wire                sample_ready,
    output wire signed [15:0]  sample_re,
    output wire signed [15:0]  sample_im,
    output wire [6:0]          sample_index,
    output wire                sample_is_cp,
    output wire                sample_last,

    output wire                ifft_busy,
    output wire [15:0]         total_saturation_count,
    output wire                frame_error
);

    reg [5:0] accepted_data_count;
    reg frame_locked;

    wire inner_bits_valid;
    wire inner_bits_ready;

    wire inner_sample_valid;
    wire inner_sample_ready;
    wire signed [15:0] inner_sample_re;
    wire signed [15:0] inner_sample_im;
    wire [5:0] inner_sample_index;
    wire inner_sample_last;

    wire external_bit_accept = bits_valid && bits_ready;
    wire output_frame_accept = sample_valid && sample_ready && sample_last;

    assign bits_ready = resetn && !frame_locked && inner_bits_ready;
    assign inner_bits_valid = bits_valid && bits_ready;

    always @(posedge clk) begin
        if (!resetn) begin
            accepted_data_count <= 6'd0;
            frame_locked <= 1'b0;
        end else begin
            if (external_bit_accept) begin
                if (accepted_data_count == 6'd47) begin
                    accepted_data_count <= 6'd0;
                    frame_locked <= 1'b1;
                end else begin
                    accepted_data_count <= accepted_data_count + 6'd1;
                end
            end

            if (output_frame_accept) begin
                accepted_data_count <= 6'd0;
                frame_locked <= 1'b0;
            end
        end
    end

    ofdm_tx_mapper_ifft_path tx_core (
        .clk(clk),
        .resetn(resetn),
        .bits_valid(inner_bits_valid),
        .bits_ready(inner_bits_ready),
        .bits_in(bits_in),
        .sample_valid(inner_sample_valid),
        .sample_ready(inner_sample_ready),
        .sample_re(inner_sample_re),
        .sample_im(inner_sample_im),
        .sample_index(inner_sample_index),
        .sample_last(inner_sample_last),
        .ifft_busy(ifft_busy),
        .total_saturation_count(total_saturation_count)
    );

    ofdm_cp16_inserter cp16 (
        .clk(clk),
        .resetn(resetn),
        .in_valid(inner_sample_valid),
        .in_ready(inner_sample_ready),
        .in_re(inner_sample_re),
        .in_im(inner_sample_im),
        .in_last(inner_sample_last),
        .out_valid(sample_valid),
        .out_ready(sample_ready),
        .out_re(sample_re),
        .out_im(sample_im),
        .out_index(sample_index),
        .out_is_cp(sample_is_cp),
        .out_last(sample_last),
        .frame_error(frame_error)
    );

endmodule
