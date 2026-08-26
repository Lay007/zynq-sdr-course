`timescale 1ns/1ps

module tb_css_symbol_buffer;

    localparam integer DEPTH = 8;
    localparam integer ADDR_WIDTH = 3;

    reg clk = 1'b0;
    reg resetn = 1'b0;
    reg valid_in = 1'b0;
    reg signed [15:0] iq_re = 16'sd0;
    reg signed [15:0] iq_im = 16'sd0;
    reg release_buffer = 1'b0;
    reg [ADDR_WIDTH-1:0] read_addr = {ADDR_WIDTH{1'b0}};

    wire ready;
    wire symbol_complete;
    wire full;
    wire [ADDR_WIDTH:0] accepted_count;
    wire signed [15:0] read_re;
    wire signed [15:0] read_im;

    integer i;
    integer errors = 0;

    always #5 clk = ~clk;

    css_symbol_buffer #(
        .DEPTH(DEPTH),
        .ADDR_WIDTH(ADDR_WIDTH)
    ) dut (
        .clk(clk),
        .resetn(resetn),
        .valid_in(valid_in),
        .ready(ready),
        .iq_re(iq_re),
        .iq_im(iq_im),
        .release_buffer(release_buffer),
        .symbol_complete(symbol_complete),
        .full(full),
        .accepted_count(accepted_count),
        .read_addr(read_addr),
        .read_re(read_re),
        .read_im(read_im)
    );

    task automatic check_bit;
        input [511:0] label;
        input actual;
        input expected;
        begin
            if (actual !== expected) begin
                $display("FAIL %0s actual=%0d expected=%0d", label, actual, expected);
                errors = errors + 1;
            end else begin
                $display("PASS %0s value=%0d", label, actual);
            end
        end
    endtask

    task automatic check_int;
        input [511:0] label;
        input integer actual;
        input integer expected;
        begin
            if (actual !== expected) begin
                $display("FAIL %0s actual=%0d expected=%0d", label, actual, expected);
                errors = errors + 1;
            end else begin
                $display("PASS %0s value=%0d", label, actual);
            end
        end
    endtask

    task automatic send_sample;
        input integer re_value;
        input integer im_value;
        begin
            @(negedge clk);
            valid_in = 1'b1;
            iq_re = re_value;
            iq_im = im_value;
            @(posedge clk);
            #1;
            @(negedge clk);
            valid_in = 1'b0;
            iq_re = 16'sd0;
            iq_im = 16'sd0;
        end
    endtask

    task automatic pulse_release;
        begin
            @(negedge clk);
            release_buffer = 1'b1;
            @(posedge clk);
            #1;
            @(negedge clk);
            release_buffer = 1'b0;
        end
    endtask

    initial begin
        repeat (3) @(posedge clk);
        #1;
        check_bit("ready stays low in reset", ready, 1'b0);
        check_bit("full reset", full, 1'b0);
        check_bit("symbol complete reset", symbol_complete, 1'b0);
        check_int("accepted count reset", accepted_count, 0);

        @(negedge clk);
        resetn = 1'b1;
        @(posedge clk);
        #1;
        check_bit("ready after reset", ready, 1'b1);

        repeat (3) @(posedge clk);
        #1;
        check_int("valid gaps do not advance count", accepted_count, 0);

        for (i = 0; i < 4; i = i + 1)
            send_sample(100 + i, -100 - i);
        check_int("four accepted samples counted", accepted_count, 4);
        check_bit("partial symbol is not full", full, 1'b0);

        repeat (2) @(posedge clk);
        #1;
        check_int("idle gap preserves partial symbol", accepted_count, 4);

        for (i = 4; i < DEPTH; i = i + 1)
            send_sample(100 + i, -100 - i);

        check_bit("buffer full after eighth accepted sample", full, 1'b1);
        check_bit("ready deasserts while full", ready, 1'b0);
        check_int("accepted count reaches depth", accepted_count, DEPTH);
        check_bit("symbol complete pulses on last sample", symbol_complete, 1'b1);

        @(posedge clk);
        #1;
        check_bit("symbol complete is one-cycle pulse", symbol_complete, 1'b0);

        for (i = 0; i < DEPTH; i = i + 1) begin
            read_addr = i[ADDR_WIDTH-1:0];
            #1;
            check_int("stored real sample", read_re, 100 + i);
            check_int("stored imag sample", read_im, -100 - i);
        end

        // Holding valid while ready=0 is legal backpressure, not a transfer.
        @(negedge clk);
        valid_in = 1'b1;
        iq_re = 16'sd777;
        iq_im = -16'sd777;
        repeat (2) @(posedge clk);
        #1;
        check_int("backpressure prevents extra accepted sample", accepted_count, DEPTH);
        check_bit("backpressure does not retrigger completion", symbol_complete, 1'b0);
        @(negedge clk);
        valid_in = 1'b0;

        read_addr = 3'd0;
        #1;
        check_int("full buffer is not overwritten while stalled", read_re, 100);

        pulse_release();
        check_bit("release clears full", full, 1'b0);
        check_bit("release re-enables ready", ready, 1'b1);
        check_int("release clears accepted count", accepted_count, 0);

        // Reset in the middle of a new symbol must discard the partial frame.
        send_sample(500, -500);
        send_sample(501, -501);
        send_sample(502, -502);
        check_int("second symbol partial count", accepted_count, 3);

        @(negedge clk);
        resetn = 1'b0;
        @(posedge clk);
        #1;
        check_bit("mid-symbol reset clears full", full, 1'b0);
        check_int("mid-symbol reset discards partial count", accepted_count, 0);
        check_bit("mid-symbol reset suppresses ready", ready, 1'b0);

        @(negedge clk);
        resetn = 1'b1;
        @(posedge clk);
        #1;
        check_bit("ready recovers after mid-symbol reset", ready, 1'b1);

        for (i = 0; i < DEPTH; i = i + 1)
            send_sample(200 + i, -200 - i);

        check_bit("fresh full symbol succeeds after reset", full, 1'b1);
        check_int("fresh symbol count reaches depth", accepted_count, DEPTH);
        for (i = 0; i < DEPTH; i = i + 1) begin
            read_addr = i[ADDR_WIDTH-1:0];
            #1;
            check_int("fresh real sample after reset", read_re, 200 + i);
            check_int("fresh imag sample after reset", read_im, -200 - i);
        end

        if (errors == 0) begin
            $display("PASS tb_css_symbol_buffer");
        end else begin
            $display("FAIL tb_css_symbol_buffer errors=%0d", errors);
            $fatal(1);
        end
        $finish;
    end

endmodule
