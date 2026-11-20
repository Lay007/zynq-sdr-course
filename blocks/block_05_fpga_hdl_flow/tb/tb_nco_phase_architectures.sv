`timescale 1ns/1ps

module tb_nco_phase_architectures;
    parameter integer CORDIC = 0;
    localparam integer OFFSET = CORDIC ? 16 : 0;
    reg clk = 0;
    always #5 clk = !clk;
    reg rst = 1, phase_valid = 0;
    reg [31:0] phase;
    wire phase_ready, out_valid;
    wire signed [15:0] out_i, out_q;
    nco_phase_architectures #(.CORDIC(CORDIC)) dut (.*);

    integer cycle = 0, due = -1, next_ready = 0, results = 0;
    integer expected_i, expected_q, got_i, got_q;
    integer vectors, trace_file, read_count;
    reg [31:0] candidate_phase;
    reg accepted;

    task automatic tick(input bit reset, input bit valid, input [31:0] phase_word);
        begin
            @(negedge clk);
            rst = reset;
            phase_valid = valid;
            phase = phase_word;
            @(posedge clk);
            cycle = cycle + 1;
            if (phase_ready !== (!reset && cycle >= next_ready))
                $fatal(1, "Unexpected ready at cycle %0d", cycle);
            accepted = valid && phase_ready;
            if (reset) begin
                due = -1;
                next_ready = cycle + 1;
            end else if (accepted) begin
                due = cycle + OFFSET;
                next_ready = due + 1;
            end
            #1;
            if (out_valid !== (cycle == due))
                $fatal(1, "Unexpected valid at cycle %0d", cycle);
        end
    endtask

    initial begin
        vectors = $fopen("nco_vectors.txt", "r");
        trace_file = $fopen("nco_trace.txt", "w");
        if (!vectors || !trace_file) $fatal(1, "Cannot open vectors or trace");
        // Reset with an outstanding calculation, then wait past its due edge.
        tick(1, 0, 0);
        tick(0, 1, 32'h70000000);
        tick(1, 0, 0);
        repeat (18) tick(0, 0, 0);
        read_count = $fscanf(vectors, "%x %d %d", candidate_phase, expected_i, expected_q);
        while (read_count == 3) begin
            tick(0, 1, candidate_phase);
            if (!accepted) $fatal(1, "Could not accept input at its scheduled edge");
            while (!out_valid) tick(0, 0, 0);
            got_i = $signed(out_i);
            got_q = $signed(out_q);
            if (got_i !== expected_i || got_q !== expected_q)
                $fatal(1, "Phase %x: got (%0d,%0d), expected (%0d,%0d)",
                       candidate_phase, got_i, got_q, expected_i, expected_q);
            $fdisplay(trace_file, "%0d %0d", got_i, got_q);
            results = results + 1;
            read_count = $fscanf(vectors, "%x %d %d", candidate_phase, expected_i, expected_q);
        end
        if ((read_count != -1 && (read_count != 0 || !$feof(vectors))) || results == 0)
            $fatal(1, "Invalid vector file");
        repeat (2) tick(0, 0, 0);
        $fclose(vectors);
        $fclose(trace_file);
        $display("PASS CORDIC=%0d samples=%0d latency=%0d ii=%0d", CORDIC, results, OFFSET+1, OFFSET+1);
        $finish;
    end

    initial begin
        #2000000;
        $fatal(1, "NCO simulation timeout");
    end
endmodule
