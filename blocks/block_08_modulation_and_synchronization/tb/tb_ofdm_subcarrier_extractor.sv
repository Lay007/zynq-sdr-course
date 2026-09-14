`timescale 1ns/1ps

module tb_ofdm_subcarrier_extractor;
    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg resetn = 1'b0;
    reg bin_valid = 1'b0;
    wire bin_ready;
    reg signed [15:0] bin_re = 16'sd0;
    reg signed [15:0] bin_im = 16'sd0;
    reg [5:0] bin_index = 6'd0;
    reg bin_last = 1'b0;

    wire data_valid;
    reg data_ready = 1'b0;
    wire signed [15:0] data_re;
    wire signed [15:0] data_im;
    wire [5:0] data_bin_index;
    wire [5:0] data_index;
    wire data_last;

    wire pilot_valid;
    reg pilot_ready = 1'b0;
    wire signed [15:0] pilot_re;
    wire signed [15:0] pilot_im;
    wire [5:0] pilot_bin_index;
    wire [1:0] pilot_slot;
    wire signed [15:0] pilot_ref_re;

    integer cycle_count = 0;
    integer data_count = 0;
    integer pilot_count = 0;
    integer errors = 0;
    integer b;

    ofdm_subcarrier_extractor dut (
        .resetn(resetn),
        .bin_valid(bin_valid), .bin_ready(bin_ready),
        .bin_re(bin_re), .bin_im(bin_im),
        .bin_index(bin_index), .bin_last(bin_last),
        .data_valid(data_valid), .data_ready(data_ready),
        .data_re(data_re), .data_im(data_im),
        .data_bin_index(data_bin_index), .data_index(data_index),
        .data_last(data_last),
        .pilot_valid(pilot_valid), .pilot_ready(pilot_ready),
        .pilot_re(pilot_re), .pilot_im(pilot_im),
        .pilot_bin_index(pilot_bin_index), .pilot_slot(pilot_slot),
        .pilot_ref_re(pilot_ref_re)
    );

    function automatic is_pilot_bin;
        input integer idx;
        begin
            is_pilot_bin = (idx == 43) || (idx == 57) ||
                           (idx == 7) || (idx == 21);
        end
    endfunction

    function automatic is_null_bin;
        input integer idx;
        begin
            is_null_bin = (idx == 0) || ((idx >= 27) && (idx <= 37));
        end
    endfunction

    function automatic [5:0] expected_data_index;
        input integer idx;
        begin
            if ((idx >= 1) && (idx <= 6))
                expected_data_index = idx + 23;
            else if ((idx >= 8) && (idx <= 20))
                expected_data_index = idx + 22;
            else if ((idx >= 22) && (idx <= 26))
                expected_data_index = idx + 21;
            else if ((idx >= 38) && (idx <= 42))
                expected_data_index = idx - 38;
            else if ((idx >= 44) && (idx <= 56))
                expected_data_index = idx - 39;
            else
                expected_data_index = idx - 40;
        end
    endfunction

    function automatic [1:0] expected_pilot_slot;
        input integer idx;
        begin
            case (idx)
                43: expected_pilot_slot = 2'd0;
                57: expected_pilot_slot = 2'd1;
                7:  expected_pilot_slot = 2'd2;
                default: expected_pilot_slot = 2'd3;
            endcase
        end
    endfunction

    always @(posedge clk) begin
        cycle_count <= cycle_count + 1;
        if (resetn) begin
            data_ready <= (cycle_count % 3) != 0;
            pilot_ready <= (cycle_count % 4) != 1;
        end else begin
            data_ready <= 1'b0;
            pilot_ready <= 1'b0;
        end
    end

    task automatic send_and_check_bin;
        input integer idx;
        reg signed [15:0] exp_re;
        reg signed [15:0] exp_im;
        begin
            exp_re = idx * 37 - 1000;
            exp_im = 2000 - idx * 29;
            @(negedge clk);
            bin_index = idx[5:0];
            bin_re = exp_re;
            bin_im = exp_im;
            bin_last = (idx == 63);
            bin_valid = 1'b1;

            while (!bin_ready)
                @(posedge clk);
            @(posedge clk);
            #1;

            if (is_pilot_bin(idx)) begin
                if (!pilot_valid || data_valid) begin
                    $display("FAIL bin %0d: pilot/data valid classification", idx);
                    errors = errors + 1;
                end
                if ((pilot_re !== exp_re) || (pilot_im !== exp_im) ||
                    (pilot_bin_index !== idx[5:0]) ||
                    (pilot_slot !== expected_pilot_slot(idx))) begin
                    $display("FAIL bin %0d: pilot payload/slot mismatch", idx);
                    errors = errors + 1;
                end
                if ((idx == 21 && pilot_ref_re !== 16'sh8000) ||
                    (idx != 21 && pilot_ref_re !== 16'sd32767)) begin
                    $display("FAIL bin %0d: pilot reference mismatch", idx);
                    errors = errors + 1;
                end
                pilot_count = pilot_count + 1;
            end else if (!is_null_bin(idx)) begin
                if (!data_valid || pilot_valid) begin
                    $display("FAIL bin %0d: data/pilot valid classification", idx);
                    errors = errors + 1;
                end
                if ((data_re !== exp_re) || (data_im !== exp_im) ||
                    (data_bin_index !== idx[5:0]) ||
                    (data_index !== expected_data_index(idx))) begin
                    $display("FAIL bin %0d: data payload/index mismatch", idx);
                    errors = errors + 1;
                end
                if (data_last !== (idx == 63)) begin
                    $display("FAIL bin %0d: data_last mismatch", idx);
                    errors = errors + 1;
                end
                data_count = data_count + 1;
            end else if (data_valid || pilot_valid) begin
                $display("FAIL bin %0d: null carrier was forwarded", idx);
                errors = errors + 1;
            end

            @(negedge clk);
            bin_valid = 1'b0;
            bin_last = 1'b0;
        end
    endtask

    initial begin
        repeat (3) @(posedge clk);
        resetn = 1'b1;
        repeat (2) @(posedge clk);

        for (b = 0; b < 64; b = b + 1)
            send_and_check_bin(b);

        if (data_count != 48) begin
            $display("FAIL expected 48 data carriers, got %0d", data_count);
            errors = errors + 1;
        end
        if (pilot_count != 4) begin
            $display("FAIL expected 4 pilots, got %0d", pilot_count);
            errors = errors + 1;
        end

        if (errors == 0)
            $display("PASS: OFDM subcarrier extractor classified 48 data + 4 pilots under backpressure");
        else begin
            $display("FAIL: OFDM subcarrier extractor errors=%0d", errors);
            $fatal(1);
        end
        $finish;
    end
endmodule
