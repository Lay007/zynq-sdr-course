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
localparam integer PAIR_COUNT = NTAPS / 2;
localparam integer CENTER_TAP = NTAPS / 2;
localparam integer PROD_COUNT = PAIR_COUNT + 1;
localparam integer STAGE1_COUNT = (PROD_COUNT + 1) / 2;
localparam integer STAGE2_COUNT = (STAGE1_COUNT + 1) / 2;
localparam integer STAGE3_COUNT = (STAGE2_COUNT + 1) / 2;
localparam integer STAGE4_COUNT = (STAGE3_COUNT + 1) / 2;
localparam integer STAGE5_COUNT = (STAGE4_COUNT + 1) / 2;
localparam integer STAGE6_COUNT = (STAGE5_COUNT + 1) / 2;

reg signed [CW-1:0] coeff_mem [0:NTAPS-1];
reg signed [W-1:0] xi [0:NTAPS-2];
reg signed [W-1:0] xq [0:NTAPS-2];

reg                  pair_valid;
reg                  stage0_valid;
reg                  stage1_valid;
reg                  stage2_valid;
reg                  stage3_valid;
reg                  stage4_valid;
reg                  stage5_valid;
reg                  stage6_valid;

reg signed [W:0] pair_i [0:PAIR_COUNT-1];
reg signed [W:0] pair_q [0:PAIR_COUNT-1];
reg signed [W-1:0] center_i;
reg signed [W-1:0] center_q;
reg signed [ACC_W-1:0] prod_i [0:PROD_COUNT-1];
reg signed [ACC_W-1:0] prod_q [0:PROD_COUNT-1];
reg signed [ACC_W-1:0] sum1_i [0:STAGE1_COUNT-1];
reg signed [ACC_W-1:0] sum1_q [0:STAGE1_COUNT-1];
reg signed [ACC_W-1:0] sum2_i [0:STAGE2_COUNT-1];
reg signed [ACC_W-1:0] sum2_q [0:STAGE2_COUNT-1];
reg signed [ACC_W-1:0] sum3_i [0:STAGE3_COUNT-1];
reg signed [ACC_W-1:0] sum3_q [0:STAGE3_COUNT-1];
reg signed [ACC_W-1:0] sum4_i [0:STAGE4_COUNT-1];
reg signed [ACC_W-1:0] sum4_q [0:STAGE4_COUNT-1];
reg signed [ACC_W-1:0] sum5_i [0:STAGE5_COUNT-1];
reg signed [ACC_W-1:0] sum5_q [0:STAGE5_COUNT-1];
reg signed [ACC_W-1:0] sum6_i [0:STAGE6_COUNT-1];
reg signed [ACC_W-1:0] sum6_q [0:STAGE6_COUNT-1];

reg signed [ACC_W-1:0] rounded_i;
reg signed [ACC_W-1:0] rounded_q;

integer tap;
integer idx;

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
        coeff_mem[tap] = {CW{1'b0}};
    end
    $readmemh(COEF_FILE, coeff_mem);
end

always @(posedge clk) begin
    if (rst) begin
        out_valid <= 1'b0;
        out_i <= {W{1'b0}};
        out_q <= {W{1'b0}};
        pair_valid <= 1'b0;
        stage0_valid <= 1'b0;
        stage1_valid <= 1'b0;
        stage2_valid <= 1'b0;
        stage3_valid <= 1'b0;
        stage4_valid <= 1'b0;
        stage5_valid <= 1'b0;
        stage6_valid <= 1'b0;
        rounded_i <= {ACC_W{1'b0}};
        rounded_q <= {ACC_W{1'b0}};

        for (tap = 0; tap < NTAPS - 1; tap = tap + 1) begin
            xi[tap] <= {W{1'b0}};
            xq[tap] <= {W{1'b0}};
        end
        center_i <= {W{1'b0}};
        center_q <= {W{1'b0}};
        for (tap = 0; tap < PAIR_COUNT; tap = tap + 1) begin
            pair_i[tap] <= {(W+1){1'b0}};
            pair_q[tap] <= {(W+1){1'b0}};
        end
        for (tap = 0; tap < PROD_COUNT; tap = tap + 1) begin
            prod_i[tap] <= {ACC_W{1'b0}};
            prod_q[tap] <= {ACC_W{1'b0}};
        end
        for (tap = 0; tap < STAGE1_COUNT; tap = tap + 1) begin
            sum1_i[tap] <= {ACC_W{1'b0}};
            sum1_q[tap] <= {ACC_W{1'b0}};
        end
        for (tap = 0; tap < STAGE2_COUNT; tap = tap + 1) begin
            sum2_i[tap] <= {ACC_W{1'b0}};
            sum2_q[tap] <= {ACC_W{1'b0}};
        end
        for (tap = 0; tap < STAGE3_COUNT; tap = tap + 1) begin
            sum3_i[tap] <= {ACC_W{1'b0}};
            sum3_q[tap] <= {ACC_W{1'b0}};
        end
        for (tap = 0; tap < STAGE4_COUNT; tap = tap + 1) begin
            sum4_i[tap] <= {ACC_W{1'b0}};
            sum4_q[tap] <= {ACC_W{1'b0}};
        end
        for (tap = 0; tap < STAGE5_COUNT; tap = tap + 1) begin
            sum5_i[tap] <= {ACC_W{1'b0}};
            sum5_q[tap] <= {ACC_W{1'b0}};
        end
        for (tap = 0; tap < STAGE6_COUNT; tap = tap + 1) begin
            sum6_i[tap] <= {ACC_W{1'b0}};
            sum6_q[tap] <= {ACC_W{1'b0}};
        end
    end else begin
        pair_valid <= in_valid;
        stage0_valid <= pair_valid;
        stage1_valid <= stage0_valid;
        stage2_valid <= stage1_valid;
        stage3_valid <= stage2_valid;
        stage4_valid <= stage3_valid;
        stage5_valid <= stage4_valid;
        stage6_valid <= stage5_valid;
        out_valid <= stage6_valid;

        if (stage0_valid) begin
            for (idx = 0; idx < STAGE1_COUNT; idx = idx + 1) begin
                sum1_i[idx] <= prod_i[idx*2] +
                    (((idx*2)+1 < PROD_COUNT) ? prod_i[(idx*2)+1] : {ACC_W{1'b0}});
                sum1_q[idx] <= prod_q[idx*2] +
                    (((idx*2)+1 < PROD_COUNT) ? prod_q[(idx*2)+1] : {ACC_W{1'b0}});
            end
        end

        if (stage1_valid) begin
            for (idx = 0; idx < STAGE2_COUNT; idx = idx + 1) begin
                sum2_i[idx] <= sum1_i[idx*2] +
                    (((idx*2)+1 < STAGE1_COUNT) ? sum1_i[(idx*2)+1] : {ACC_W{1'b0}});
                sum2_q[idx] <= sum1_q[idx*2] +
                    (((idx*2)+1 < STAGE1_COUNT) ? sum1_q[(idx*2)+1] : {ACC_W{1'b0}});
            end
        end

        if (stage2_valid) begin
            for (idx = 0; idx < STAGE3_COUNT; idx = idx + 1) begin
                sum3_i[idx] <= sum2_i[idx*2] +
                    (((idx*2)+1 < STAGE2_COUNT) ? sum2_i[(idx*2)+1] : {ACC_W{1'b0}});
                sum3_q[idx] <= sum2_q[idx*2] +
                    (((idx*2)+1 < STAGE2_COUNT) ? sum2_q[(idx*2)+1] : {ACC_W{1'b0}});
            end
        end

        if (stage3_valid) begin
            for (idx = 0; idx < STAGE4_COUNT; idx = idx + 1) begin
                sum4_i[idx] <= sum3_i[idx*2] +
                    (((idx*2)+1 < STAGE3_COUNT) ? sum3_i[(idx*2)+1] : {ACC_W{1'b0}});
                sum4_q[idx] <= sum3_q[idx*2] +
                    (((idx*2)+1 < STAGE3_COUNT) ? sum3_q[(idx*2)+1] : {ACC_W{1'b0}});
            end
        end

        if (stage4_valid) begin
            for (idx = 0; idx < STAGE5_COUNT; idx = idx + 1) begin
                sum5_i[idx] <= sum4_i[idx*2] +
                    (((idx*2)+1 < STAGE4_COUNT) ? sum4_i[(idx*2)+1] : {ACC_W{1'b0}});
                sum5_q[idx] <= sum4_q[idx*2] +
                    (((idx*2)+1 < STAGE4_COUNT) ? sum4_q[(idx*2)+1] : {ACC_W{1'b0}});
            end
        end

        if (stage5_valid) begin
            for (idx = 0; idx < STAGE6_COUNT; idx = idx + 1) begin
                sum6_i[idx] <= sum5_i[idx*2] +
                    (((idx*2)+1 < STAGE5_COUNT) ? sum5_i[(idx*2)+1] : {ACC_W{1'b0}});
                sum6_q[idx] <= sum5_q[idx*2] +
                    (((idx*2)+1 < STAGE5_COUNT) ? sum5_q[(idx*2)+1] : {ACC_W{1'b0}});
            end
        end

        if (stage6_valid) begin
            rounded_i = round_q15(sum6_i[0]);
            rounded_q = round_q15(sum6_q[0]);

            out_i <= sat_q15(rounded_i);
            out_q <= sat_q15(rounded_q);
        end

        if (pair_valid) begin
            // Keep the symmetric pre-add separate from the multiplier input.
            // Vivado otherwise absorbs both into one xi -> DSP-input path that
            // is marginal on the 125 MHz divide-select clock.
            prod_i[PAIR_COUNT] <= $signed(center_i) * $signed(coeff_mem[CENTER_TAP]);
            prod_q[PAIR_COUNT] <= $signed(center_q) * $signed(coeff_mem[CENTER_TAP]);
            for (tap = 0; tap < PAIR_COUNT; tap = tap + 1) begin
                prod_i[tap] <= $signed(pair_i[tap]) * $signed(coeff_mem[tap]);
                prod_q[tap] <= $signed(pair_q[tap]) * $signed(coeff_mem[tap]);
            end
        end

        if (in_valid) begin
            // The symmetric taps still save multipliers, but the sum reduction
            // now runs through a registered tree so the filter sustains the
            // divided AD9361 clock used by the hardware integration.
            center_i <= xi[CENTER_TAP-1];
            center_q <= xq[CENTER_TAP-1];

            for (tap = 0; tap < PAIR_COUNT; tap = tap + 1) begin
                if (tap == 0) begin
                    pair_i[tap] <= $signed({in_i[W-1], in_i}) +
                        $signed({xi[NTAPS-2][W-1], xi[NTAPS-2]});
                    pair_q[tap] <= $signed({in_q[W-1], in_q}) +
                        $signed({xq[NTAPS-2][W-1], xq[NTAPS-2]});
                end else begin
                    pair_i[tap] <= $signed({xi[tap-1][W-1], xi[tap-1]}) +
                        $signed({xi[NTAPS-tap-2][W-1], xi[NTAPS-tap-2]});
                    pair_q[tap] <= $signed({xq[tap-1][W-1], xq[tap-1]}) +
                        $signed({xq[NTAPS-tap-2][W-1], xq[NTAPS-tap-2]});
                end
            end

            for (tap = NTAPS - 2; tap > 0; tap = tap - 1) begin
                xi[tap] <= xi[tap-1];
                xq[tap] <= xq[tap-1];
            end
            xi[0] <= in_i;
            xq[0] <= in_q;
        end
    end
end

endmodule
