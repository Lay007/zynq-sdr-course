`timescale 1ns/1ps

// Phase-to-IQ stage of an NCO. One turn is 2**32 codes, amplitude is 7/8.
// The same external phase accumulator can feed either implementation.
// Input transfers on valid && ready. The sink takes every valid output.
module nco_phase_architectures #(
    parameter integer CORDIC = 0
) (
    input wire clk, rst, phase_valid,
    output wire phase_ready,
    input wire [31:0] phase,
    output reg out_valid,
    output reg signed [15:0] out_i, out_q
);
    if (CORDIC == 0) begin : table_nco
        reg signed [15:0] quarter [0:256];
        initial $readmemh("nco_quarter_q15.mem", quarter);

        function automatic signed [15:0] sin_code(input [9:0] angle);
            reg [8:0] address;
            begin
                address = angle[8] ? 9'd256 - {1'b0, angle[7:0]} : {1'b0, angle[7:0]};
                sin_code = angle[9] ? -quarter[address] : quarter[address];
            end
        endfunction

        wire [9:0] address_sin = phase[31:22];
        wire [9:0] address_cos = address_sin + 10'd256;
        assign phase_ready = !rst;
        always @(posedge clk) begin
            out_valid <= !rst && phase_valid;
            if (rst) begin
                out_i <= 0;
                out_q <= 0;
            end else if (phase_valid) begin
                out_i <= sin_code(address_cos);
                out_q <= sin_code(address_sin);
            end
        end
    end else begin : cordic_nco
        localparam signed [23:0] INITIAL_X = 24'sd2228628;
        reg busy;
        reg [3:0] step;
        reg signed [23:0] x, y;
        reg signed [31:0] z;

        function automatic signed [31:0] atan_step(input [3:0] index);
            case (index)
                0: atan_step = 32'sd536870912;
                1: atan_step = 32'sd316933406;
                2: atan_step = 32'sd167458907;
                3: atan_step = 32'sd85004756;
                4: atan_step = 32'sd42667331;
                5: atan_step = 32'sd21354465;
                6: atan_step = 32'sd10679838;
                7: atan_step = 32'sd5340245;
                8: atan_step = 32'sd2670163;
                9: atan_step = 32'sd1335087;
                10: atan_step = 32'sd667544;
                11: atan_step = 32'sd333772;
                12: atan_step = 32'sd166886;
                13: atan_step = 32'sd83443;
                14: atan_step = 32'sd41722;
                15: atan_step = 32'sd20861;
                default: atan_step = 0;
            endcase
        endfunction

        function automatic signed [15:0] q15(input signed [23:0] value);
            reg signed [23:0] rounded;
            begin
                rounded = (value + 24'sd64) >>> 7;
                // The 7/8 amplitude bounds the rounded result inside Q1.15.
                q15 = rounded[15:0];
            end
        endfunction

        wire rotate_positive = !z[31];
        wire signed [23:0] shifted_y = y >>> step;
        wire signed [23:0] shifted_x = x >>> step;
        wire signed [23:0] next_x = rotate_positive ? x - shifted_y : x + shifted_y;
        wire signed [23:0] next_y = rotate_positive ? y + shifted_x : y - shifted_x;
        wire signed [31:0] next_z = rotate_positive ? z - atan_step(step) : z + atan_step(step);
        // Quadrants II and III start from the opposite vector so that the
        // remaining angle lies in the CORDIC convergence range.
        wire half_turn = phase[31] != phase[30];
        assign phase_ready = !rst && !busy;

        always @(posedge clk) begin
            if (rst) begin
                busy <= 0;
                step <= 0;
                x <= 0;
                y <= 0;
                z <= 0;
                out_valid <= 0;
                out_i <= 0;
                out_q <= 0;
            end else begin
                out_valid <= 0;
                if (phase_valid && phase_ready) begin
                    busy <= 1;
                    step <= 0;
                    x <= half_turn ? -INITIAL_X : INITIAL_X;
                    y <= 0;
                    z <= {phase[31] ^ half_turn, phase[30:0]};
                end else if (busy) begin
                    x <= next_x;
                    y <= next_y;
                    z <= next_z;
                    step <= step + 1'b1;
                    if (step == 15) begin
                        busy <= 0;
                        out_valid <= 1;
                        out_i <= q15(next_x);
                        out_q <= q15(next_y);
                    end
                end
            end
        end
    end
endmodule
