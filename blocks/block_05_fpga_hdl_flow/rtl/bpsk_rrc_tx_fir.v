// Lab 5.6 - BPSK RRC TX FIR
//
// Pulse-shaping RTL stage for the executable BPSK route:
// Block 11 handoff symbols -> Q1.15 RRC FIR -> future TX gain / DAC path.
//
// The coefficient memory file is generated from the shared Block 11 package by:
//   python blocks/block_05_fpga_hdl_flow/python/generate_bpsk_rrc_tx_fir_vectors.py

`timescale 1ns/1ps

module bpsk_rrc_tx_fir #(
    parameter integer W = 16,
    parameter integer CW = 16,
    parameter integer NTAPS = 65,
    parameter integer ACC_W = 40,
    parameter integer SHIFT = 15,
    parameter COEF_FILE = "blocks/block_05_fpga_hdl_flow/rtl/bpsk_rrc_tx_fir_taps.mem"
) (
    input  wire                 clk,
    input  wire                 rst,
    input  wire                 in_valid,
    input  wire signed [W-1:0]  in_i,
    input  wire signed [W-1:0]  in_q,
    output reg                  out_valid,
    output reg signed [W-1:0]   out_i,
    output reg signed [W-1:0]   out_q
);

localparam signed [ACC_W-1:0] ROUND_BIAS = {{(ACC_W-1){1'b0}}, 1'b1} <<< (SHIFT - 1);

reg signed [CW-1:0] coeff_mem [0:NTAPS-1];
reg signed [W-1:0] xi [0:NTAPS-1];
reg signed [W-1:0] xq [0:NTAPS-1];

reg signed [ACC_W-1:0] acc_i;
reg signed [ACC_W-1:0] acc_q;
reg signed [ACC_W-1:0] rounded_i;
reg signed [ACC_W-1:0] rounded_q;

integer tap;

function signed [ACC_W-1:0] round_q15;
    input signed [ACC_W-1:0] value;
    begin
        round_q15 = (value + ROUND_BIAS) >>> SHIFT;
    end
endfunction

function signed [W-1:0] sat_q15;
    input signed [ACC_W-1:0] value;
    begin
        if (value > 32767)
            sat_q15 = 16'sd32767;
        else if (value < -32768)
            sat_q15 = -16'sd32768;
        else
            sat_q15 = value[W-1:0];
    end
endfunction

initial begin
    for (tap = 0; tap < NTAPS; tap = tap + 1) begin
        coeff_mem[tap] = '0;
    end
    $readmemh(COEF_FILE, coeff_mem);
end

always @(posedge clk) begin
    if (rst) begin
        out_valid <= 1'b0;
        out_i <= '0;
        out_q <= '0;
        acc_i <= '0;
        acc_q <= '0;
        rounded_i <= '0;
        rounded_q <= '0;

        for (tap = 0; tap < NTAPS; tap = tap + 1) begin
            xi[tap] <= '0;
            xq[tap] <= '0;
        end
    end else begin
        out_valid <= in_valid;

        if (in_valid) begin
            acc_i = $signed(in_i) * $signed(coeff_mem[0]);
            acc_q = $signed(in_q) * $signed(coeff_mem[0]);

            for (tap = 1; tap < NTAPS; tap = tap + 1) begin
                acc_i = acc_i + $signed(xi[tap-1]) * $signed(coeff_mem[tap]);
                acc_q = acc_q + $signed(xq[tap-1]) * $signed(coeff_mem[tap]);
            end

            rounded_i = round_q15(acc_i);
            rounded_q = round_q15(acc_q);

            out_i <= sat_q15(rounded_i);
            out_q <= sat_q15(rounded_q);

            for (tap = NTAPS - 1; tap > 0; tap = tap - 1) begin
                xi[tap] <= xi[tap-1];
                xq[tap] <= xq[tap-1];
            end
            xi[0] <= in_i;
            xq[0] <= in_q;
        end
    end
end

endmodule
