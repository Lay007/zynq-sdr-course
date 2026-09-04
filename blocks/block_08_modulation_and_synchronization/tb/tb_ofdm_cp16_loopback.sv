`timescale 1ns/1ps

module tb_ofdm_cp16_loopback;
    reg clk = 1'b0;
    reg resetn = 1'b0;

    reg source_valid = 1'b0;
    wire source_ready;
    reg signed [15:0] source_re = 16'sd0;
    reg signed [15:0] source_im = 16'sd0;
    reg source_last = 1'b0;

    wire cp_valid;
    wire cp_ready;
    wire signed [15:0] cp_re;
    wire signed [15:0] cp_im;
    wire cp_last;
    wire insert_error;

    wire sink_valid;
    reg sink_ready = 1'b0;
    wire signed [15:0] sink_re;
    wire signed [15:0] sink_im;
    wire sink_last;
    wire remove_error;

    integer source_index = 0;
    integer sink_index = 0;
    integer cycles = 0;
    integer errors = 0;

    ofdm_cp16_inserter u_insert (
        .clk(clk),
        .resetn(resetn),
        .in_valid(source_valid),
        .in_ready(source_ready),
        .in_re(source_re),
        .in_im(source_im),
        .in_last(source_last),
        .out_valid(cp_valid),
        .out_ready(cp_ready),
        .out_re(cp_re),
        .out_im(cp_im),
        .out_index(),
        .out_is_cp(),
        .out_last(cp_last),
        .frame_error(insert_error)
    );

    ofdm_cp16_remover u_remove (
        .clk(clk),
        .resetn(resetn),
        .in_i(cp_re),
        .in_q(cp_im),
        .in_valid(cp_valid),
        .in_ready(cp_ready),
        .in_last(cp_last),
        .out_i(sink_re),
        .out_q(sink_im),
        .out_valid(sink_valid),
        .out_ready(sink_ready),
        .out_last(sink_last),
        .frame_error(remove_error)
    );

    always #5 clk = ~clk;

    always @(negedge clk) begin
        if (!resetn) begin
            source_valid = 1'b0;
            source_last = 1'b0;
            sink_ready = 1'b0;
        end else begin
            sink_ready = ((cycles % 5) != 2);

            if (source_index < 64) begin
                source_valid = ((cycles % 3) != 1);
                source_re = 16'sd200 + source_index;
                source_im = -16'sd200 - source_index;
                source_last = (source_index == 63);
            end else begin
                source_valid = 1'b0;
                source_last = 1'b0;
            end

            cycles = cycles + 1;
        end
    end

    always @(posedge clk) begin
        if (resetn) begin
            if (source_valid && source_ready)
                source_index = source_index + 1;

            if (remove_error) begin
                $display("FAIL CP remover frame_error");
                errors = errors + 1;
            end

            if (sink_valid && sink_ready) begin
                if (insert_error) begin
                    $display("FAIL CP inserter frame_error");
                    errors = errors + 1;
                end
                if (sink_re !== (16'sd200 + sink_index)) begin
                    $display("FAIL sink I[%0d]: got %0d expected %0d", sink_index, sink_re, 200 + sink_index);
                    errors = errors + 1;
                end
                if (sink_im !== (-16'sd200 - sink_index)) begin
                    $display("FAIL sink Q[%0d]: got %0d expected %0d", sink_index, sink_im, -200 - sink_index);
                    errors = errors + 1;
                end
                if (sink_last !== (sink_index == 63)) begin
                    $display("FAIL sink_last[%0d]: got %0b", sink_index, sink_last);
                    errors = errors + 1;
                end
                sink_index = sink_index + 1;
            end

            if (sink_index == 64) begin
                if (source_index != 64) begin
                    $display("FAIL source accepted count %0d", source_index);
                    errors = errors + 1;
                end

                if (errors == 0)
                    $display("PASS tb_ofdm_cp16_loopback");
                else
                    $display("FAIL tb_ofdm_cp16_loopback with %0d errors", errors);
                $finish;
            end

            if (cycles > 500) begin
                $display("FAIL timeout source=%0d sink=%0d", source_index, sink_index);
                $finish;
            end
        end
    end

    initial begin
        repeat (3) @(posedge clk);
        resetn = 1'b1;
    end
endmodule
