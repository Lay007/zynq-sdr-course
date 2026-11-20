`timescale 1ns/1ps

module tb_fir_iq_architectures;
    parameter integer ARCH = 0;
    localparam integer OUTPUT_OFFSET = ARCH == 1 ? 4 : ARCH == 2 ? 2 : 0;
    localparam integer II = ARCH == 1 ? 5 : 1;
    reg clk = 0;
    always #5 clk = !clk;

    reg rst = 1, in_valid = 0;
    reg signed [15:0] in_i = 0, in_q = 0, h0 = 0, h1 = 0, h2 = 0, h3 = 0;
    wire in_ready, out_valid;
    wire signed [15:0] out_i, out_q;
    fir_iq_architectures #(.ARCH(ARCH)) dut (.*);

    integer cycle = 0, next_accept = 0;
    integer head = 0, tail = 0;
    integer expected_at [0:511], expected_i [0:511], expected_q [0:511];
    integer checked = 0, stalls = 0, intervals_at_ii = 0, last_accept = -100;
    reg accepted;

    task automatic tick(
        input bit reset, input bit valid,
        input integer i_value, q_value, want_i, want_q
    );
        bit want_valid;
        begin
            @(negedge clk);
            rst = reset;
            in_valid = valid;
            in_i = i_value;
            in_q = q_value;
            @(posedge clk);
            cycle = cycle + 1;
            if (in_ready !== (!reset && cycle >= next_accept))
                $fatal(1, "ARCH=%0d incorrect ready at cycle %0d", ARCH, cycle);
            accepted = valid && in_ready;
            if (reset) begin
                head = 0;
                tail = 0;
                next_accept = cycle + 1;
                last_accept = -100;
            end else if (accepted) begin
                if (cycle - last_accept == II)
                    intervals_at_ii = intervals_at_ii + 1;
                last_accept = cycle;
                next_accept = cycle + II;
                expected_at[tail] = cycle + OUTPUT_OFFSET;
                expected_i[tail] = want_i;
                expected_q[tail] = want_q;
                tail = tail + 1;
            end else if (valid) begin
                stalls = stalls + 1;
            end
            // Observe the registered result after nonblocking assignments.
            #1;
            want_valid = head < tail && cycle == expected_at[head];
            if (out_valid !== want_valid)
                $fatal(1, "ARCH=%0d incorrect valid at cycle %0d", ARCH, cycle);
            if (want_valid) begin
                if ($signed(out_i) !== expected_i[head] || $signed(out_q) !== expected_q[head])
                    $fatal(1, "ARCH=%0d sample %0d got (%0d,%0d), expected (%0d,%0d)",
                           ARCH, checked, out_i, out_q, expected_i[head], expected_q[head]);
                head = head + 1;
                checked = checked + 1;
            end
        end
    endtask

    integer file_handle, groups, count, gap, total = 0;
    integer a, b, c, d, i_value, q_value, want_i, want_q;
    initial begin
        file_handle = $fopen("fir_vectors.txt", "r");
        if (file_handle == 0 || $fscanf(file_handle, "%d", groups) != 1 || groups < 1)
            $fatal(1, "Missing FIR vectors");

        // Reset one clock after acceptance. Folded and pipelined DUTs must
        // discard the in-flight result and remain quiet through their latency.
        tick(1, 0, 0, 0, 0, 0);
        h0 = 16384;
        tick(0, 1, 400, -600, 200, -300);
        tick(1, 0, 0, 0, 0, 0);
        repeat (6) tick(0, 0, 0, 0, 0, 0);
        checked = 0;

        repeat (groups) begin
            if ($fscanf(file_handle, "%d %d %d %d %d", a, b, c, d, count) != 5
                || count < 1 || count > 512)
                $fatal(1, "Malformed FIR vector header");
            tick(1, 0, 0, 0, 0, 0);
            h0 = a; h1 = b; h2 = c; h3 = d;
            total = total + count;
            repeat (count) begin
                if ($fscanf(file_handle, "%d %d %d %d %d",
                            gap, i_value, q_value, want_i, want_q) != 5)
                    $fatal(1, "Missing FIR vector");
                repeat (gap) tick(0, 0, 0, 0, 0, 0);
                tick(0, 1, i_value, q_value, want_i, want_q);
                while (!accepted) tick(0, 1, i_value, q_value, want_i, want_q);
            end
            repeat (6) tick(0, 0, 0, 0, 0, 0);
        end
        $fclose(file_handle);
        if (checked != total || head != tail || intervals_at_ii == 0 ||
            (ARCH == 1 && stalls == 0) || (ARCH != 1 && stalls != 0))
            $fatal(1, "ARCH=%0d incomplete result or handshake coverage", ARCH);
        // Latency counts edges from input transfer to output consumption by
        // a downstream register, rather than to the output becoming valid.
        $display("PASS ARCH=%0d compared=%0d latency=%0d ii=%0d stalled_input_cycles=%0d",
                 ARCH, checked, OUTPUT_OFFSET + 1, II, stalls);
        $finish;
    end

    initial begin
        #1000000;
        $fatal(1, "ARCH=%0d timeout", ARCH);
    end
endmodule
