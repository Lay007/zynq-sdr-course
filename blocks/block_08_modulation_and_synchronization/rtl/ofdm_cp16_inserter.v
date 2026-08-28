`timescale 1ns/1ps

// Block 8 OFDM RTL: fixed CP=16 inserter for one 64-sample time-domain symbol.
//
// Input contract:
//   * exactly 64 accepted Q1.15 complex samples form one symbol;
//   * in_last is expected only on accepted sample index 63;
//   * input valid gaps do not advance the sample index;
//   * no next input symbol is accepted while the current symbol is emitted.
//
// Output contract:
//   * 80 samples are emitted: input[48..63], then input[0..63];
//   * out_index is 0..79 and out_is_cp is asserted for indices 0..15;
//   * out_last is asserted only for output index 79;
//   * valid, payload, index, CP flag, last and frame_error remain stable under
//     downstream backpressure;
//   * frame_error is asserted for the complete output symbol if input in_last
//     was early or missing at accepted input index 63;
//   * synchronous active-low reset discards a partial input/output symbol.
module ofdm_cp16_inserter (
    input  wire                clk,
    input  wire                resetn,

    input  wire                in_valid,
    output wire                in_ready,
    input  wire signed [15:0]  in_re,
    input  wire signed [15:0]  in_im,
    input  wire                in_last,

    output wire                out_valid,
    input  wire                out_ready,
    output wire signed [15:0]  out_re,
    output wire signed [15:0]  out_im,
    output wire [6:0]          out_index,
    output wire                out_is_cp,
    output wire                out_last,
    output wire                frame_error
);

    localparam STATE_COLLECT = 1'b0;
    localparam STATE_EMIT    = 1'b1;

    reg state;
    reg [5:0] input_index;
    reg [6:0] output_index;
    reg frame_error_reg;

    reg signed [15:0] sample_re_mem [0:63];
    reg signed [15:0] sample_im_mem [0:63];

    wire expected_input_last = (input_index == 6'd63);
    wire input_last_mismatch = in_last != expected_input_last;
    wire [5:0] output_memory_index =
        (output_index < 7'd16)
            ? (6'd48 + output_index[5:0])
            : (output_index[5:0] - 6'd16);

    assign in_ready = (state == STATE_COLLECT);
    assign out_valid = (state == STATE_EMIT);
    assign out_re = sample_re_mem[output_memory_index];
    assign out_im = sample_im_mem[output_memory_index];
    assign out_index = output_index;
    assign out_is_cp = out_valid && (output_index < 7'd16);
    assign out_last = out_valid && (output_index == 7'd79);
    assign frame_error = out_valid && frame_error_reg;

    always @(posedge clk) begin
        if (!resetn) begin
            state <= STATE_COLLECT;
            input_index <= 6'd0;
            output_index <= 7'd0;
            frame_error_reg <= 1'b0;
        end else begin
            if (state == STATE_COLLECT) begin
                if (in_valid) begin
                    sample_re_mem[input_index] <= in_re;
                    sample_im_mem[input_index] <= in_im;

                    if (input_last_mismatch)
                        frame_error_reg <= 1'b1;

                    if (input_index == 6'd63) begin
                        input_index <= 6'd0;
                        output_index <= 7'd0;
                        state <= STATE_EMIT;
                    end else begin
                        input_index <= input_index + 6'd1;
                    end
                end
            end else if (out_ready) begin
                if (output_index == 7'd79) begin
                    output_index <= 7'd0;
                    frame_error_reg <= 1'b0;
                    state <= STATE_COLLECT;
                end else begin
                    output_index <= output_index + 7'd1;
                end
            end
        end
    end

endmodule
