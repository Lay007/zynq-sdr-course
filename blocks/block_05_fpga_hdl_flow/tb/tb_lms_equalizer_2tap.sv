`timescale 1ns/1ps

module tb_lms_equalizer_2tap;
    reg clk = 0;
    always #5 clk = !clk;
    reg rst = 1, in_valid = 0, train = 0;
    reg signed [15:0] sample = 0, desired = 0;
    wire out_valid, weight_clipped;
    wire signed [18:0] y;
    wire signed [15:0] w0, w1;
    lms_equalizer_2tap dut (.*);

    integer vector_file, count, cycle, accepted = 0, clips = 0;
    integer reset_in, valid_in, train_in, x_in, d_in;
    integer want_valid, want_y, want_w0, want_w1, want_clip;

    initial begin
        vector_file = $fopen("lms_vectors.txt", "r");
        if (!vector_file || $fscanf(vector_file, "%d", count) != 1 || count < 1)
            $fatal(1, "Missing LMS vectors");
        for (cycle = 0; cycle < count; cycle = cycle + 1) begin
            if ($fscanf(vector_file, "%d %d %d %d %d %d %d %d %d %d",
                       reset_in, valid_in, train_in, x_in, d_in,
                       want_valid, want_y, want_w0, want_w1, want_clip) != 10)
                $fatal(1, "Invalid LMS vector %0d", cycle);
            @(negedge clk);
            rst = reset_in != 0;
            in_valid = valid_in != 0;
            train = train_in != 0;
            sample = x_in[15:0];
            desired = d_in[15:0];
            @(posedge clk);
            #1;
            if (out_valid !== want_valid[0] || $signed(y) !== want_y ||
                $signed(w0) !== want_w0 || $signed(w1) !== want_w1 ||
                weight_clipped !== want_clip[0])
                $fatal(1, "Cycle %0d: valid/y/w0/w1/clip got %0d/%0d/%0d/%0d/%0d expected %0d/%0d/%0d/%0d/%0d",
                       cycle, out_valid, y, w0, w1, weight_clipped,
                       want_valid, want_y, want_w0, want_w1, want_clip);
            accepted = accepted + out_valid;
            clips = clips + weight_clipped;
        end
        $fclose(vector_file);
        $display("PASS LMS cycles=%0d samples=%0d saturation_flags=%0d", count, accepted, clips);
        $finish;
    end

    initial begin
        #1000000;
        $fatal(1, "LMS simulation timeout");
    end
endmodule
