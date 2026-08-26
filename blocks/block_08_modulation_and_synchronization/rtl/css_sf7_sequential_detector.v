`timescale 1ns/1ps

// Educational SF7 CSS detector assembled from reusable accelerator stages:
// dechirp front end, symbol buffer, sequential DFT core, and two-peak search.
//
// This block intentionally favors readable RTL over area/throughput optimality.
// It accepts one complete 128-sample Q1.15 symbol and preserves the original
// detector interface and fixed-point result convention. The reusable DFT core
// evaluates one complex MAC per clock and streams one completed bin every 129
// clocks. It is not a throughput-optimized FFT.
//
// Input contract:
//   * transfer when valid_in && ready;
//   * exactly 128 transfers form one symbol;
//   * resetn is active low and aborts every pipeline stage;
//   * no next symbol is accepted until done releases the symbol buffer.
//
// The output registers hold their most recent result. The public done pulse is
// delayed until the symbol buffer has been released, so ready is high in the
// done cycle as in the original monolithic detector. dechirp_overflow_count
// counts saturated input samples.
module css_sf7_sequential_detector #(
    parameter TWIDDLE_I_FILE =
        "blocks/block_08_modulation_and_synchronization/tb/vectors/css_sf7_twiddle_i_q15.hex",
    parameter TWIDDLE_Q_FILE =
        "blocks/block_08_modulation_and_synchronization/tb/vectors/css_sf7_twiddle_q_q15.hex"
) (
    input  wire                    clk,
    input  wire                    resetn,

    input  wire                    valid_in,
    output wire                    ready,
    input  wire signed [15:0]      iq_re,
    input  wire signed [15:0]      iq_im,

    output wire                    busy,
    output reg                     done,
    output reg  [6:0]              peak_bin,
    output reg  [6:0]              second_bin,
    output reg  signed [63:0]      peak_magnitude_squared,
    output reg  signed [63:0]      second_magnitude_squared,
    output reg  [15:0]             dechirp_overflow_count
);

    reg [6:0] input_index;

    wire dechirp_valid;
    wire signed [15:0] dechirp_re;
    wire signed [15:0] dechirp_im;
    wire dechirp_overflow;

    css_sf7_dechirp_frontend u_dechirp_frontend (
        .clk          (clk),
        .resetn       (resetn),
        .valid_in     (valid_in && ready),
        .sample_index (input_index),
        .iq_re        (iq_re),
        .iq_im        (iq_im),
        .valid_out    (dechirp_valid),
        .dechirp_re   (dechirp_re),
        .dechirp_im   (dechirp_im),
        .overflow     (dechirp_overflow)
    );

    wire buffer_ready;
    wire buffer_complete;
    wire buffer_full;
    wire [7:0] buffer_accepted_count;
    wire [6:0] buffer_read_addr;
    wire signed [15:0] buffer_read_re;
    wire signed [15:0] buffer_read_im;
    wire buffer_release;

    css_symbol_buffer #(
        .DEPTH(128),
        .ADDR_WIDTH(7)
    ) u_symbol_buffer (
        .clk             (clk),
        .resetn          (resetn),
        .valid_in        (dechirp_valid),
        .ready           (buffer_ready),
        .iq_re           (dechirp_re),
        .iq_im           (dechirp_im),
        .release_buffer  (buffer_release),
        .symbol_complete (buffer_complete),
        .full            (buffer_full),
        .accepted_count  (buffer_accepted_count),
        .read_addr       (buffer_read_addr),
        .read_re         (buffer_read_re),
        .read_im         (buffer_read_im)
    );

    wire dft_busy;
    wire dft_done;
    wire dft_start_rejected;
    wire dft_bin_valid;
    wire [6:0] dft_bin_index;
    wire signed [31:0] dft_bin_re;
    wire signed [31:0] dft_bin_im;
    wire signed [63:0] dft_magnitude_squared;

    css_dft128_core #(
        .TWIDDLE_I_FILE(TWIDDLE_I_FILE),
        .TWIDDLE_Q_FILE(TWIDDLE_Q_FILE)
    ) u_dft_core (
        .clk               (clk),
        .resetn            (resetn),
        .start             (buffer_complete),
        .busy              (dft_busy),
        .done              (dft_done),
        .start_rejected    (dft_start_rejected),
        .sample_addr       (buffer_read_addr),
        .sample_re         (buffer_read_re),
        .sample_im         (buffer_read_im),
        .bin_valid         (dft_bin_valid),
        .bin_index         (dft_bin_index),
        .bin_re            (dft_bin_re),
        .bin_im            (dft_bin_im),
        .magnitude_squared (dft_magnitude_squared)
    );

    assign ready = buffer_ready;
    assign busy = (input_index != 7'd0) ||
                  (buffer_accepted_count != 8'd0) ||
                  buffer_full ||
                  dft_busy;
    assign buffer_release = dft_done;

    always @(posedge clk) begin
        if (!resetn) begin
            input_index                 <= 7'd0;
            done                        <= 1'b0;
            peak_bin                    <= 7'd0;
            second_bin                  <= 7'd0;
            peak_magnitude_squared      <= 64'sd0;
            second_magnitude_squared    <= 64'sd0;
            dechirp_overflow_count      <= 16'd0;
        end else begin
            done <= 1'b0;

            if (valid_in && ready) begin
                if (input_index == 7'd0)
                    dechirp_overflow_count <= 16'd0;
                if (input_index == 7'd127)
                    input_index <= 7'd0;
                else
                    input_index <= input_index + 1'b1;
            end

            if (dechirp_valid && dechirp_overflow)
                dechirp_overflow_count <= dechirp_overflow_count + 1'b1;

            if (buffer_complete) begin
                peak_bin                   <= 7'd0;
                second_bin                 <= 7'd0;
                peak_magnitude_squared     <= 64'sd0;
                second_magnitude_squared  <= 64'sd0;
            end

            if (dft_bin_valid) begin
                if (dft_bin_index == 7'd0) begin
                    peak_magnitude_squared <= dft_magnitude_squared;
                    peak_bin <= 7'd0;
                end else if (dft_magnitude_squared > peak_magnitude_squared) begin
                    second_magnitude_squared <= peak_magnitude_squared;
                    second_bin <= peak_bin;
                    peak_magnitude_squared <= dft_magnitude_squared;
                    peak_bin <= dft_bin_index;
                end else if (dft_magnitude_squared > second_magnitude_squared) begin
                    second_magnitude_squared <= dft_magnitude_squared;
                    second_bin <= dft_bin_index;
                end
            end

            if (dft_done)
                done <= 1'b1;
        end
    end

endmodule
