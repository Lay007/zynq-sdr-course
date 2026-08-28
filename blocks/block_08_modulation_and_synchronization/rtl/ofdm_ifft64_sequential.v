`timescale 1ns/1ps

// Block 8 OFDM RTL: transparent baseline 64-point radix-2 DIT IFFT.
//
// This core intentionally reuses one ofdm_ifft_butterfly instead of hiding the
// arithmetic inside a vendor FFT IP. It is the course baseline for verifying
// ordering, fixed-point scaling, saturation and control before throughput
// optimization.
//
// Interface contract:
//   * 64 natural-order frequency bins are accepted with valid/ready;
//   * input bins are written directly into bit-reversed memory addresses;
//   * six radix-2 DIT stages execute 32 butterflies each;
//   * one butterfly is issued at a time and takes two controller clocks
//     (issue + writeback), for 384 compute clocks after input collection;
//   * each butterfly divides by two, giving the normalized 1/64 IFFT scale;
//   * 64 natural-order time samples are emitted with valid/ready;
//   * output payload/index/last remain stable under backpressure;
//   * the next transform is not accepted until the current output frame ends;
//   * total_saturation_count accumulates final-component clips from all 192
//     butterflies and remains visible through output/readback;
//   * all logic uses one clock and synchronous active-low reset.
//
// Memory is deliberately described as a small dual-read/two-write register
// array. A later optimized implementation may replace the controller/memory
// architecture without changing this arithmetic contract.
module ofdm_ifft64_sequential (
    input  wire                clk,
    input  wire                resetn,

    input  wire                bin_valid,
    output wire                bin_ready,
    input  wire signed [15:0]  bin_re,
    input  wire signed [15:0]  bin_im,

    output wire                sample_valid,
    input  wire                sample_ready,
    output wire signed [15:0]  sample_re,
    output wire signed [15:0]  sample_im,
    output wire [5:0]          sample_index,
    output wire                sample_last,

    output wire                busy,
    output reg  [15:0]         total_saturation_count
);

    localparam [1:0] STATE_LOAD   = 2'd0;
    localparam [1:0] STATE_ISSUE  = 2'd1;
    localparam [1:0] STATE_WAIT   = 2'd2;
    localparam [1:0] STATE_OUTPUT = 2'd3;

    reg [1:0] state;
    reg [5:0] input_index;
    reg [2:0] stage;
    reg [5:0] group_base;
    reg [4:0] butterfly_j;
    reg [5:0] output_index;

    reg signed [15:0] memory_re [0:63];
    reg signed [15:0] memory_im [0:63];

    function automatic [5:0] bit_reverse6;
        input [5:0] value;
        begin
            bit_reverse6 = {
                value[0], value[1], value[2],
                value[3], value[4], value[5]
            };
        end
    endfunction

    function automatic signed [15:0] twiddle_re_q15;
        input [4:0] index;
        begin
            case (index)
                5'd0:  twiddle_re_q15 = 16'sd32767;
                5'd1:  twiddle_re_q15 = 16'sd32610;
                5'd2:  twiddle_re_q15 = 16'sd32138;
                5'd3:  twiddle_re_q15 = 16'sd31357;
                5'd4:  twiddle_re_q15 = 16'sd30274;
                5'd5:  twiddle_re_q15 = 16'sd28899;
                5'd6:  twiddle_re_q15 = 16'sd27246;
                5'd7:  twiddle_re_q15 = 16'sd25330;
                5'd8:  twiddle_re_q15 = 16'sd23170;
                5'd9:  twiddle_re_q15 = 16'sd20788;
                5'd10: twiddle_re_q15 = 16'sd18205;
                5'd11: twiddle_re_q15 = 16'sd15447;
                5'd12: twiddle_re_q15 = 16'sd12540;
                5'd13: twiddle_re_q15 = 16'sd9512;
                5'd14: twiddle_re_q15 = 16'sd6393;
                5'd15: twiddle_re_q15 = 16'sd3212;
                5'd16: twiddle_re_q15 = 16'sd0;
                5'd17: twiddle_re_q15 = -16'sd3212;
                5'd18: twiddle_re_q15 = -16'sd6393;
                5'd19: twiddle_re_q15 = -16'sd9512;
                5'd20: twiddle_re_q15 = -16'sd12540;
                5'd21: twiddle_re_q15 = -16'sd15447;
                5'd22: twiddle_re_q15 = -16'sd18205;
                5'd23: twiddle_re_q15 = -16'sd20788;
                5'd24: twiddle_re_q15 = -16'sd23170;
                5'd25: twiddle_re_q15 = -16'sd25330;
                5'd26: twiddle_re_q15 = -16'sd27246;
                5'd27: twiddle_re_q15 = -16'sd28899;
                5'd28: twiddle_re_q15 = -16'sd30274;
                5'd29: twiddle_re_q15 = -16'sd31357;
                5'd30: twiddle_re_q15 = -16'sd32138;
                default: twiddle_re_q15 = -16'sd32610;
            endcase
        end
    endfunction

    function automatic signed [15:0] twiddle_im_q15;
        input [4:0] index;
        begin
            case (index)
                5'd0:  twiddle_im_q15 = 16'sd0;
                5'd1:  twiddle_im_q15 = 16'sd3212;
                5'd2:  twiddle_im_q15 = 16'sd6393;
                5'd3:  twiddle_im_q15 = 16'sd9512;
                5'd4:  twiddle_im_q15 = 16'sd12540;
                5'd5:  twiddle_im_q15 = 16'sd15447;
                5'd6:  twiddle_im_q15 = 16'sd18205;
                5'd7:  twiddle_im_q15 = 16'sd20788;
                5'd8:  twiddle_im_q15 = 16'sd23170;
                5'd9:  twiddle_im_q15 = 16'sd25330;
                5'd10: twiddle_im_q15 = 16'sd27246;
                5'd11: twiddle_im_q15 = 16'sd28899;
                5'd12: twiddle_im_q15 = 16'sd30274;
                5'd13: twiddle_im_q15 = 16'sd31357;
                5'd14: twiddle_im_q15 = 16'sd32138;
                5'd15: twiddle_im_q15 = 16'sd32610;
                5'd16: twiddle_im_q15 = 16'sd32767;
                5'd17: twiddle_im_q15 = 16'sd32610;
                5'd18: twiddle_im_q15 = 16'sd32138;
                5'd19: twiddle_im_q15 = 16'sd31357;
                5'd20: twiddle_im_q15 = 16'sd30274;
                5'd21: twiddle_im_q15 = 16'sd28899;
                5'd22: twiddle_im_q15 = 16'sd27246;
                5'd23: twiddle_im_q15 = 16'sd25330;
                5'd24: twiddle_im_q15 = 16'sd23170;
                5'd25: twiddle_im_q15 = 16'sd20788;
                5'd26: twiddle_im_q15 = 16'sd18205;
                5'd27: twiddle_im_q15 = 16'sd15447;
                5'd28: twiddle_im_q15 = 16'sd12540;
                5'd29: twiddle_im_q15 = 16'sd9512;
                5'd30: twiddle_im_q15 = 16'sd6393;
                default: twiddle_im_q15 = 16'sd3212;
            endcase
        end
    endfunction

    wire [5:0] half_size = 6'd1 << stage;
    wire [6:0] span_size = {half_size, 1'b0};
    wire [5:0] butterfly_index0 = group_base + {1'b0, butterfly_j};
    wire [5:0] butterfly_index1 = butterfly_index0 + half_size;

    reg [4:0] twiddle_index;
    always @* begin
        case (stage)
            3'd0: twiddle_index = butterfly_j << 5;
            3'd1: twiddle_index = butterfly_j << 4;
            3'd2: twiddle_index = butterfly_j << 3;
            3'd3: twiddle_index = butterfly_j << 2;
            3'd4: twiddle_index = butterfly_j << 1;
            default: twiddle_index = butterfly_j;
        endcase
    end

    wire butterfly_valid_out;
    wire signed [15:0] butterfly_y0_re;
    wire signed [15:0] butterfly_y0_im;
    wire signed [15:0] butterfly_y1_re;
    wire signed [15:0] butterfly_y1_im;
    wire [2:0] butterfly_saturation_count;

    ofdm_ifft_butterfly butterfly (
        .clk(clk),
        .resetn(resetn),
        .valid_in(state == STATE_ISSUE),
        .a_re(memory_re[butterfly_index0]),
        .a_im(memory_im[butterfly_index0]),
        .b_re(memory_re[butterfly_index1]),
        .b_im(memory_im[butterfly_index1]),
        .w_re(twiddle_re_q15(twiddle_index)),
        .w_im(twiddle_im_q15(twiddle_index)),
        .valid_out(butterfly_valid_out),
        .y0_re(butterfly_y0_re),
        .y0_im(butterfly_y0_im),
        .y1_re(butterfly_y1_re),
        .y1_im(butterfly_y1_im),
        .saturation_count(butterfly_saturation_count)
    );

    assign bin_ready = (state == STATE_LOAD);
    assign sample_valid = (state == STATE_OUTPUT);
    assign sample_re = memory_re[output_index];
    assign sample_im = memory_im[output_index];
    assign sample_index = output_index;
    assign sample_last = sample_valid && (output_index == 6'd63);
    assign busy = (state == STATE_ISSUE) || (state == STATE_WAIT);

    always @(posedge clk) begin
        if (!resetn) begin
            state <= STATE_LOAD;
            input_index <= 6'd0;
            stage <= 3'd0;
            group_base <= 6'd0;
            butterfly_j <= 5'd0;
            output_index <= 6'd0;
            total_saturation_count <= 16'd0;
        end else begin
            case (state)
                STATE_LOAD: begin
                    if (bin_valid) begin
                        memory_re[bit_reverse6(input_index)] <= bin_re;
                        memory_im[bit_reverse6(input_index)] <= bin_im;

                        if (input_index == 6'd63) begin
                            input_index <= 6'd0;
                            stage <= 3'd0;
                            group_base <= 6'd0;
                            butterfly_j <= 5'd0;
                            total_saturation_count <= 16'd0;
                            state <= STATE_ISSUE;
                        end else begin
                            input_index <= input_index + 6'd1;
                        end
                    end
                end

                STATE_ISSUE: begin
                    // The butterfly samples memory/twiddle inputs on this edge.
                    state <= STATE_WAIT;
                end

                STATE_WAIT: begin
                    if (butterfly_valid_out) begin
                        memory_re[butterfly_index0] <= butterfly_y0_re;
                        memory_im[butterfly_index0] <= butterfly_y0_im;
                        memory_re[butterfly_index1] <= butterfly_y1_re;
                        memory_im[butterfly_index1] <= butterfly_y1_im;
                        total_saturation_count <=
                            total_saturation_count + butterfly_saturation_count;

                        if ({1'b0, butterfly_j} == (half_size - 6'd1)) begin
                            butterfly_j <= 5'd0;
                            if (({1'b0, group_base} + span_size) >= 7'd64) begin
                                group_base <= 6'd0;
                                if (stage == 3'd5) begin
                                    output_index <= 6'd0;
                                    state <= STATE_OUTPUT;
                                end else begin
                                    stage <= stage + 3'd1;
                                    state <= STATE_ISSUE;
                                end
                            end else begin
                                group_base <= group_base + span_size[5:0];
                                state <= STATE_ISSUE;
                            end
                        end else begin
                            butterfly_j <= butterfly_j + 5'd1;
                            state <= STATE_ISSUE;
                        end
                    end
                end

                default: begin // STATE_OUTPUT
                    if (sample_ready) begin
                        if (output_index == 6'd63) begin
                            output_index <= 6'd0;
                            input_index <= 6'd0;
                            state <= STATE_LOAD;
                        end else begin
                            output_index <= output_index + 6'd1;
                        end
                    end
                end
            endcase
        end
    end

endmodule
