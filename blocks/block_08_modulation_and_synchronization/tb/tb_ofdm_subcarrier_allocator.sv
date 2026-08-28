`timescale 1ns/1ps

module tb_ofdm_subcarrier_allocator;

    reg clk = 1'b0;
    reg resetn = 1'b0;

    reg data_valid = 1'b0;
    wire data_ready;
    reg signed [15:0] data_i = 16'sd0;
    reg signed [15:0] data_q = 16'sd0;

    wire bin_valid;
    reg bin_ready = 1'b0;
    wire [5:0] bin_index;
    wire signed [15:0] bin_i;
    wire signed [15:0] bin_q;
    wire bin_last;

    integer errors = 0;
    integer idx;
    integer expected_idx;
    integer expected_i;
    integer expected_q;
    integer target_k;
    integer held_i;
    integer held_q;
    integer held_index;

    ofdm_subcarrier_allocator dut (
        .clk(clk),
        .resetn(resetn),
        .data_valid(data_valid),
        .data_ready(data_ready),
        .data_i(data_i),
        .data_q(data_q),
        .bin_valid(bin_valid),
        .bin_ready(bin_ready),
        .bin_index(bin_index),
        .bin_i(bin_i),
        .bin_q(bin_q),
        .bin_last(bin_last)
    );

    always #5 clk = ~clk;

    function integer is_pilot_k;
        input integer k;
        begin
            is_pilot_k = (k == -21) || (k == -7) || (k == 7) || (k == 21);
        end
    endfunction

    // Derive the data_k index independently from the DUT by walking the exact
    // Python ordering: -26..-1 followed by +1..+26 with pilots removed.
    function integer expected_data_index;
        input integer natural_bin;
        integer k;
        integer count;
        integer wanted_k;
        begin
            if (natural_bin <= 31)
                wanted_k = natural_bin;
            else
                wanted_k = natural_bin - 64;

            expected_data_index = -1;
            count = 0;
            for (k = -26; k <= -1; k = k + 1) begin
                if (!is_pilot_k(k)) begin
                    if (k == wanted_k)
                        expected_data_index = count;
                    count = count + 1;
                end
            end
            for (k = 1; k <= 26; k = k + 1) begin
                if (!is_pilot_k(k)) begin
                    if (k == wanted_k)
                        expected_data_index = count;
                    count = count + 1;
                end
            end
        end
    endfunction

    task expect_bit;
        input actual;
        input expected;
        input [8*64-1:0] label_text;
        begin
            if (actual !== expected) begin
                $display("FAIL %-52s actual=%0d expected=%0d", label_text, actual, expected);
                errors = errors + 1;
            end else begin
                $display("PASS %-52s value=%0d", label_text, actual);
            end
        end
    endtask

    task expect_int;
        input integer actual;
        input integer expected;
        input [8*64-1:0] label_text;
        begin
            if (actual !== expected) begin
                $display("FAIL %-52s actual=%0d expected=%0d", label_text, actual, expected);
                errors = errors + 1;
            end else begin
                $display("PASS %-52s value=%0d", label_text, actual);
            end
        end
    endtask

    task send_data_symbol;
        input integer data_number;
        begin
            @(negedge clk);
            data_valid = 1'b1;
            data_i = 16'sd1000 + data_number;
            data_q = -(16'sd2000 + data_number);
            @(posedge clk);
            #1;
            if (data_number < 47)
                expect_bit(data_ready, 1'b1, "allocator remains ready while collecting");
            else begin
                expect_bit(data_ready, 1'b0, "allocator closes input after data carrier 47");
                expect_bit(bin_valid, 1'b1, "64-bin frame becomes valid after 48 data carriers");
                expect_int(bin_index, 0, "first emitted natural bin is DC bin 0");
            end
            @(negedge clk);
            data_valid = 1'b0;
        end
    endtask

    task check_current_bin;
        input integer natural_bin;
        begin
            if (natural_bin <= 31)
                target_k = natural_bin;
            else
                target_k = natural_bin - 64;

            expected_i = 0;
            expected_q = 0;

            if ((target_k == -21) || (target_k == -7) || (target_k == 7)) begin
                expected_i = 32767;
            end else if (target_k == 21) begin
                expected_i = -32768;
            end else if ((target_k >= -26) && (target_k <= 26) && (target_k != 0)) begin
                expected_idx = expected_data_index(natural_bin);
                expected_i = 1000 + expected_idx;
                expected_q = -(2000 + expected_idx);
            end

            expect_bit(bin_valid, 1'b1, "bin_valid asserted during frame emission");
            expect_int(bin_index, natural_bin, "natural bin index");
            expect_int($signed(bin_i), expected_i, "natural bin I payload");
            expect_int($signed(bin_q), expected_q, "natural bin Q payload");
            expect_bit(bin_last, (natural_bin == 63), "bin_last only on natural bin 63");
        end
    endtask

    initial begin
        repeat (3) @(posedge clk);
        #1;
        expect_bit(data_ready, 1'b1, "reset leaves allocator ready for data");
        expect_bit(bin_valid, 1'b0, "reset leaves output invalid");
        expect_int(bin_index, 0, "reset clears output bin index");

        @(negedge clk);
        resetn = 1'b1;

        // Fill all 48 Lab 8.5 data carriers. Periodic valid gaps verify that
        // only accepted symbols advance the allocator's data order.
        for (idx = 0; idx < 48; idx = idx + 1) begin
            if ((idx == 5) || (idx == 19) || (idx == 33)) begin
                @(negedge clk);
                data_valid = 1'b0;
                @(posedge clk);
                #1;
                expect_bit(data_ready, 1'b1, "input valid gap does not close collector");
                expect_bit(bin_valid, 1'b0, "input valid gap does not emit early frame");
            end
            send_data_symbol(idx);
        end

        // First bin is deliberately stalled. All output signals must remain
        // coherent while downstream backpressure is asserted.
        bin_ready = 1'b0;
        #1;
        check_current_bin(0);
        held_i = $signed(bin_i);
        held_q = $signed(bin_q);
        held_index = bin_index;
        repeat (2) begin
            @(posedge clk);
            #1;
            expect_int(bin_index, held_index, "backpressure holds bin index");
            expect_int($signed(bin_i), held_i, "backpressure holds bin I");
            expect_int($signed(bin_q), held_q, "backpressure holds bin Q");
            expect_bit(bin_valid, 1'b1, "backpressure keeps bin_valid asserted");
        end

        // Consume the full 64-bin frequency-domain frame. Add a second stall
        // at a data bin to prove that hold behavior is not special to DC.
        for (idx = 0; idx < 64; idx = idx + 1) begin
            @(negedge clk);
            if (idx == 44) begin
                bin_ready = 1'b0;
                #1;
                check_current_bin(idx);
                held_i = $signed(bin_i);
                held_q = $signed(bin_q);
                held_index = bin_index;
                repeat (2) begin
                    @(posedge clk);
                    #1;
                    expect_int(bin_index, held_index, "mid-frame stall holds bin index");
                    expect_int($signed(bin_i), held_i, "mid-frame stall holds bin I");
                    expect_int($signed(bin_q), held_q, "mid-frame stall holds bin Q");
                end
                @(negedge clk);
            end

            bin_ready = 1'b1;
            #1;
            check_current_bin(idx);
            @(posedge clk);
            #1;
        end

        expect_bit(bin_valid, 1'b0, "frame completion drops bin_valid");
        expect_bit(data_ready, 1'b1, "frame completion rearms data collector");
        expect_int(bin_index, 0, "frame completion returns bin index to zero");

        // Reset during a partially collected next frame must discard that
        // partial frame and return to the initial collector state.
        send_data_symbol(0);
        send_data_symbol(1);
        @(negedge clk);
        resetn = 1'b0;
        data_valid = 1'b1;
        data_i = 16'sd7777;
        data_q = -16'sd7777;
        @(posedge clk);
        #1;
        expect_bit(bin_valid, 1'b0, "reset suppresses partial-frame output");
        expect_bit(data_ready, 1'b1, "reset reopens data collector");
        expect_int(bin_index, 0, "reset clears bin index after partial frame");

        @(negedge clk);
        data_valid = 1'b0;
        resetn = 1'b1;

        if (errors == 0) begin
            $display("PASS tb_ofdm_subcarrier_allocator");
        end else begin
            $display("FAIL tb_ofdm_subcarrier_allocator errors=%0d", errors);
            $fatal(1);
        end
        $finish;
    end

endmodule
