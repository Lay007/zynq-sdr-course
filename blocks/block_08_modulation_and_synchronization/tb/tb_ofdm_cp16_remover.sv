`timescale 1ns/1ps

module tb_ofdm_cp16_remover;
    reg clk = 1'b0;
    reg resetn = 1'b0;

    reg signed [15:0] in_i = 16'sd0;
    reg signed [15:0] in_q = 16'sd0;
    reg in_valid = 1'b0;
    wire in_ready;
    reg in_last = 1'b0;

    wire signed [15:0] out_i;
    wire signed [15:0] out_q;
    wire out_valid;
    reg out_ready = 1'b0;
    wire out_last;
    wire frame_error;

    integer errors = 0;
    integer input_index = 0;
    integer output_index = 0;
    integer cycles = 0;

    ofdm_cp16_remover dut (
        .clk(clk),
        .resetn(resetn),
        .in_i(in_i),
        .in_q(in_q),
        .in_valid(in_valid),
        .in_ready(in_ready),
        .in_last(in_last),
        .out_i(out_i),
        .out_q(out_q),
        .out_valid(out_valid),
        .out_ready(out_ready),
        .out_last(out_last),
        .frame_error(frame_error)
    );

    always #5 clk = ~clk;

    task drive_input;
        integer payload_index;
        begin
            if (input_index < 80) begin
                in_valid = 1'b1;
                in_last = (input_index == 79);
                if (input_index < 16) begin
                    in_i = 16'sd1000 + input_index;
                    in_q = -16'sd1000 - input_index;
                end else begin
                    payload_index = input_index - 16;
                    in_i = payload_index;
                    in_q = -payload_index;
                end
            end else begin
                in_valid = 1'b0;
                in_last = 1'b0;
                in_i = 16'sd0;
                in_q = 16'sd0;
            end
        end
    endtask

    always @(negedge clk) begin
        if (!resetn) begin
            in_valid = 1'b0;
            in_last = 1'b0;
            out_ready = 1'b0;
        end else begin
            // Deterministic backpressure: useful payload stalls every fourth cycle.
            out_ready = ((cycles % 4) != 1);
            drive_input();
            cycles = cycles + 1;
        end
    end

    always @(posedge clk) begin
        if (resetn) begin
            if (frame_error) begin
                $display("FAIL unexpected frame_error at input index %0d", input_index);
                errors = errors + 1;
            end

            if (in_valid && in_ready)
                input_index = input_index + 1;

            if (out_valid && out_ready) begin
                if (out_i !== output_index) begin
                    $display("FAIL output I[%0d]: got %0d expected %0d", output_index, out_i, output_index);
                    errors = errors + 1;
                end
                if (out_q !== -output_index) begin
                    $display("FAIL output Q[%0d]: got %0d expected %0d", output_index, out_q, -output_index);
                    errors = errors + 1;
                end
                if (out_last !== (output_index == 63)) begin
                    $display("FAIL out_last[%0d]: got %0b", output_index, out_last);
                    errors = errors + 1;
                end
                output_index = output_index + 1;
            end

            if (output_index == 64) begin
                if (input_index != 80) begin
                    $display("FAIL accepted input count: got %0d expected 80", input_index);
                    errors = errors + 1;
                end

                if (errors == 0)
                    $display("PASS tb_ofdm_cp16_remover");
                else
                    $display("FAIL tb_ofdm_cp16_remover with %0d errors", errors);
                $finish;
            end

            if (cycles > 300) begin
                $display("FAIL timeout input=%0d output=%0d", input_index, output_index);
                $finish;
            end
        end
    end

    initial begin
        repeat (3) @(posedge clk);
        resetn = 1'b1;
    end
endmodule
