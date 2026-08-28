`timescale 1ns/1ps

module tb_ofdm_qpsk_mapper;

    reg clk = 1'b0;
    reg resetn = 1'b0;
    reg valid_in = 1'b0;
    reg [1:0] bits_in = 2'b00;
    wire valid_out;
    wire signed [15:0] i_out;
    wire signed [15:0] q_out;

    integer errors = 0;

    always #5 clk = ~clk;

    ofdm_qpsk_mapper dut (
        .clk       (clk),
        .resetn    (resetn),
        .valid_in  (valid_in),
        .bits_in   (bits_in),
        .valid_out (valid_out),
        .i_out     (i_out),
        .q_out     (q_out)
    );

    task automatic check_int(
        input string label,
        input integer actual,
        input integer expected
    );
        begin
            if (actual !== expected) begin
                $display("FAIL %-52s actual=%0d expected=%0d", label, actual, expected);
                errors = errors + 1;
            end else begin
                $display("PASS %-52s value=%0d", label, actual);
            end
        end
    endtask

    task automatic drive_and_check(
        input [1:0] bits,
        input integer expected_i,
        input integer expected_q,
        input string label
    );
        begin
            @(negedge clk);
            bits_in = bits;
            valid_in = 1'b1;
            @(posedge clk);
            #1;
            check_int({label, " valid"}, valid_out, 1);
            check_int({label, " I"}, $signed(i_out), expected_i);
            check_int({label, " Q"}, $signed(q_out), expected_q);
        end
    endtask

    initial begin
        repeat (2) @(posedge clk);
        #1;
        check_int("valid reset", valid_out, 0);
        check_int("I reset", $signed(i_out), 0);
        check_int("Q reset", $signed(q_out), 0);

        @(negedge clk);
        resetn = 1'b1;

        // The four checks are intentionally back-to-back with valid_in held
        // high between symbols. This proves one QPSK symbol per clock after
        // the fixed one-clock pipeline latency.
        drive_and_check(2'b00,  23170,  23170, "bits 00 maps to +I +Q");
        drive_and_check(2'b01,  23170, -23170, "bits 01 maps to +I -Q");
        drive_and_check(2'b10, -23170,  23170, "bits 10 maps to -I +Q");
        drive_and_check(2'b11, -23170, -23170, "bits 11 maps to -I -Q");

        @(negedge clk);
        valid_in = 1'b0;
        bits_in = 2'b00;
        @(posedge clk);
        #1;
        check_int("valid gap emits no symbol", valid_out, 0);
        check_int("valid gap holds previous I", $signed(i_out), -23170);
        check_int("valid gap holds previous Q", $signed(q_out), -23170);

        // A synchronous reset wins over an otherwise accepted input and clears
        // both the response pulse and data registers at the active edge.
        @(negedge clk);
        valid_in = 1'b1;
        bits_in = 2'b00;
        resetn = 1'b0;
        @(posedge clk);
        #1;
        check_int("reset suppresses accepted valid", valid_out, 0);
        check_int("reset clears I", $signed(i_out), 0);
        check_int("reset clears Q", $signed(q_out), 0);

        @(negedge clk);
        valid_in = 1'b0;
        resetn = 1'b1;
        @(posedge clk);
        #1;
        check_int("post-reset idle stays invalid", valid_out, 0);

        if (errors == 0) begin
            $display("PASS tb_ofdm_qpsk_mapper");
            $finish;
        end

        $display("FAIL tb_ofdm_qpsk_mapper errors=%0d", errors);
        $fatal(1);
    end

endmodule
