`timescale 1ns/1ps
// Pilot phase tracker for the Block 8 OFDM RX chain.
//
// Consumes the pilot stream of ofdm_subcarrier_extractor (four pilots per OFDM
// symbol, in bin order) and produces one correction coefficient per symbol for
// ofdm_one_tap_equalizer:
//
//   P     = sum(sign(pilot_ref_re) * pilot)       exact, no multipliers
//   phase = angle(P)                              vectoring CORDIC
//   coeff = 16384 * exp(-j * phase)               rotation CORDIC, Q2.14
//
// This is the fixed-point form of Lab 8.5's
// pilot_phase = angle(vdot(pilot_ref, y[pilots])). The bit-exact reference is
// tools/ofdm_pilot_phase_tracker_fixed.py.
//
// Angles are 16-bit two's complement with pi = 2^15 and wrap naturally.
// pilot_ready is low while a coefficient is being computed (2 * 14 CORDIC
// iterations plus three control cycles); the extractor supports backpressure.
// The coefficient belongs to the symbol whose pilots produced it; applying it
// to that same symbol needs a one-symbol data buffer, applying it to the next
// symbol gives phase tracking with a one-symbol lag.
// If all four pilots cancel (P = 0), the output is the identity coefficient
// and zero_energy is set.

module ofdm_pilot_phase_tracker (
    input  wire                clk,
    input  wire                resetn,

    input  wire                pilot_valid,
    output wire                pilot_ready,
    input  wire signed [15:0]  pilot_re,
    input  wire signed [15:0]  pilot_im,
    input  wire signed [15:0]  pilot_ref_re,

    output reg                 coeff_valid,
    output reg signed [15:0]   coeff_re,
    output reg signed [15:0]   coeff_im,
    output reg signed [15:0]   phase,
    output reg signed [19:0]   correlation_re,
    output reg signed [19:0]   correlation_im,
    output reg                 zero_energy,
    output reg [15:0]          symbol_count
);

    localparam integer ITERATIONS = 14;
    localparam signed [17:0] ROTATION_X0 = 18'sd9949; // round(16384 / K14)

    localparam [2:0] S_ACC  = 3'd0;
    localparam [2:0] S_VEC0 = 3'd1;
    localparam [2:0] S_VEC  = 3'd2;
    localparam [2:0] S_ROT0 = 3'd3;
    localparam [2:0] S_ROT  = 3'd4;
    localparam [2:0] S_OUT  = 3'd5;

    reg [2:0] state;
    reg [1:0] pilot_count;
    reg [3:0] iter;

    reg signed [19:0] acc_re;
    reg signed [19:0] acc_im;

    reg signed [21:0] vx;
    reg signed [21:0] vy;
    reg signed [15:0] vz;

    reg signed [17:0] rx;
    reg signed [17:0] ry;
    reg signed [15:0] rz;

    function automatic signed [15:0] atan_lut;
        input [3:0] index;
        begin
            case (index)
                4'd0:  atan_lut = 16'sd8192;
                4'd1:  atan_lut = 16'sd4836;
                4'd2:  atan_lut = 16'sd2555;
                4'd3:  atan_lut = 16'sd1297;
                4'd4:  atan_lut = 16'sd651;
                4'd5:  atan_lut = 16'sd326;
                4'd6:  atan_lut = 16'sd163;
                4'd7:  atan_lut = 16'sd81;
                4'd8:  atan_lut = 16'sd41;
                4'd9:  atan_lut = 16'sd20;
                4'd10: atan_lut = 16'sd10;
                4'd11: atan_lut = 16'sd5;
                4'd12: atan_lut = 16'sd3;
                4'd13: atan_lut = 16'sd1;
                default: atan_lut = 16'sd0;
            endcase
        end
    endfunction

    wire signed [19:0] pilot_re_ext = {{4{pilot_re[15]}}, pilot_re};
    wire signed [19:0] pilot_im_ext = {{4{pilot_im[15]}}, pilot_im};
    wire signed [19:0] next_acc_re = pilot_ref_re[15] ? acc_re - pilot_re_ext : acc_re + pilot_re_ext;
    wire signed [19:0] next_acc_im = pilot_ref_re[15] ? acc_im - pilot_im_ext : acc_im + pilot_im_ext;

    wire signed [15:0] atan_i = atan_lut(iter);
    wire signed [15:0] rotation_target = -vz;
    wire rotation_needs_pi = (rotation_target > 16'sd16384) || (rotation_target < -16'sd16384);

    assign pilot_ready = resetn && (state == S_ACC);

    always @(posedge clk) begin
        if (!resetn) begin
            state <= S_ACC;
            pilot_count <= 2'd0;
            iter <= 4'd0;
            acc_re <= 20'sd0;
            acc_im <= 20'sd0;
            vx <= 22'sd0;
            vy <= 22'sd0;
            vz <= 16'sd0;
            rx <= 18'sd0;
            ry <= 18'sd0;
            rz <= 16'sd0;
            coeff_valid <= 1'b0;
            coeff_re <= 16'sd16384;
            coeff_im <= 16'sd0;
            phase <= 16'sd0;
            correlation_re <= 20'sd0;
            correlation_im <= 20'sd0;
            zero_energy <= 1'b0;
            symbol_count <= 16'd0;
        end else begin
            coeff_valid <= 1'b0;
            case (state)
                S_ACC: begin
                    if (pilot_valid) begin
                        acc_re <= next_acc_re;
                        acc_im <= next_acc_im;
                        pilot_count <= pilot_count + 2'd1;
                        if (pilot_count == 2'd3)
                            state <= S_VEC0;
                    end
                end

                S_VEC0: begin
                    correlation_re <= acc_re;
                    correlation_im <= acc_im;
                    iter <= 4'd0;
                    if (acc_re == 20'sd0 && acc_im == 20'sd0) begin
                        zero_energy <= 1'b1;
                        vz <= 16'sd0;
                        rx <= 18'sd16384;
                        ry <= 18'sd0;
                        state <= S_OUT;
                    end else begin
                        zero_energy <= 1'b0;
                        if (acc_re < 0) begin
                            vx <= -{{2{acc_re[19]}}, acc_re};
                            vy <= -{{2{acc_im[19]}}, acc_im};
                            vz <= 16'sh8000; // -pi
                        end else begin
                            vx <= {{2{acc_re[19]}}, acc_re};
                            vy <= {{2{acc_im[19]}}, acc_im};
                            vz <= 16'sd0;
                        end
                        state <= S_VEC;
                    end
                end

                S_VEC: begin
                    if (vy >= 0) begin
                        vx <= vx + (vy >>> iter);
                        vy <= vy - (vx >>> iter);
                        vz <= vz + atan_i;
                    end else begin
                        vx <= vx - (vy >>> iter);
                        vy <= vy + (vx >>> iter);
                        vz <= vz - atan_i;
                    end
                    if (iter == ITERATIONS - 1) begin
                        iter <= 4'd0;
                        state <= S_ROT0;
                    end else begin
                        iter <= iter + 4'd1;
                    end
                end

                S_ROT0: begin
                    ry <= 18'sd0;
                    if (rotation_needs_pi) begin
                        rx <= -ROTATION_X0;
                        rz <= rotation_target - 16'sh8000;
                    end else begin
                        rx <= ROTATION_X0;
                        rz <= rotation_target;
                    end
                    state <= S_ROT;
                end

                S_ROT: begin
                    if (rz >= 0) begin
                        rx <= rx - (ry >>> iter);
                        ry <= ry + (rx >>> iter);
                        rz <= rz - atan_i;
                    end else begin
                        rx <= rx + (ry >>> iter);
                        ry <= ry - (rx >>> iter);
                        rz <= rz + atan_i;
                    end
                    if (iter == ITERATIONS - 1) begin
                        iter <= 4'd0;
                        state <= S_OUT;
                    end else begin
                        iter <= iter + 4'd1;
                    end
                end

                S_OUT: begin
                    coeff_valid <= 1'b1;
                    coeff_re <= rx[15:0];
                    coeff_im <= ry[15:0];
                    phase <= vz;
                    symbol_count <= symbol_count + 16'd1;
                    acc_re <= 20'sd0;
                    acc_im <= 20'sd0;
                    pilot_count <= 2'd0;
                    state <= S_ACC;
                end

                default: state <= S_ACC;
            endcase
        end
    end

endmodule
