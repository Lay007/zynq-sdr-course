`timescale 1ns/1ps

// Reusable peak and second-peak detector for a sequential CSS bin stream.
//
// Contract:
//   * start clears the previous frame result and enters busy;
//   * bins are consumed only when busy && bin_valid;
//   * the first valid bin initializes the peak;
//   * strict comparisons preserve first-occurrence tie breaking;
//   * LAST_BIN completes the frame and produces a one-cycle done pulse;
//   * start while busy is ignored and produces a one-cycle start_rejected pulse;
//   * reset aborts an active frame and clears all result/control registers.
//
// Magnitudes are signed to preserve the existing detector interface. The CSS
// DFT contract guarantees non-negative values below the signed width limit.
module css_peak_detector #(
    parameter integer BIN_INDEX_WIDTH = 7,
    parameter integer MAG_WIDTH = 64,
    parameter [BIN_INDEX_WIDTH-1:0] LAST_BIN =
        {BIN_INDEX_WIDTH{1'b1}}
) (
    input  wire                                  clk,
    input  wire                                  resetn,

    input  wire                                  start,
    output reg                                   busy,
    output reg                                   done,
    output reg                                   start_rejected,

    input  wire                                  bin_valid,
    input  wire [BIN_INDEX_WIDTH-1:0]            bin_index,
    input  wire signed [MAG_WIDTH-1:0]           magnitude_squared,

    output reg  [BIN_INDEX_WIDTH-1:0]            peak_bin,
    output reg  [BIN_INDEX_WIDTH-1:0]            second_bin,
    output reg  signed [MAG_WIDTH-1:0]           peak_magnitude_squared,
    output reg  signed [MAG_WIDTH-1:0]           second_magnitude_squared
);

    reg have_peak;

    always @(posedge clk) begin
        if (!resetn) begin
            busy                         <= 1'b0;
            done                         <= 1'b0;
            start_rejected               <= 1'b0;
            have_peak                     <= 1'b0;
            peak_bin                      <= {BIN_INDEX_WIDTH{1'b0}};
            second_bin                    <= {BIN_INDEX_WIDTH{1'b0}};
            peak_magnitude_squared        <= {MAG_WIDTH{1'b0}};
            second_magnitude_squared      <= {MAG_WIDTH{1'b0}};
        end else begin
            done           <= 1'b0;
            start_rejected <= 1'b0;

            if (start && busy)
                start_rejected <= 1'b1;

            if (start && !busy) begin
                busy                         <= 1'b1;
                have_peak                     <= 1'b0;
                peak_bin                      <= {BIN_INDEX_WIDTH{1'b0}};
                second_bin                    <= {BIN_INDEX_WIDTH{1'b0}};
                peak_magnitude_squared        <= {MAG_WIDTH{1'b0}};
                second_magnitude_squared      <= {MAG_WIDTH{1'b0}};
            end else if (busy && bin_valid) begin
                if (!have_peak) begin
                    have_peak                <= 1'b1;
                    peak_bin                 <= bin_index;
                    peak_magnitude_squared   <= magnitude_squared;
                end else if (magnitude_squared > peak_magnitude_squared) begin
                    second_bin                 <= peak_bin;
                    second_magnitude_squared   <= peak_magnitude_squared;
                    peak_bin                   <= bin_index;
                    peak_magnitude_squared     <= magnitude_squared;
                end else if (magnitude_squared > second_magnitude_squared) begin
                    second_bin                 <= bin_index;
                    second_magnitude_squared   <= magnitude_squared;
                end

                if (bin_index == LAST_BIN) begin
                    busy <= 1'b0;
                    done <= 1'b1;
                end
            end
        end
    end

endmodule
