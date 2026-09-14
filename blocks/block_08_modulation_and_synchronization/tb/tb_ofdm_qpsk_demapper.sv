`timescale 1ns/1ps

module tb_ofdm_qpsk_demapper;
    reg resetn = 1'b0;
    reg symbol_valid = 1'b0;
    wire symbol_ready;
    reg signed [15:0] symbol_re = 16'sd0;
    reg signed [15:0] symbol_im = 16'sd0;
    reg [5:0] data_index = 6'd0;
    reg symbol_last = 1'b0;

    wire bits_valid;
    reg bits_ready = 1'b0;
    wire [1:0] bits_out;
    wire [5:0] bits_index;
    wire bits_last;

    integer errors = 0;

    ofdm_qpsk_demapper dut (
        .resetn(resetn),
        .symbol_valid(symbol_valid), .symbol_ready(symbol_ready),
        .symbol_re(symbol_re), .symbol_im(symbol_im),
        .data_index(data_index), .symbol_last(symbol_last),
        .bits_valid(bits_valid), .bits_ready(bits_ready),
        .bits_out(bits_out), .bits_index(bits_index), .bits_last(bits_last)
    );

    task automatic check_symbol;
        input signed [15:0] re_value;
        input signed [15:0] im_value;
        input [1:0] expected_bits;
        input [5:0] expected_index;
        input expected_last;
        begin
            symbol_re = re_value;
            symbol_im = im_value;
            data_index = expected_index;
            symbol_last = expected_last;
            symbol_valid = 1'b1;
            bits_ready = 1'b1;
            #1;

            if (!symbol_ready || !bits_valid ||
                bits_out !== expected_bits ||
                bits_index !== expected_index ||
                bits_last !== expected_last) begin
                $display("FAIL re=%0d im=%0d expected bits=%b got=%b", re_value, im_value, expected_bits, bits_out);
                errors = errors + 1;
            end
            symbol_valid = 1'b0;
            #1;
        end
    endtask

    initial begin
        #1;
        if (symbol_ready || bits_valid) begin
            $display("FAIL outputs active during reset");
            errors = errors + 1;
        end

        resetn = 1'b1;
        check_symbol(16'sd23170,  16'sd23170, 2'b00, 6'd0, 1'b0);
        check_symbol(16'sd23170, -16'sd23170, 2'b01, 6'd1, 1'b0);
        check_symbol(-16'sd23170, 16'sd23170, 2'b10, 6'd46, 1'b0);
        check_symbol(-16'sd23170,-16'sd23170, 2'b11, 6'd47, 1'b1);
        check_symbol(16'sd0, 16'sd0, 2'b00, 6'd12, 1'b0);

        // Backpressure: decision and metadata must remain visible and stable
        // while the upstream symbol is held.
        symbol_re = -16'sd100;
        symbol_im = 16'sd200;
        data_index = 6'd17;
        symbol_last = 1'b1;
        symbol_valid = 1'b1;
        bits_ready = 1'b0;
        #1;
        if (symbol_ready || !bits_valid || bits_out !== 2'b10 ||
            bits_index !== 6'd17 || !bits_last) begin
            $display("FAIL backpressure contract");
            errors = errors + 1;
        end
        bits_ready = 1'b1;
        #1;
        if (!symbol_ready || bits_out !== 2'b10) begin
            $display("FAIL release from backpressure");
            errors = errors + 1;
        end

        if (errors == 0)
            $display("PASS: OFDM QPSK demapper matches mapper/Python sign convention");
        else begin
            $display("FAIL: OFDM QPSK demapper errors=%0d", errors);
            $fatal(1);
        end
        $finish;
    end
endmodule
