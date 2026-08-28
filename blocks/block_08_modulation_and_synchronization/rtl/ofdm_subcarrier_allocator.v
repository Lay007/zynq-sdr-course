`timescale 1ns/1ps

// Block 8 OFDM RTL: 64-bin frequency-domain allocator matching Lab 8.5.
//
// Lab 8.5 uses the signed subcarrier set
//   used  = -26..-1, +1..+26
//   pilot = -21, -7, +7, +21
// and 48 QPSK data subcarriers in the remaining used positions.
//
// This block collects those 48 data symbols in the same order as the Python
// model's data_k array (negative frequencies first, then positive), then emits
// one complete 64-bin IFFT frame in natural FFT memory order 0..63:
//   bin 0      : DC = 0
//   bins 1..26 : positive-frequency used carriers
//   bins 27..37: upper guard = 0
//   bins 38..63: negative-frequency used carriers (-26..-1)
//
// Pilot sequence follows Lab 8.5 pilot_ref = [1, 1, 1, -1] at
// k = [-21, -7, +7, +21]. Q1.15 quantization uses the representable endpoints
// +1 -> +32767 and -1 -> -32768; pilot Q is zero.
//
// Contract:
//   * synchronous active-low reset;
//   * accept data only on data_valid && data_ready;
//   * exactly 48 accepted data symbols arm one 64-bin output frame;
//   * no next input frame is accepted while the current frame is emitted;
//   * bin_valid/data/index/last remain stable under output backpressure;
//   * bin_last is asserted only for natural bin index 63;
//   * stored data need not be reset because all 48 entries are overwritten
//     before any output frame can be emitted.
module ofdm_subcarrier_allocator (
    input  wire                clk,
    input  wire                resetn,

    input  wire                data_valid,
    output wire                data_ready,
    input  wire signed [15:0]  data_i,
    input  wire signed [15:0]  data_q,

    output wire                bin_valid,
    input  wire                bin_ready,
    output reg  [5:0]          bin_index,
    output reg  signed [15:0]  bin_i,
    output reg  signed [15:0]  bin_q,
    output wire                bin_last
);

    localparam STATE_COLLECT = 1'b0;
    localparam STATE_EMIT    = 1'b1;

    localparam signed [15:0] PILOT_POS = 16'sd32767;
    localparam signed [15:0] PILOT_NEG = -16'sd32768;

    reg state;
    reg [5:0] data_count;
    reg signed [15:0] data_i_mem [0:47];
    reg signed [15:0] data_q_mem [0:47];

    integer data_index;

    assign data_ready = (state == STATE_COLLECT);
    assign bin_valid = (state == STATE_EMIT);
    assign bin_last = bin_valid && (bin_index == 6'd63);

    // Convert a natural 0..63 FFT bin into the corresponding data_k entry.
    // The caller uses this only for non-pilot used bins.
    function integer data_index_for_bin;
        input [5:0] natural_bin;
        begin
            if ((natural_bin >= 6'd1) && (natural_bin <= 6'd6)) begin
                data_index_for_bin = natural_bin + 23; // +1..+6 -> 24..29
            end else if ((natural_bin >= 6'd8) && (natural_bin <= 6'd20)) begin
                data_index_for_bin = natural_bin + 22; // +8..+20 -> 30..42
            end else if ((natural_bin >= 6'd22) && (natural_bin <= 6'd26)) begin
                data_index_for_bin = natural_bin + 21; // +22..+26 -> 43..47
            end else if ((natural_bin >= 6'd38) && (natural_bin <= 6'd42)) begin
                data_index_for_bin = natural_bin - 38; // -26..-22 -> 0..4
            end else if ((natural_bin >= 6'd44) && (natural_bin <= 6'd56)) begin
                data_index_for_bin = natural_bin - 39; // -20..-8 -> 5..17
            end else begin
                data_index_for_bin = natural_bin - 40; // -6..-1 -> 18..23
            end
        end
    endfunction

    always @* begin
        bin_i = 16'sd0;
        bin_q = 16'sd0;
        data_index = 0;

        case (bin_index)
            6'd43, // k = -21
            6'd57, // k = -7
            6'd7: begin // k = +7
                bin_i = PILOT_POS;
                bin_q = 16'sd0;
            end
            6'd21: begin // k = +21
                bin_i = PILOT_NEG;
                bin_q = 16'sd0;
            end
            6'd0,
            6'd27, 6'd28, 6'd29, 6'd30, 6'd31, 6'd32,
            6'd33, 6'd34, 6'd35, 6'd36, 6'd37: begin
                bin_i = 16'sd0;
                bin_q = 16'sd0;
            end
            default: begin
                data_index = data_index_for_bin(bin_index);
                bin_i = data_i_mem[data_index];
                bin_q = data_q_mem[data_index];
            end
        endcase
    end

    always @(posedge clk) begin
        if (!resetn) begin
            state <= STATE_COLLECT;
            data_count <= 6'd0;
            bin_index <= 6'd0;
        end else begin
            if (state == STATE_COLLECT) begin
                if (data_valid) begin
                    data_i_mem[data_count] <= data_i;
                    data_q_mem[data_count] <= data_q;

                    if (data_count == 6'd47) begin
                        data_count <= 6'd0;
                        bin_index <= 6'd0;
                        state <= STATE_EMIT;
                    end else begin
                        data_count <= data_count + 6'd1;
                    end
                end
            end else if (bin_ready) begin
                if (bin_index == 6'd63) begin
                    bin_index <= 6'd0;
                    state <= STATE_COLLECT;
                end else begin
                    bin_index <= bin_index + 6'd1;
                end
            end
        end
    end

endmodule
