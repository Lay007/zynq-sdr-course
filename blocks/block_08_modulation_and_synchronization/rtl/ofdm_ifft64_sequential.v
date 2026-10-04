`timescale 1ns/1ps

// Default IFFT/FFT schedule for the whole OFDM chain: 1 = pipelined butterfly
// (timing-closed at 100 MHz), 0 = the one-cycle teaching baseline. Override per
// instance with the PIPELINED parameter, or globally with
// +define+OFDM_IFFT_PIPELINED=0.
`ifndef OFDM_IFFT_PIPELINED
`define OFDM_IFFT_PIPELINED 1
`endif

// Working memory of the transforms: 0 = fabric registers/LUT RAM (default),
// 1 = two block-RAM banks (needs PIPELINED = 1). Override per instance with the
// BRAM_MEMORY parameter, or globally with +define+OFDM_IFFT_BRAM=1.
`ifndef OFDM_IFFT_BRAM
`define OFDM_IFFT_BRAM 0
`endif


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
//   * PIPELINED = 0: one butterfly is issued at a time and takes two
//     controller clocks (issue + writeback), for 384 compute clocks after
//     input collection (PIPELINED = 1: 222 clocks, see below);
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
//
// PIPELINED = 1 keeps the arithmetic, ordering and interface contract but
// changes the schedule: the four-cycle pipelined butterfly accepts one
// butterfly per clock, so a stage's 32 butterflies are issued back to back and
// each result is written back four clocks later (the write addresses travel
// alongside in a delay line). Inside one radix-2 stage every point belongs to
// exactly one butterfly, so those reads and writes never collide; between
// stages the controller waits until the pipeline has drained. Compute then
// takes about 6 * (32 + 4) clocks instead of 384, and no single clock holds
// the multiply-round-saturate chain.
//
// BRAM_MEMORY = 1 (with PIPELINED = 1) moves the working memory into two
// block-RAM banks of 32 words: bank = XOR of the six address bits, word =
// address[5:1]. The two points of a butterfly differ in exactly one address
// bit, so they are always in different banks: each bank serves one read and
// one write per clock (simple dual-port), which covers two reads and two
// write-backs per clock. Block RAM reads are registered, so the operands and
// the twiddle reach the butterfly one clock after issue (write-back five
// clocks after issue), and the output starts one clock later; the read
// address of the output is the next index, so backpressure keeps the sample
// stable. Arithmetic and ordering are unchanged.
module ofdm_ifft64_sequential #(
    parameter integer PIPELINED = `OFDM_IFFT_PIPELINED,
    parameter integer BRAM_MEMORY = `OFDM_IFFT_BRAM
) (
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

    localparam [2:0] STATE_LOAD   = 3'd0;
    localparam [2:0] STATE_ISSUE  = 3'd1;
    localparam [2:0] STATE_WAIT   = 3'd2;
    localparam [2:0] STATE_OUTPUT = 3'd3;
    localparam [2:0] STATE_DRAIN  = 3'd4; // pipelined only: wait for write-back
    localparam [2:0] STATE_PREP   = 3'd5; // BRAM only: read output sample 0

    localparam integer LATENCY = (PIPELINED != 0) ? 4 : 1;
    // Issue to write-back: the butterfly latency, plus the block-RAM read.
    localparam integer WB_DELAY = LATENCY + ((BRAM_MEMORY != 0) ? 1 : 0);

    generate
        if ((BRAM_MEMORY != 0) && (PIPELINED == 0)) begin : g_bad_config
            initial begin
                $display("ERROR: ofdm_ifft64_sequential BRAM_MEMORY=1 needs PIPELINED=1");
                $finish;
            end
        end
    endgenerate

    reg [2:0] state;
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

    // Write-back addresses of the butterflies in flight (pipelined mode).
    reg [5:0] wb_index0 [0:WB_DELAY-1];
    reg [5:0] wb_index1 [0:WB_DELAY-1];
    reg [2:0] in_flight;
    integer wb_k;

    wire last_butterfly_of_stage =
        ({1'b0, butterfly_j} == (half_size - 6'd1)) &&
        (({1'b0, group_base} + span_size) >= 7'd64);

    // ---- block-RAM working memory (BRAM_MEMORY = 1) ----
    function automatic parity6;
        input [5:0] value;
        begin
            parity6 = ^value;
        end
    endfunction

    reg         bank_we [0:1];
    reg  [4:0]  bank_waddr [0:1];
    reg  [31:0] bank_wdata [0:1];
    reg  [4:0]  bank_raddr [0:1];
    wire [31:0] bank_rdata0;
    wire [31:0] bank_rdata1;
    reg         issue_q;          // a butterfly's operands are on the bank outputs
    reg         bank_sel_q;       // bank of operand a for that butterfly
    reg signed [15:0] tw_re_q;
    reg signed [15:0] tw_im_q;
    reg  [5:0]  next_output_index;

    wire [31:0] op_a = bank_sel_q ? bank_rdata1 : bank_rdata0;
    wire [31:0] op_b = bank_sel_q ? bank_rdata0 : bank_rdata1;

    generate
        if (BRAM_MEMORY != 0) begin : g_banks
            ofdm_iq_bank_ram bank0 (
                .clk(clk), .we(bank_we[0]), .waddr(bank_waddr[0]), .wdata(bank_wdata[0]),
                .raddr(bank_raddr[0]), .rdata(bank_rdata0)
            );
            ofdm_iq_bank_ram bank1 (
                .clk(clk), .we(bank_we[1]), .waddr(bank_waddr[1]), .wdata(bank_wdata[1]),
                .raddr(bank_raddr[1]), .rdata(bank_rdata1)
            );
        end else begin : g_no_banks
            assign bank_rdata0 = 32'd0;
            assign bank_rdata1 = 32'd0;
        end
    endgenerate

    wire [5:0] load_address = bit_reverse6(input_index);
    wire [5:0] wb_last0 = wb_index0[WB_DELAY-1];
    wire [5:0] wb_last1 = wb_index1[WB_DELAY-1];
    wire sample_fire = (state == STATE_OUTPUT) && sample_ready;

    always @* begin
        // Output read address: the index that will be on the output next clock.
        if (state == STATE_OUTPUT)
            next_output_index = sample_fire ? output_index + 6'd1 : output_index;
        else
            next_output_index = 6'd0;

        bank_we[0] = 1'b0;
        bank_we[1] = 1'b0;
        bank_waddr[0] = 5'd0;
        bank_waddr[1] = 5'd0;
        bank_wdata[0] = 32'd0;
        bank_wdata[1] = 32'd0;
        if (state == STATE_LOAD && bin_valid) begin
            bank_we[parity6(load_address)] = 1'b1;
            bank_waddr[parity6(load_address)] = load_address[5:1];
            bank_wdata[parity6(load_address)] = {bin_re, bin_im};
        end
        if (butterfly_valid_out) begin
            bank_we[parity6(wb_last0)] = 1'b1;
            bank_waddr[parity6(wb_last0)] = wb_last0[5:1];
            bank_wdata[parity6(wb_last0)] = {butterfly_y0_re, butterfly_y0_im};
            bank_we[parity6(wb_last1)] = 1'b1;
            bank_waddr[parity6(wb_last1)] = wb_last1[5:1];
            bank_wdata[parity6(wb_last1)] = {butterfly_y1_re, butterfly_y1_im};
        end

        if (state == STATE_ISSUE) begin
            bank_raddr[parity6(butterfly_index0)] = butterfly_index0[5:1];
            bank_raddr[parity6(butterfly_index1)] = butterfly_index1[5:1];
        end else begin
            bank_raddr[0] = next_output_index[5:1];
            bank_raddr[1] = next_output_index[5:1];
        end
    end

    ofdm_ifft_butterfly #(.PIPELINED(PIPELINED)) butterfly (
        .clk(clk),
        .resetn(resetn),
        .valid_in((BRAM_MEMORY != 0) ? issue_q : (state == STATE_ISSUE)),
        .a_re((BRAM_MEMORY != 0) ? op_a[31:16] : memory_re[butterfly_index0]),
        .a_im((BRAM_MEMORY != 0) ? op_a[15:0]  : memory_im[butterfly_index0]),
        .b_re((BRAM_MEMORY != 0) ? op_b[31:16] : memory_re[butterfly_index1]),
        .b_im((BRAM_MEMORY != 0) ? op_b[15:0]  : memory_im[butterfly_index1]),
        .w_re((BRAM_MEMORY != 0) ? tw_re_q : twiddle_re_q15(twiddle_index)),
        .w_im((BRAM_MEMORY != 0) ? tw_im_q : twiddle_im_q15(twiddle_index)),
        .valid_out(butterfly_valid_out),
        .y0_re(butterfly_y0_re),
        .y0_im(butterfly_y0_im),
        .y1_re(butterfly_y1_re),
        .y1_im(butterfly_y1_im),
        .saturation_count(butterfly_saturation_count)
    );

    assign bin_ready = (state == STATE_LOAD);
    assign sample_valid = (state == STATE_OUTPUT);
    wire [31:0] bank_sample = parity6(output_index) ? bank_rdata1 : bank_rdata0;
    assign sample_re = (BRAM_MEMORY != 0) ? bank_sample[31:16] : memory_re[output_index];
    assign sample_im = (BRAM_MEMORY != 0) ? bank_sample[15:0]  : memory_im[output_index];
    assign sample_index = output_index;
    assign sample_last = sample_valid && (output_index == 6'd63);
    assign busy = (state == STATE_ISSUE) || (state == STATE_WAIT) || (state == STATE_DRAIN) ||
                  (state == STATE_PREP);

    always @(posedge clk) begin
        if (!resetn) begin
            state <= STATE_LOAD;
            input_index <= 6'd0;
            stage <= 3'd0;
            group_base <= 6'd0;
            butterfly_j <= 5'd0;
            output_index <= 6'd0;
            total_saturation_count <= 16'd0;
            in_flight <= 3'd0;
            issue_q <= 1'b0;
            bank_sel_q <= 1'b0;
        end else begin
            // BRAM: operands and twiddle of the butterfly issued last clock.
            issue_q <= (state == STATE_ISSUE);
            bank_sel_q <= parity6(butterfly_index0);
            tw_re_q <= twiddle_re_q15(twiddle_index);
            tw_im_q <= twiddle_im_q15(twiddle_index);

            if (PIPELINED != 0) begin
                // Address delay line, aligned with the butterfly pipeline.
                wb_index0[0] <= butterfly_index0;
                wb_index1[0] <= butterfly_index1;
                for (wb_k = 1; wb_k < WB_DELAY; wb_k = wb_k + 1) begin
                    wb_index0[wb_k] <= wb_index0[wb_k - 1];
                    wb_index1[wb_k] <= wb_index1[wb_k - 1];
                end
                // Write back whatever leaves the pipeline (BRAM: see the banks).
                if (butterfly_valid_out) begin
                    if (BRAM_MEMORY == 0) begin
                        memory_re[wb_index0[WB_DELAY-1]] <= butterfly_y0_re;
                        memory_im[wb_index0[WB_DELAY-1]] <= butterfly_y0_im;
                        memory_re[wb_index1[WB_DELAY-1]] <= butterfly_y1_re;
                        memory_im[wb_index1[WB_DELAY-1]] <= butterfly_y1_im;
                    end
                    total_saturation_count <=
                        total_saturation_count + butterfly_saturation_count;
                end
                in_flight <= in_flight + {2'd0, (state == STATE_ISSUE)}
                                       - {2'd0, butterfly_valid_out};
            end

            case (state)
                STATE_LOAD: begin
                    if (bin_valid) begin
                        if (BRAM_MEMORY == 0) begin
                            memory_re[bit_reverse6(input_index)] <= bin_re;
                            memory_im[bit_reverse6(input_index)] <= bin_im;
                        end

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
                    if (PIPELINED == 0) begin
                        state <= STATE_WAIT;
                    end else if (last_butterfly_of_stage) begin
                        butterfly_j <= 5'd0;
                        group_base <= 6'd0;
                        state <= STATE_DRAIN;
                    end else if ({1'b0, butterfly_j} == (half_size - 6'd1)) begin
                        butterfly_j <= 5'd0;
                        group_base <= group_base + span_size[5:0];
                    end else begin
                        butterfly_j <= butterfly_j + 5'd1;
                    end
                end

                STATE_DRAIN: begin
                    // The next stage reads what this stage writes: wait until
                    // the stage's last result has been written back.
                    if (in_flight == 3'd0) begin
                        if (stage == 3'd5) begin
                            output_index <= 6'd0;
                            state <= (BRAM_MEMORY != 0) ? STATE_PREP : STATE_OUTPUT;
                        end else begin
                            stage <= stage + 3'd1;
                            state <= STATE_ISSUE;
                        end
                    end
                end

                STATE_WAIT: begin
                    if (PIPELINED == 0 && butterfly_valid_out) begin
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

                STATE_PREP: begin
                    // Block RAM: sample 0 is read on this edge.
                    state <= STATE_OUTPUT;
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
