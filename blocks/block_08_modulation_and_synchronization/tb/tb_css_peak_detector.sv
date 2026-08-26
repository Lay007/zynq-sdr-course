`timescale 1ns/1ps

module tb_css_peak_detector;

    localparam integer BIN_INDEX_WIDTH = 7;
    localparam integer MAG_WIDTH = 64;
    localparam [BIN_INDEX_WIDTH-1:0] LAST_BIN = 7'd7;

    reg clk = 1'b0;
    reg resetn = 1'b0;
    reg start = 1'b0;
    reg bin_valid = 1'b0;
    reg [BIN_INDEX_WIDTH-1:0] bin_index = {BIN_INDEX_WIDTH{1'b0}};
    reg signed [MAG_WIDTH-1:0] magnitude_squared = {MAG_WIDTH{1'b0}};

    wire busy;
    wire done;
    wire start_rejected;
    wire [BIN_INDEX_WIDTH-1:0] peak_bin;
    wire [BIN_INDEX_WIDTH-1:0] second_bin;
    wire signed [MAG_WIDTH-1:0] peak_magnitude_squared;
    wire signed [MAG_WIDTH-1:0] second_magnitude_squared;

    integer errors = 0;

    always #5 clk = ~clk;

    css_peak_detector #(
        .BIN_INDEX_WIDTH(BIN_INDEX_WIDTH),
        .MAG_WIDTH(MAG_WIDTH),
        .LAST_BIN(LAST_BIN)
    ) dut (
        .clk(clk),
        .resetn(resetn),
        .start(start),
        .busy(busy),
        .done(done),
        .start_rejected(start_rejected),
        .bin_valid(bin_valid),
        .bin_index(bin_index),
        .magnitude_squared(magnitude_squared),
        .peak_bin(peak_bin),
        .second_bin(second_bin),
        .peak_magnitude_squared(peak_magnitude_squared),
        .second_magnitude_squared(second_magnitude_squared)
    );

    task automatic fail;
        input [767:0] message;
        begin
            $display("FAIL %0s", message);
            errors = errors + 1;
        end
    endtask

    task automatic check_bit;
        input [767:0] label;
        input actual;
        input expected;
        begin
            if (actual !== expected) begin
                $display(
                    "FAIL %0s actual=%0d expected=%0d",
                    label,
                    actual,
                    expected
                );
                errors = errors + 1;
            end
        end
    endtask

    task automatic check_index;
        input [767:0] label;
        input [BIN_INDEX_WIDTH-1:0] actual;
        input [BIN_INDEX_WIDTH-1:0] expected;
        begin
            if (actual !== expected) begin
                $display(
                    "FAIL %0s actual=%0d expected=%0d",
                    label,
                    actual,
                    expected
                );
                errors = errors + 1;
            end
        end
    endtask

    task automatic check_magnitude;
        input [767:0] label;
        input signed [MAG_WIDTH-1:0] actual;
        input signed [MAG_WIDTH-1:0] expected;
        begin
            if (actual !== expected) begin
                $display(
                    "FAIL %0s actual=%0d expected=%0d",
                    label,
                    actual,
                    expected
                );
                errors = errors + 1;
            end
        end
    endtask

    task automatic pulse_start;
        begin
            @(negedge clk);
            start = 1'b1;
            @(posedge clk);
            #1;
            check_bit("accepted start asserts busy", busy, 1'b1);
            @(negedge clk);
            start = 1'b0;
        end
    endtask

    task automatic send_bin;
        input integer index_value;
        input integer magnitude_value;
        begin
            @(negedge clk);
            bin_valid = 1'b1;
            bin_index = index_value[BIN_INDEX_WIDTH-1:0];
            magnitude_squared = magnitude_value;
            @(posedge clk);
            #1;
            @(negedge clk);
            bin_valid = 1'b0;
            bin_index = {BIN_INDEX_WIDTH{1'b0}};
            magnitude_squared = {MAG_WIDTH{1'b0}};
        end
    endtask

    initial begin
        repeat (3) @(posedge clk);
        #1;
        check_bit("busy reset", busy, 1'b0);
        check_bit("done reset", done, 1'b0);
        check_bit("start rejected reset", start_rejected, 1'b0);
        check_index("peak bin reset", peak_bin, 7'd0);
        check_index("second bin reset", second_bin, 7'd0);
        check_magnitude("peak magnitude reset", peak_magnitude_squared, 64'sd0);
        check_magnitude(
            "second magnitude reset",
            second_magnitude_squared,
            64'sd0
        );

        @(negedge clk);
        resetn = 1'b1;
        @(posedge clk);
        #1;
        check_bit("idle after reset", busy, 1'b0);

        // An unframed bin must not alter the held result.
        send_bin(6, 999);
        check_index("idle bin ignored", peak_bin, 7'd0);
        check_magnitude("idle magnitude ignored", peak_magnitude_squared, 64'sd0);

        pulse_start();
        send_bin(0, 10);
        check_index("first bin initializes peak", peak_bin, 7'd0);
        check_magnitude("first bin magnitude", peak_magnitude_squared, 64'sd10);

        // A second start while active is rejected without clearing the frame.
        @(negedge clk);
        start = 1'b1;
        @(posedge clk);
        #1;
        check_bit("busy start rejected", start_rejected, 1'b1);
        check_bit("busy preserved after rejected start", busy, 1'b1);
        check_magnitude(
            "rejected start preserves peak",
            peak_magnitude_squared,
            64'sd10
        );
        @(negedge clk);
        start = 1'b0;
        @(posedge clk);
        #1;
        check_bit("start rejected pulse clears", start_rejected, 1'b0);

        repeat (2) @(posedge clk);
        #1;
        check_magnitude("valid gaps preserve peak", peak_magnitude_squared, 64'sd10);

        send_bin(1, 50);
        send_bin(2, 20);
        send_bin(3, 50);
        send_bin(4, 30);
        send_bin(5, 50);
        send_bin(6, 40);
        check_index("first equal maximum remains peak", peak_bin, 7'd1);
        check_index("second equal maximum uses first later tie", second_bin, 7'd3);
        check_magnitude("peak tie magnitude", peak_magnitude_squared, 64'sd50);
        check_magnitude("second tie magnitude", second_magnitude_squared, 64'sd50);

        send_bin(7, 5);
        check_bit("last bin clears busy", busy, 1'b0);
        check_bit("last bin pulses done", done, 1'b1);
        check_index("completed peak bin", peak_bin, 7'd1);
        check_index("completed second bin", second_bin, 7'd3);
        if ((^peak_bin === 1'bx) || (^second_bin === 1'bx) ||
            (^peak_magnitude_squared === 1'bx) ||
            (^second_magnitude_squared === 1'bx))
            fail("completed result contains X/Z values");

        @(posedge clk);
        #1;
        check_bit("done is a one-cycle pulse", done, 1'b0);

        // Reset in the middle of a frame must abort and clear partial results.
        pulse_start();
        send_bin(0, 100);
        send_bin(1, 90);
        @(negedge clk);
        resetn = 1'b0;
        @(posedge clk);
        #1;
        check_bit("mid-frame reset aborts busy", busy, 1'b0);
        check_bit("mid-frame reset suppresses done", done, 1'b0);
        check_index("mid-frame reset clears peak bin", peak_bin, 7'd0);
        check_magnitude(
            "mid-frame reset clears peak magnitude",
            peak_magnitude_squared,
            64'sd0
        );

        @(negedge clk);
        resetn = 1'b1;
        @(posedge clk);
        #1;
        pulse_start();
        send_bin(0, 100);
        send_bin(1, 10);
        send_bin(2, 20);
        send_bin(3, 30);
        send_bin(4, 40);
        send_bin(5, 50);
        send_bin(6, 60);
        send_bin(7, 70);
        check_bit("restart frame completes", done, 1'b1);
        check_index("restart peak bin", peak_bin, 7'd0);
        check_index("restart second bin", second_bin, 7'd7);
        check_magnitude("restart peak magnitude", peak_magnitude_squared, 64'sd100);
        check_magnitude(
            "restart second magnitude",
            second_magnitude_squared,
            64'sd70
        );

        if (errors == 0) begin
            $display("PASS tb_css_peak_detector frames=2 bins=16");
        end else begin
            $display("FAIL tb_css_peak_detector errors=%0d", errors);
            $fatal(1);
        end
        $finish;
    end

endmodule
