`timescale 1ns/1ps

// Reusable educational 128-point complex DFT core for the Block 8 CSS path.
//
// One buffered Q1.15 sample is read and accumulated per clock. Each bin takes
// 128 MAC clocks followed by one output clock; this is deliberately a readable
// sequential DFT, not a throughput-optimized FFT.
//
// Fixed-point contract, preserved from css_sf7_sequential_detector:
//   * sample_re/sample_im and twiddles are signed 16-bit Q1.15;
//   * each real multiply produces a signed 32-bit Q2.30 product;
//   * complex product add/sub operations are widened to signed 33 bits;
//   * each complex term is arithmetically shifted right by 15 before the MAC;
//   * accumulators and streamed bin components are signed 32 bits;
//   * two signed 32x32 squares and their signed 64-bit sum form magnitude_squared.
//
// The explicit [31:0] assignment of next_accumulator_* preserves the original
// accumulator truncation boundary. For Q1.15 inputs, one shifted complex term
// has magnitude below 2^17 and 128 terms remain within the signed 32-bit
// accumulator. Under that same contract, the magnitude sum remains positive
// and below the signed 64-bit limit. No saturation or overflow flag is provided
// inside this core because the supported SF7 numerical bounds do not overflow.
module css_dft128_core #(
    parameter TWIDDLE_I_FILE =
        "blocks/block_08_modulation_and_synchronization/tb/vectors/css_sf7_twiddle_i_q15.hex",
    parameter TWIDDLE_Q_FILE =
        "blocks/block_08_modulation_and_synchronization/tb/vectors/css_sf7_twiddle_q_q15.hex"
) (
    input  wire                    clk,
    input  wire                    resetn,

    input  wire                    start,
    output wire                    busy,
    output reg                     done,
    output reg                     start_rejected,

    output wire [6:0]              sample_addr,
    input  wire signed [15:0]      sample_re,
    input  wire signed [15:0]      sample_im,

    output reg                     bin_valid,
    output reg  [6:0]              bin_index,
    output reg  signed [31:0]      bin_re,
    output reg  signed [31:0]      bin_im,
    output reg  signed [63:0]      magnitude_squared
);

    localparam [1:0] S_IDLE = 2'd0;
    localparam [1:0] S_MAC  = 2'd1;
    localparam [1:0] S_EMIT = 2'd2;

    reg [1:0] state;
    reg [6:0] sample_index;
    reg [6:0] twiddle_index;
    reg signed [31:0] accumulator_re;
    reg signed [31:0] accumulator_im;

    assign busy = (state != S_IDLE);
    assign sample_addr = sample_index;

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

    wire signed [31:0] product_rr = sample_re * twiddle_re;
    wire signed [31:0] product_ii = sample_im * twiddle_im;
    wire signed [31:0] product_ri = sample_re * twiddle_im;
    wire signed [31:0] product_ir = sample_im * twiddle_re;

    wire signed [32:0] full_term_re =
        {product_rr[31], product_rr} - {product_ii[31], product_ii};
    wire signed [32:0] full_term_im =
        {product_ri[31], product_ri} + {product_ir[31], product_ir};
    wire signed [32:0] term_re = full_term_re >>> 15;
    wire signed [32:0] term_im = full_term_im >>> 15;

    wire signed [32:0] next_accumulator_re =
        {accumulator_re[31], accumulator_re} + term_re;
    wire signed [32:0] next_accumulator_im =
        {accumulator_im[31], accumulator_im} + term_im;

    wire signed [63:0] accumulator_re_squared =
        accumulator_re * accumulator_re;
    wire signed [63:0] accumulator_im_squared =
        accumulator_im * accumulator_im;
    wire signed [63:0] accumulator_magnitude_squared =
        accumulator_re_squared + accumulator_im_squared;

    always @(posedge clk) begin
        if (!resetn) begin
            state               <= S_IDLE;
            sample_index        <= 7'd0;
            twiddle_index       <= 7'd0;
            accumulator_re      <= 32'sd0;
            accumulator_im      <= 32'sd0;
            done                <= 1'b0;
            start_rejected      <= 1'b0;
            bin_valid           <= 1'b0;
            bin_index           <= 7'd0;
            bin_re              <= 32'sd0;
            bin_im              <= 32'sd0;
            magnitude_squared   <= 64'sd0;
        end else begin
            done           <= 1'b0;
            start_rejected <= 1'b0;
            bin_valid      <= 1'b0;

            if (start && state != S_IDLE)
                start_rejected <= 1'b1;

            case (state)
                S_IDLE: begin
                    if (start) begin
                        sample_index    <= 7'd0;
                        twiddle_index   <= 7'd0;
                        accumulator_re  <= 32'sd0;
                        accumulator_im  <= 32'sd0;
                        bin_index       <= 7'd0;
                        state           <= S_MAC;
                    end
                end

                S_MAC: begin
                    accumulator_re <= next_accumulator_re[31:0];
                    accumulator_im <= next_accumulator_im[31:0];
                    twiddle_index  <= twiddle_index + bin_index;
                    if (sample_index == 7'd127) begin
                        state <= S_EMIT;
                    end else begin
                        sample_index <= sample_index + 1'b1;
                    end
                end

                S_EMIT: begin
                    bin_valid         <= 1'b1;
                    bin_re            <= accumulator_re;
                    bin_im            <= accumulator_im;
                    magnitude_squared <= accumulator_magnitude_squared;

                    sample_index    <= 7'd0;
                    twiddle_index   <= 7'd0;
                    accumulator_re  <= 32'sd0;
                    accumulator_im  <= 32'sd0;
                    if (bin_index == 7'd127) begin
                        done  <= 1'b1;
                        state <= S_IDLE;
                    end else begin
                        bin_index <= bin_index + 1'b1;
                        state     <= S_MAC;
                    end
                end

                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
