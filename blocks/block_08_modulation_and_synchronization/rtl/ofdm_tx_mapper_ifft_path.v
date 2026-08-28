`timescale 1ns/1ps

// Block 8 OFDM RTL: first end-to-end transmit path for one 64-point symbol.
//
//   48 QPSK bit pairs
//       -> fixed Q1.15 mapper
//       -> Lab 8.5 subcarrier/pilot allocator
//       -> normalized sequential 64-point IFFT
//       -> 64 natural-order complex time samples
//
// This is deliberately a single-symbol-at-a-time baseline. The next frame is
// not accepted until sample 63 of the current frame is consumed. That removes
// hidden queueing between the allocator and sequential IFFT and makes the
// frame-level latency/valid contract explicit before adding CP and AXI-Stream.
//
// The mapper itself has one cycle of latency and no ready input. A one-entry
// bridge therefore captures its output before presenting it to the allocator.
// bits_ready is asserted only when both mapper/bridge are empty and the
// allocator is collecting. This prevents accepting a 49th data carrier while
// the 48th mapped symbol is still in flight.
module ofdm_tx_mapper_ifft_path (
    input  wire                clk,
    input  wire                resetn,

    input  wire                bits_valid,
    output wire                bits_ready,
    input  wire [1:0]          bits_in,

    output wire                sample_valid,
    input  wire                sample_ready,
    output wire signed [15:0]  sample_re,
    output wire signed [15:0]  sample_im,
    output wire [5:0]          sample_index,
    output wire                sample_last,

    output wire                ifft_busy,
    output wire [15:0]         total_saturation_count
);

    reg mapper_inflight;
    reg bridge_valid;
    reg signed [15:0] bridge_i;
    reg signed [15:0] bridge_q;
    reg [5:0] accepted_data_count;
    reg frame_locked;

    wire mapper_valid;
    wire signed [15:0] mapper_i;
    wire signed [15:0] mapper_q;

    wire allocator_data_ready;
    wire allocator_bin_valid;
    wire allocator_bin_ready;
    wire [5:0] allocator_bin_index;
    wire signed [15:0] allocator_bin_i;
    wire signed [15:0] allocator_bin_q;
    wire allocator_bin_last;

    wire launch_mapper = bits_valid && bits_ready;
    wire bridge_accept = bridge_valid && allocator_data_ready;
    wire frame_output_accept = sample_valid && sample_ready && sample_last;

    assign bits_ready =
        resetn &&
        !frame_locked &&
        !mapper_inflight &&
        !bridge_valid &&
        allocator_data_ready;

    ofdm_qpsk_mapper mapper (
        .clk(clk),
        .resetn(resetn),
        .valid_in(launch_mapper),
        .bits_in(bits_in),
        .valid_out(mapper_valid),
        .i_out(mapper_i),
        .q_out(mapper_q)
    );

    always @(posedge clk) begin
        if (!resetn) begin
            mapper_inflight <= 1'b0;
            bridge_valid <= 1'b0;
            bridge_i <= 16'sd0;
            bridge_q <= 16'sd0;
            accepted_data_count <= 6'd0;
            frame_locked <= 1'b0;
        end else begin
            if (launch_mapper) begin
                mapper_inflight <= 1'b1;
                if (accepted_data_count == 6'd47) begin
                    accepted_data_count <= 6'd0;
                    frame_locked <= 1'b1;
                end else begin
                    accepted_data_count <= accepted_data_count + 6'd1;
                end
            end

            if (mapper_valid) begin
                mapper_inflight <= 1'b0;
                bridge_valid <= 1'b1;
                bridge_i <= mapper_i;
                bridge_q <= mapper_q;
            end

            if (bridge_accept) begin
                bridge_valid <= 1'b0;
            end

            if (frame_output_accept) begin
                frame_locked <= 1'b0;
                accepted_data_count <= 6'd0;
            end
        end
    end

    ofdm_subcarrier_allocator allocator (
        .clk(clk),
        .resetn(resetn),
        .data_valid(bridge_valid),
        .data_ready(allocator_data_ready),
        .data_i(bridge_i),
        .data_q(bridge_q),
        .bin_valid(allocator_bin_valid),
        .bin_ready(allocator_bin_ready),
        .bin_index(allocator_bin_index),
        .bin_i(allocator_bin_i),
        .bin_q(allocator_bin_q),
        .bin_last(allocator_bin_last)
    );

    ofdm_ifft64_sequential ifft (
        .clk(clk),
        .resetn(resetn),
        .bin_valid(allocator_bin_valid),
        .bin_ready(allocator_bin_ready),
        .bin_re(allocator_bin_i),
        .bin_im(allocator_bin_q),
        .sample_valid(sample_valid),
        .sample_ready(sample_ready),
        .sample_re(sample_re),
        .sample_im(sample_im),
        .sample_index(sample_index),
        .sample_last(sample_last),
        .busy(ifft_busy),
        .total_saturation_count(total_saturation_count)
    );

endmodule
