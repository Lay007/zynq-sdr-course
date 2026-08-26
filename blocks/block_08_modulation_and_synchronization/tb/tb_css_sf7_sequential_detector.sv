`timescale 1ns/1ps

module tb_css_sf7_sequential_detector;

    localparam integer N = 128;
    localparam integer MAX_RESULT_CYCLES = 17000;
    localparam integer EXPECTED_RESULT_CYCLES = 16644;

    reg clk = 1'b0;
    reg resetn = 1'b0;
    reg valid_in = 1'b0;
    reg signed [15:0] iq_re = 16'sd0;
    reg signed [15:0] iq_im = 16'sd0;

    wire ready;
    wire busy;
    wire done;
    wire [6:0] peak_bin;
    wire [6:0] second_bin;
    wire signed [63:0] peak_magnitude_squared;
    wire signed [63:0] second_magnitude_squared;
    wire [15:0] dechirp_overflow_count;

    integer input_file;
    integer expected_file;
    integer meta_file;
    integer case_count;
    integer case_index;
    integer sample_index;
    integer input_re;
    integer input_im;
    integer expected_peak;
    integer expected_second;
    integer expected_overflow;
    integer scan_count;
    integer wait_cycles;
    integer errors = 0;

    always #5 clk = ~clk;

    css_sf7_sequential_detector dut (
        .clk                        (clk),
        .resetn                     (resetn),
        .valid_in                   (valid_in),
        .ready                      (ready),
        .iq_re                      (iq_re),
        .iq_im                      (iq_im),
        .busy                       (busy),
        .done                       (done),
        .peak_bin                   (peak_bin),
        .second_bin                 (second_bin),
        .peak_magnitude_squared     (peak_magnitude_squared),
        .second_magnitude_squared  (second_magnitude_squared),
        .dechirp_overflow_count     (dechirp_overflow_count)
    );

    task automatic fail;
        input [511:0] message;
        begin
            $display("FAIL %0s", message);
            errors = errors + 1;
        end
    endtask

    initial begin
        input_file = $fopen(
            "blocks/block_08_modulation_and_synchronization/tb/vectors/css_sf7_detector_input.txt",
            "r"
        );
        expected_file = $fopen(
            "blocks/block_08_modulation_and_synchronization/tb/vectors/css_sf7_detector_expected.txt",
            "r"
        );
        meta_file = $fopen(
            "blocks/block_08_modulation_and_synchronization/tb/vectors/css_sf7_detector_meta.txt",
            "r"
        );
        if (input_file == 0 || expected_file == 0 || meta_file == 0) begin
            $display("FAIL missing generated SF7 detector vectors");
            $fatal(1);
        end

        scan_count = $fscanf(meta_file, "%d", case_count);
        if (scan_count != 1 || case_count < 128) begin
            $display("FAIL invalid vector metadata count=%0d", case_count);
            $fatal(1);
        end
        $fclose(meta_file);

        repeat (3) @(posedge clk);
        if (ready !== 1'b0 || busy !== 1'b0 || done !== 1'b0)
            fail("reset outputs are not idle");

        @(negedge clk);
        resetn = 1'b1;
        @(posedge clk);
        #1;
        if (ready !== 1'b1 || busy !== 1'b0 || done !== 1'b0)
            fail("detector did not enter idle LOAD state after reset");

        for (case_index = 0; case_index < case_count; case_index = case_index + 1) begin
            for (sample_index = 0; sample_index < N; sample_index = sample_index + 1) begin
                scan_count = $fscanf(input_file, "%d %d", input_re, input_im);
                if (scan_count != 2) begin
                    $display(
                        "FAIL truncated input vectors case=%0d sample=%0d",
                        case_index,
                        sample_index
                    );
                    $fatal(1);
                end

                @(negedge clk);
                if (ready !== 1'b1) begin
                    $display(
                        "FAIL detector deasserted ready during case=%0d sample=%0d",
                        case_index,
                        sample_index
                    );
                    $fatal(1);
                end
                valid_in = 1'b1;
                iq_re = input_re;
                iq_im = input_im;
            end

            @(negedge clk);
            valid_in = 1'b0;
            iq_re = 16'sd0;
            iq_im = 16'sd0;

            wait_cycles = 0;
            while (done !== 1'b1 && wait_cycles < MAX_RESULT_CYCLES) begin
                @(posedge clk);
                #1;
                wait_cycles = wait_cycles + 1;
            end
            if (done !== 1'b1) begin
                $display("FAIL detector timeout on case=%0d", case_index);
                $fatal(1);
            end
            if (wait_cycles != EXPECTED_RESULT_CYCLES) begin
                $display(
                    "FAIL case=%0d result cycles actual=%0d expected=%0d",
                    case_index,
                    wait_cycles,
                    EXPECTED_RESULT_CYCLES
                );
                errors = errors + 1;
            end

            scan_count = $fscanf(
                expected_file,
                "%d %d %d",
                expected_peak,
                expected_second,
                expected_overflow
            );
            if (scan_count != 3) begin
                $display("FAIL truncated expected vectors case=%0d", case_index);
                $fatal(1);
            end

            if (peak_bin !== expected_peak[6:0]) begin
                $display(
                    "FAIL case=%0d peak actual=%0d expected=%0d",
                    case_index,
                    peak_bin,
                    expected_peak
                );
                errors = errors + 1;
            end
            if (second_bin !== expected_second[6:0]) begin
                $display(
                    "FAIL case=%0d second actual=%0d expected=%0d",
                    case_index,
                    second_bin,
                    expected_second
                );
                errors = errors + 1;
            end
            if (dechirp_overflow_count !== expected_overflow[15:0]) begin
                $display(
                    "FAIL case=%0d overflow actual=%0d expected=%0d",
                    case_index,
                    dechirp_overflow_count,
                    expected_overflow
                );
                errors = errors + 1;
            end
            if (peak_magnitude_squared <= second_magnitude_squared) begin
                $display(
                    "FAIL case=%0d peak magnitude=%0d second magnitude=%0d",
                    case_index,
                    peak_magnitude_squared,
                    second_magnitude_squared
                );
                errors = errors + 1;
            end
        end

        $fclose(input_file);
        $fclose(expected_file);

        if (errors == 0) begin
            $display(
                "PASS tb_css_sf7_sequential_detector cases=%0d samples=%0d result_cycles=%0d",
                case_count,
                case_count * N,
                EXPECTED_RESULT_CYCLES
            );
        end else begin
            $display("FAIL tb_css_sf7_sequential_detector errors=%0d", errors);
            $fatal(1);
        end

        $finish;
    end

endmodule
