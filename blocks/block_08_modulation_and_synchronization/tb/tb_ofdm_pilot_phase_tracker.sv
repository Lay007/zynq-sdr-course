`timescale 1ns/1ps
// Self-checking testbench for ofdm_pilot_phase_tracker.
//
// Vectors come from tools/ofdm_pilot_phase_tracker_fixed.py via
// tools/generate_ofdm_pilot_tracker_vectors.py. Every OFDM symbol's four
// pilots are offered back to back with pilot_valid held high, including while
// the tracker is busy, so the pilot_ready backpressure is exercised. The
// coefficient, phase and zero-energy flag must match the model bit for bit.

module tb_ofdm_pilot_phase_tracker;
    localparam string VECTORS = "verification/vectors/block08_ofdm_pilot_tracker_vectors.txt";

    reg clk = 1'b0;
    reg resetn = 1'b0;
    always #5 clk = ~clk;

    reg pilot_valid = 1'b0;
    reg signed [15:0] pilot_re = 16'sd0;
    reg signed [15:0] pilot_im = 16'sd0;
    reg signed [15:0] pilot_ref_re = 16'sd0;
    wire pilot_ready;

    wire coeff_valid;
    wire signed [15:0] coeff_re;
    wire signed [15:0] coeff_im;
    wire signed [15:0] phase;
    wire signed [19:0] correlation_re;
    wire signed [19:0] correlation_im;
    wire zero_energy;
    wire [15:0] symbol_count;

    ofdm_pilot_phase_tracker dut (
        .clk(clk),
        .resetn(resetn),
        .pilot_valid(pilot_valid),
        .pilot_ready(pilot_ready),
        .pilot_re(pilot_re),
        .pilot_im(pilot_im),
        .pilot_ref_re(pilot_ref_re),
        .coeff_valid(coeff_valid),
        .coeff_re(coeff_re),
        .coeff_im(coeff_im),
        .phase(phase),
        .correlation_re(correlation_re),
        .correlation_im(correlation_im),
        .zero_energy(zero_energy),
        .symbol_count(symbol_count)
    );

    integer fd;
    integer scanned;
    integer symbols = 0;
    integer errors = 0;
    integer busy_cycles_seen = 0;
    integer k;
    integer p_re [0:3];
    integer p_im [0:3];
    integer p_ref [0:3];
    integer exp_re;
    integer exp_im;
    integer exp_phase;
    integer exp_zero;

    // Count cycles in which a pilot is offered but not accepted.
    always @(posedge clk) begin
        if (resetn && pilot_valid && !pilot_ready)
            busy_cycles_seen <= busy_cycles_seen + 1;
    end

    // Drive on the falling edge; a beat is accepted at the next rising edge
    // only if pilot_ready is already high before that edge.
    task automatic send_pilot(input integer re, input integer im, input integer ref_value);
        begin
            @(negedge clk);
            pilot_re = re[15:0];
            pilot_im = im[15:0];
            pilot_ref_re = ref_value[15:0];
            pilot_valid = 1'b1;
            while (!pilot_ready) @(negedge clk);
            @(posedge clk);
        end
    endtask

    initial begin
        fd = $fopen(VECTORS, "r");
        if (fd == 0) begin
            $display("FAIL: cannot open %s", VECTORS);
            $fatal(1);
        end

        repeat (4) @(posedge clk);
        resetn <= 1'b1;
        @(posedge clk);

        while (!$feof(fd)) begin
            scanned = $fscanf(fd, "%d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d\n",
                              p_re[0], p_im[0], p_ref[0], p_re[1], p_im[1], p_ref[1],
                              p_re[2], p_im[2], p_ref[2], p_re[3], p_im[3], p_ref[3],
                              exp_re, exp_im, exp_phase, exp_zero);
            if (scanned != 16) begin
                if (scanned > 0) begin
                    $display("FAIL: malformed vector line after %0d symbols", symbols);
                    errors = errors + 1;
                end
            end else begin
                for (k = 0; k < 4; k = k + 1)
                    send_pilot(p_re[k], p_im[k], p_ref[k]);
                // Hold the next symbol's first pilot valid while the tracker is
                // busy: nothing may be accepted until the coefficient is out.
                @(negedge clk);
                pilot_re = 16'sh7abc;
                pilot_im = 16'sh1234;
                pilot_ref_re = 16'sd32767;
                pilot_valid = 1'b1;
                while (!coeff_valid) @(negedge clk);
                pilot_valid = 1'b0;
                if (coeff_re !== exp_re[15:0] || coeff_im !== exp_im[15:0] ||
                    phase !== exp_phase[15:0] || zero_energy !== exp_zero[0]) begin
                    $display("ERROR symbol %0d: coeff=(%0d,%0d) phase=%0d zero=%0b expected=(%0d,%0d) phase=%0d zero=%0d",
                             symbols, coeff_re, coeff_im, phase, zero_energy,
                             exp_re, exp_im, exp_phase, exp_zero);
                    errors = errors + 1;
                end
                symbols = symbols + 1;
            end
        end
        $fclose(fd);

        if (symbol_count != symbols[15:0]) begin
            $display("ERROR: symbol_count=%0d, expected %0d", symbol_count, symbols);
            errors = errors + 1;
        end
        if (busy_cycles_seen == 0) begin
            $display("ERROR: pilot_ready backpressure was never exercised");
            errors = errors + 1;
        end
        if (symbols == 0) begin
            $display("ERROR: no vectors were read");
            errors = errors + 1;
        end

        if (errors == 0) begin
            $display("PASS: ofdm_pilot_phase_tracker matched the fixed-point model on %0d symbols (backpressure cycles %0d)",
                     symbols, busy_cycles_seen);
            $finish;
        end else begin
            $display("FAIL: ofdm_pilot_phase_tracker completed with %0d errors", errors);
            $fatal(1);
        end
    end

    initial begin
        #10000000;
        $display("FAIL: timeout");
        $fatal(1);
    end
endmodule
