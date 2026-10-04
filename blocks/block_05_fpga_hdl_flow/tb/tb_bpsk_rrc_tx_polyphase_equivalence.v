// Lab 5.7b - cycle-exact equivalence of bpsk_rrc_tx_polyphase with the pair
// bpsk_upsampler_8x -> bpsk_rrc_tx_fir.
//
// Both get the same symbol stream: random full-scale I and Q values (the
// endpoints -32768 and +32767 included) with random gaps in in_valid. With the
// course RRC taps the output stays inside Q1.15 even then, so the bench counts
// saturated outputs but cannot exercise saturation. Every clock, in_ready, out_valid and (when
// valid) out_i/out_q must be identical.

`timescale 1ns/1ps

module tb_bpsk_rrc_tx_polyphase_equivalence;

localparam integer W = 16;
localparam integer N_SYM = 600;

reg clk = 1'b0;
reg rst = 1'b1;
reg in_valid = 1'b0;
reg signed [W-1:0] in_i = 0;
reg signed [W-1:0] in_q = 0;

wire ref_in_ready;
wire up_valid;
wire signed [W-1:0] up_i;
wire signed [W-1:0] up_q;
wire ref_valid;
wire signed [W-1:0] ref_i;
wire signed [W-1:0] ref_q;

wire pp_in_ready;
wire pp_valid;
wire signed [W-1:0] pp_i;
wire signed [W-1:0] pp_q;

integer sent = 0;
integer outputs = 0;
integer saturated = 0;
integer mismatches = 0;
integer cycles = 0;
integer seed = 32'h2F1D;

bpsk_upsampler_8x #(.W(W)) ref_up (
    .clk(clk), .rst(rst), .in_valid(in_valid), .in_i(in_i), .in_q(in_q),
    .in_ready(ref_in_ready), .out_valid(up_valid), .out_i(up_i), .out_q(up_q)
);

bpsk_rrc_tx_fir #(.W(W)) ref_fir (
    .clk(clk), .rst(rst), .in_valid(up_valid), .in_i(up_i), .in_q(up_q),
    .out_valid(ref_valid), .out_i(ref_i), .out_q(ref_q)
);

bpsk_rrc_tx_polyphase #(.W(W)) dut (
    .clk(clk), .rst(rst), .in_valid(in_valid), .in_i(in_i), .in_q(in_q),
    .in_ready(pp_in_ready), .out_valid(pp_valid), .out_i(pp_i), .out_q(pp_q)
);

always #5 clk = ~clk;

function signed [W-1:0] random_sample;
    input integer r;
    begin
        case (r & 7)
            0: random_sample = 16'sh7fff;
            1: random_sample = 16'sh8000;
            2: random_sample = 16'sd23170;
            3: random_sample = -16'sd23170;
            default: random_sample = $random(seed);
        endcase
    end
endfunction

always @(posedge clk) begin
    if (!rst) begin
        cycles = cycles + 1;
        if (ref_in_ready !== pp_in_ready || ref_valid !== pp_valid ||
            (ref_valid && (ref_i !== pp_i || ref_q !== pp_q))) begin
            if (mismatches < 5)
                $display("FAIL cycle %0d: ready %b/%b valid %b/%b I %0d/%0d Q %0d/%0d (direct/polyphase)",
                         cycles, ref_in_ready, pp_in_ready, ref_valid, pp_valid, ref_i, pp_i, ref_q, pp_q);
            mismatches = mismatches + 1;
        end
        if (ref_valid) begin
            outputs = outputs + 1;
            if (ref_i == 16'sh7fff || ref_i == 16'sh8000 || ref_q == 16'sh7fff || ref_q == 16'sh8000)
                saturated = saturated + 1;
        end
    end
end

initial begin
    repeat (4) @(negedge clk);
    rst = 1'b0;
    while (sent < N_SYM) begin
        @(negedge clk);
        if (($random(seed) & 3) != 0) begin
            in_valid = 1'b1;
            in_i = random_sample($random(seed));
            in_q = random_sample($random(seed));
        end else begin
            in_valid = 1'b0;
        end
        @(posedge clk);
        if (in_valid && ref_in_ready)
            sent = sent + 1;
    end
    @(negedge clk);
    in_valid = 1'b0;
    repeat (40) @(posedge clk);

    if (outputs != 8 * N_SYM) begin
        $display("FAIL: %0d output samples, expected %0d", outputs, 8 * N_SYM);
        mismatches = mismatches + 1;
    end
    if (mismatches != 0) begin
        $display("FAIL: bpsk_rrc_tx_polyphase differs from upsampler + bpsk_rrc_tx_fir in %0d checks", mismatches);
        $fatal(1);
    end
    $display("PASS: bpsk_rrc_tx_polyphase equals bpsk_upsampler_8x + bpsk_rrc_tx_fir clock for clock (%0d symbols, %0d samples, %0d saturated)",
             N_SYM, outputs, saturated);
    $finish;
end

endmodule
