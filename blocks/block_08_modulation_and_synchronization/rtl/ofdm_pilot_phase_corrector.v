`timescale 1ns/1ps
// Pilot-driven common-phase correction for the Block 8 OFDM RX chain.
//
// Sits between ofdm_subcarrier_extractor and the QPSK demapper:
//
//   extractor data  -> 48-entry symbol buffer --\
//                                                +-> ofdm_one_tap_equalizer -> out
//   extractor pilots -> ofdm_pilot_phase_tracker /   (coefficient of this symbol)
//
// This is Lab 8.5's per-symbol correction in RTL: the coefficient that the
// four pilots of a symbol produce is applied to the data of the *same* symbol.
// The pilots arrive interleaved with the data (bins 7, 21, 43, 57), so the
// data is buffered until both the whole symbol and its coefficient are
// available. Behaviour per symbol:
//   FILL : data samples are written into the buffer and pilots feed the
//          tracker, until the data sample marked data_last has arrived and the
//          tracker has produced a coefficient;
//   DRAIN: the buffered samples leave through the equalizer, in the order they
//          arrived, with that coefficient; data_ready and pilot_ready are low,
//          so the extractor holds the next symbol (it supports backpressure).
// Latency is therefore one OFDM symbol plus the tracker's 31 clocks. The
// arithmetic of the tracker and the equalizer is unchanged.
module ofdm_pilot_phase_corrector (
    input  wire                clk,
    input  wire                resetn,

    input  wire                data_valid,
    output wire                data_ready,
    input  wire signed [15:0]  data_re,
    input  wire signed [15:0]  data_im,
    input  wire [5:0]          data_index,
    input  wire                data_last,

    input  wire                pilot_valid,
    output wire                pilot_ready,
    input  wire signed [15:0]  pilot_re,
    input  wire signed [15:0]  pilot_im,
    input  wire signed [15:0]  pilot_ref_re,

    output wire                out_valid,
    input  wire                out_ready,
    output wire signed [15:0]  out_re,
    output wire signed [15:0]  out_im,
    output wire [5:0]          out_index,
    output wire                out_last,

    output reg signed [15:0]   applied_coeff_re,
    output reg signed [15:0]   applied_coeff_im,
    output wire signed [15:0]  last_phase,
    output wire                last_zero_energy,
    output wire [15:0]         symbol_count,
    output wire [31:0]         saturation_count
);

    localparam STATE_FILL  = 1'b0;
    localparam STATE_DRAIN = 1'b1;

    reg state;
    reg data_done;
    reg have_coeff;
    reg [5:0] write_count;
    reg [5:0] read_count;

    reg signed [15:0] buffer_re [0:47];
    reg signed [15:0] buffer_im [0:47];
    reg [5:0]         buffer_index [0:47];

    wire tracker_pilot_ready;
    wire tracker_coeff_valid;
    wire signed [15:0] tracker_coeff_re;
    wire signed [15:0] tracker_coeff_im;

    assign data_ready = resetn && (state == STATE_FILL) && !data_done;
    assign pilot_ready = (state == STATE_FILL) && tracker_pilot_ready;

    ofdm_pilot_phase_tracker tracker (
        .clk(clk),
        .resetn(resetn),
        .pilot_valid(pilot_valid && (state == STATE_FILL)),
        .pilot_ready(tracker_pilot_ready),
        .pilot_re(pilot_re),
        .pilot_im(pilot_im),
        .pilot_ref_re(pilot_ref_re),
        .coeff_valid(tracker_coeff_valid),
        .coeff_re(tracker_coeff_re),
        .coeff_im(tracker_coeff_im),
        .phase(last_phase),
        .correlation_re(),
        .correlation_im(),
        .zero_energy(last_zero_energy),
        .symbol_count(symbol_count)
    );

    wire eq_in_valid = (state == STATE_DRAIN);
    wire eq_in_ready;
    wire eq_in_last = (read_count == write_count - 6'd1);

    ofdm_one_tap_equalizer equalizer (
        .clk(clk),
        .resetn(resetn),
        .in_valid(eq_in_valid),
        .in_ready(eq_in_ready),
        .in_re(buffer_re[read_count]),
        .in_im(buffer_im[read_count]),
        .coeff_re(applied_coeff_re),
        .coeff_im(applied_coeff_im),
        .in_index(buffer_index[read_count]),
        .in_last(eq_in_last),
        .out_valid(out_valid),
        .out_ready(out_ready),
        .out_re(out_re),
        .out_im(out_im),
        .out_index(out_index),
        .out_last(out_last),
        .saturation_count(saturation_count)
    );

    always @(posedge clk) begin
        if (!resetn) begin
            state <= STATE_FILL;
            data_done <= 1'b0;
            have_coeff <= 1'b0;
            write_count <= 6'd0;
            read_count <= 6'd0;
            applied_coeff_re <= 16'sd16384;
            applied_coeff_im <= 16'sd0;
        end else begin
            case (state)
                STATE_FILL: begin
                    if (data_valid && data_ready) begin
                        buffer_re[write_count] <= data_re;
                        buffer_im[write_count] <= data_im;
                        buffer_index[write_count] <= data_index;
                        write_count <= write_count + 6'd1;
                        if (data_last)
                            data_done <= 1'b1;
                    end
                    if (tracker_coeff_valid) begin
                        applied_coeff_re <= tracker_coeff_re;
                        applied_coeff_im <= tracker_coeff_im;
                        have_coeff <= 1'b1;
                    end
                    if (data_done && have_coeff) begin
                        read_count <= 6'd0;
                        state <= STATE_DRAIN;
                    end
                end

                default: begin // STATE_DRAIN
                    if (eq_in_valid && eq_in_ready) begin
                        if (eq_in_last) begin
                            state <= STATE_FILL;
                            data_done <= 1'b0;
                            have_coeff <= 1'b0;
                            write_count <= 6'd0;
                            read_count <= 6'd0;
                        end else begin
                            read_count <= read_count + 6'd1;
                        end
                    end
                end
            endcase
        end
    end

endmodule
