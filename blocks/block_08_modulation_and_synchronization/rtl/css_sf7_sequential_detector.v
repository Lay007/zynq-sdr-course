`timescale 1ns/1ps

// Educational SF7 CSS detector: dechirp, sequential DFT, and two-peak search.
//
// This block intentionally favors readable RTL over area/throughput optimality.
// It accepts one complete 128-sample Q1.15 symbol, reuses the canonical Block 8
// saturating dechirp front end, and evaluates one complex DFT MAC per clock.
// The companion zynq-lora-phy-positioning project owns the production-oriented
// oversampled two-FFT LoRa correlator and packet/ToA integration path.
//
// Input contract:
//   * transfer when valid_in && ready;
//   * exactly 128 transfers form one symbol;
//   * resetn is active low;
//   * no next symbol is accepted until done returns the block to LOAD.
//
// Latency after the final input transfer is 1 drain cycle plus 128*(128+1)
// DFT/finish cycles and one done cycle. The output registers hold their most
// recent result. dechirp_overflow_count counts saturated input samples.
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

    localparam [2:0] S_LOAD  = 3'd0;
    localparam [2:0] S_DRAIN = 3'd1;
    localparam [2:0] S_MAC   = 3'd2;
    localparam [2:0] S_FIN   = 3'd3;
    localparam [2:0] S_DONE  = 3'd4;

    reg [2:0] state;
    reg [6:0] input_index;
    reg [6:0] write_index;
    reg [6:0] bin_index;
    reg [6:0] sample_index;
    reg [6:0] twiddle_index;

    reg signed [15:0] sample_buffer_re [0:127];
    reg signed [15:0] sample_buffer_im [0:127];
    reg signed [31:0] accumulator_re;
    reg signed [31:0] accumulator_im;

    assign ready = resetn && (state == S_LOAD);
    assign busy = (state != S_LOAD) || (input_index != 7'd0);

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

    wire signed [15:0] twiddle_re;
    wire signed [15:0] twiddle_im;

    css_q15_rom #(.FILE(TWIDDLE_I_FILE)) u_twiddle_re (
        .addr (twiddle_index),
        .dout (twiddle_re)
    );
    css_q15_rom #(.FILE(TWIDDLE_Q_FILE)) u_twiddle_im (
        .addr (twiddle_index),
        .dout (twiddle_im)
    );

    wire signed [15:0] buffered_re = sample_buffer_re[sample_index];
    wire signed [15:0] buffered_im = sample_buffer_im[sample_index];
    wire signed [31:0] product_rr = buffered_re * twiddle_re;
    wire signed [31:0] product_ii = buffered_im * twiddle_im;
    wire signed [31:0] product_ri = buffered_re * twiddle_im;
    wire signed [31:0] product_ir = buffered_im * twiddle_re;
    wire signed [32:0] full_term_re =
        {product_rr[31], product_rr} - {product_ii[31], product_ii};
    wire signed [32:0] full_term_im =
        {product_ri[31], product_ri} + {product_ir[31], product_ir};
    wire signed [32:0] term_re = full_term_re >>> 15;
    wire signed [32:0] term_im = full_term_im >>> 15;

    wire signed [63:0] accumulator_re_squared = accumulator_re * accumulator_re;
    wire signed [63:0] accumulator_im_squared = accumulator_im * accumulator_im;
    wire signed [63:0] magnitude_squared =
        accumulator_re_squared + accumulator_im_squared;

    always @(posedge clk) begin
        if (!resetn) begin
            state                       <= S_LOAD;
            input_index                 <= 7'd0;
            write_index                 <= 7'd0;
            bin_index                   <= 7'd0;
            sample_index                <= 7'd0;
            twiddle_index               <= 7'd0;
            accumulator_re              <= 32'sd0;
            accumulator_im              <= 32'sd0;
            done                        <= 1'b0;
            peak_bin                    <= 7'd0;
            second_bin                  <= 7'd0;
            peak_magnitude_squared      <= 64'sd0;
            second_magnitude_squared   <= 64'sd0;
            dechirp_overflow_count      <= 16'd0;
        end else begin
            done <= 1'b0;

            case (state)
                S_LOAD: begin
                    if (dechirp_valid) begin
                        sample_buffer_re[write_index] <= dechirp_re;
                        sample_buffer_im[write_index] <= dechirp_im;
                        write_index <= write_index + 1'b1;
                        if (dechirp_overflow)
                            dechirp_overflow_count <= dechirp_overflow_count + 1'b1;
                    end

                    if (valid_in && ready) begin
                        if (input_index == 7'd0 && write_index == 7'd0)
                            dechirp_overflow_count <= 16'd0;
                        if (input_index == 7'd127) begin
                            input_index <= 7'd0;
                            state <= S_DRAIN;
                        end else begin
                            input_index <= input_index + 1'b1;
                        end
                    end
                end

                S_DRAIN: begin
                    if (dechirp_valid) begin
                        sample_buffer_re[write_index] <= dechirp_re;
                        sample_buffer_im[write_index] <= dechirp_im;
                        if (dechirp_overflow)
                            dechirp_overflow_count <= dechirp_overflow_count + 1'b1;
                        write_index                 <= 7'd0;
                        bin_index                   <= 7'd0;
                        sample_index                <= 7'd0;
                        twiddle_index               <= 7'd0;
                        accumulator_re              <= 32'sd0;
                        accumulator_im              <= 32'sd0;
                        peak_bin                    <= 7'd0;
                        second_bin                  <= 7'd0;
                        peak_magnitude_squared      <= 64'sd0;
                        second_magnitude_squared   <= 64'sd0;
                        state                       <= S_MAC;
                    end
                end

                S_MAC: begin
                    accumulator_re <= accumulator_re + term_re;
                    accumulator_im <= accumulator_im + term_im;
                    twiddle_index <= twiddle_index + bin_index;
                    if (sample_index == 7'd127) begin
                        state <= S_FIN;
                    end else begin
                        sample_index <= sample_index + 1'b1;
                    end
                end

                S_FIN: begin
                    if (bin_index == 7'd0) begin
                        peak_magnitude_squared <= magnitude_squared;
                        peak_bin <= 7'd0;
                    end else if (magnitude_squared > peak_magnitude_squared) begin
                        second_magnitude_squared <= peak_magnitude_squared;
                        second_bin <= peak_bin;
                        peak_magnitude_squared <= magnitude_squared;
                        peak_bin <= bin_index;
                    end else if (magnitude_squared > second_magnitude_squared) begin
                        second_magnitude_squared <= magnitude_squared;
                        second_bin <= bin_index;
                    end

                    accumulator_re <= 32'sd0;
                    accumulator_im <= 32'sd0;
                    sample_index <= 7'd0;
                    twiddle_index <= 7'd0;
                    if (bin_index == 7'd127) begin
                        state <= S_DONE;
                    end else begin
                        bin_index <= bin_index + 1'b1;
                        state <= S_MAC;
                    end
                end

                S_DONE: begin
                    done <= 1'b1;
                    state <= S_LOAD;
                end

                default: state <= S_LOAD;
            endcase
        end
    end

endmodule
