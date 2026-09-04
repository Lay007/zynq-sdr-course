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
        $readmemh("verification/vectors/block08_ofdm_ifft_bin1_expected.mem", input_mem);
        $readmemh("verification/vectors/block08_ofdm_fft_bin1_expected.mem", expected_mem);
    end

    always @(negedge clk) begin
        if (!resetn) begin
            sample_valid = 1'b0;
            bin_ready = 1'b0;
        end else begin
            // Exercise both input bubbles and output backpressure.
            if (input_index < 64) begin
                sample_valid = ((cycles % 4) != 1);
                sample_re = $signed(input_mem[input_index][31:16]);
                sample_im = $signed(input_mem[input_index][15:0]);
            end else begin
                sample_valid = 1'b0;
                sample_re = 16'sd0;
                sample_im = 16'sd0;
            end

            bin_ready = ((cycles % 5) != 2);
            cycles = cycles + 1;
        end
    end

    always @(posedge clk) begin
        if (resetn) begin
            if (sample_valid && sample_ready)
                input_index = input_index + 1;

            if (bin_valid && bin_ready) begin
                if (bin_index !== output_index[5:0]) begin
                    $display("FAIL bin_index: got %0d expected %0d", bin_index, output_index);
                    errors = errors + 1;
                end
                if (bin_re !== $signed(expected_mem[output_index][31:16])) begin
                    $display(
                        "FAIL bin_re[%0d]: got %0d expected %0d",
                        output_index,
                        bin_re,
                        $signed(expected_mem[output_index][31:16])
                    );
                    errors = errors + 1;
                end
                if (bin_im !== $signed(expected_mem[output_index][15:0])) begin
                    $display(
                        "FAIL bin_im[%0d]: got %0d expected %0d",
                        output_index,
                        bin_im,
                        $signed(expected_mem[output_index][15:0])
                    );
                    errors = errors + 1;
                end
                if (bin_last !== (output_index == 63)) begin
                    $display("FAIL bin_last[%0d]: got %0b", output_index, bin_last);
                    errors = errors + 1;
                end
                output_index = output_index + 1;
            end

            if (output_index == 64) begin
                if (input_index != 64) begin
                    $display("FAIL input count: got %0d expected 64", input_index);
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

                if (errors == 0)
                    $display("PASS tb_ofdm_fft64_sequential");
                else
                    $display("FAIL tb_ofdm_fft64_sequential with %0d errors", errors);
                $finish;
            end

            if (cycles > 1000) begin
                $display(
                    "FAIL timeout input=%0d output=%0d busy=%0b",
                    input_index,
                    output_index,
                    busy
                );
                $finish;
            end
        end
    end

    initial begin
        repeat (3) @(posedge clk);
        resetn = 1'b1;
    end
endmodule
