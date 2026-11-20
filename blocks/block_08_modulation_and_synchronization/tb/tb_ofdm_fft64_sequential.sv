`timescale 1ns/1ps

module tb_ofdm_fft64_sequential;
    reg clk = 1'b0;
    reg resetn = 1'b0;

    reg sample_valid = 1'b0;
    wire sample_ready;
    reg signed [15:0] sample_re = 16'sd0;
    reg signed [15:0] sample_im = 16'sd0;

    wire bin_valid;
    reg bin_ready = 1'b0;
    wire signed [15:0] bin_re;
    wire signed [15:0] bin_im;
    wire [5:0] bin_index;
    wire bin_last;
    wire busy;
    wire [15:0] total_saturation_count;
    wire [15:0] conjugation_saturation_count;

    reg [31:0] input_mem [0:63];
    reg [31:0] expected_mem [0:63];

    integer input_index = 0;
    integer output_index = 0;
    integer cycles = 0;
    integer errors = 0;
    integer first_input, last_input, first_output, second_input;
    integer second_output;
    wire [5:0] input_bin = input_index[5:0];
    wire [5:0] output_bin = output_index[5:0];
    reg continuous;
    reg stalled = 1'b0;
    reg [38:0] held_bin;

    ofdm_fft64_sequential dut (
        .clk(clk),
        .resetn(resetn),
        .sample_valid(sample_valid),
        .sample_ready(sample_ready),
        .sample_re(sample_re),
        .sample_im(sample_im),
        .bin_valid(bin_valid),
        .bin_ready(bin_ready),
        .bin_re(bin_re),
        .bin_im(bin_im),
        .bin_index(bin_index),
        .bin_last(bin_last),
        .busy(busy),
        .total_saturation_count(total_saturation_count),
        .conjugation_saturation_count(conjugation_saturation_count)
    );

    always #5 clk = ~clk;

    initial begin
        continuous = $test$plusargs("continuous");
        $readmemh("verification/vectors/block08_ofdm_ifft_bin1_expected.mem", input_mem);
        $readmemh("verification/vectors/block08_ofdm_fft_bin1_expected.mem", expected_mem);
    end

    always @(negedge clk) begin
        if (!resetn) begin
            sample_valid = 1'b0;
            bin_ready = 1'b0;
        end else begin
            // Exercise both input bubbles and output backpressure.
            if (input_index < 128) begin
                sample_valid = continuous || ((cycles % 4) != 1);
                sample_re = $signed(input_mem[input_bin][31:16]);
                sample_im = $signed(input_mem[input_bin][15:0]);
            end else begin
                sample_valid = 1'b0;
                sample_re = 16'sd0;
                sample_im = 16'sd0;
            end

            bin_ready = continuous || ((cycles % 5) != 2);
            cycles = cycles + 1;
        end
    end

    always @(posedge clk) begin
        if (resetn) begin
            if (stalled && (!bin_valid || {bin_re, bin_im, bin_index, bin_last} !== held_bin))
                $fatal(1, "FFT bin changed during output backpressure");
            stalled = bin_valid && !bin_ready;
            held_bin = {bin_re, bin_im, bin_index, bin_last};
            if (sample_valid && sample_ready) begin
                case (input_index)
                    0: first_input = cycles;
                    63: last_input = cycles;
                    64: second_input = cycles;
                endcase
                input_index = input_index + 1;
            end

            if (bin_valid && bin_ready) begin
                if (output_index == 0) first_output = cycles;
                if (output_index == 64) second_output = cycles;
                if (bin_index !== output_bin) begin
                    $display("FAIL bin_index: got %0d expected %0d", bin_index, output_index);
                    errors = errors + 1;
                end
                if (bin_re !== $signed(expected_mem[output_bin][31:16])) begin
                    $display(
                        "FAIL bin_re[%0d]: got %0d expected %0d",
                        output_index,
                        bin_re,
                        $signed(expected_mem[output_bin][31:16])
                    );
                    errors = errors + 1;
                end
                if (bin_im !== $signed(expected_mem[output_bin][15:0])) begin
                    $display(
                        "FAIL bin_im[%0d]: got %0d expected %0d",
                        output_index,
                        bin_im,
                        $signed(expected_mem[output_bin][15:0])
                    );
                    errors = errors + 1;
                end
                if (bin_last !== (output_bin == 63)) begin
                    $display("FAIL bin_last[%0d]: got %0b", output_index, bin_last);
                    errors = errors + 1;
                end
                if (bin_last && (total_saturation_count != 0 || conjugation_saturation_count != 0))
                    $fatal(1, "Unexpected saturation in frame %0d", output_index / 64);
                output_index = output_index + 1;
            end

            if (output_index == 128) begin
                if (input_index != 128) begin
                    $display("FAIL input count: got %0d expected 128", input_index);
                    errors = errors + 1;
                end
                if (total_saturation_count != 0) begin
                    $display("FAIL total saturation count: %0d", total_saturation_count);
                    errors = errors + 1;
                end
                if (conjugation_saturation_count != 0) begin
                    $display(
                        "FAIL conjugation saturation count: %0d",
                        conjugation_saturation_count
                    );
                    errors = errors + 1;
                end

                if (errors != 0)
                    $fatal(1, "FAIL tb_ofdm_fft64_sequential with %0d errors", errors);
                if (continuous) begin
                    if (first_output - first_input != second_output - second_input)
                        $fatal(1, "FFT frame-to-frame latency changed");
                    $display("FFT bins=%0d latency=%0d last_in_to_first_out=%0d frame_ii=%0d",
                             output_index, first_output-first_input,
                             first_output-last_input, second_input-first_input);
                end
                $display("PASS tb_ofdm_fft64_sequential");
                $finish;
            end

            if (cycles > 1600) begin
                $fatal(1,
                    "FAIL timeout input=%0d output=%0d busy=%0b",
                    input_index,
                    output_index,
                    busy
                );
            end
        end
    end

    initial begin
        repeat (3) @(negedge clk);
        #1;
        resetn = 1'b1;
    end
endmodule
