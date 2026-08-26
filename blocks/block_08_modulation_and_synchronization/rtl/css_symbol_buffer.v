`timescale 1ns/1ps

// Reusable complex symbol buffer for the Block 8 CSS accelerator.
//
// The buffer accepts one complete fixed-point symbol through a valid/ready
// handshake, then freezes the captured samples for random/sequential read by a
// downstream DFT/FFT engine. The stored RAM contents are intentionally not
// reset; validity is carried by full/accepted_count.
//
// Contract:
//   * a sample is accepted only when valid_in && ready;
//   * valid gaps do not advance the write index;
//   * symbol_complete is a one-cycle pulse on the DEPTH-th accepted sample;
//   * full remains asserted until release is accepted;
//   * while full, ready is low and no input transfer occurs;
//   * reset discards a partial/full symbol without clearing the RAM array;
//   * read data is combinational and meaningful while full is asserted.
module css_symbol_buffer #(
    parameter integer DEPTH = 128,
    parameter integer ADDR_WIDTH = 7
) (
    input  wire                         clk,
    input  wire                         resetn,

    input  wire                         valid_in,
    output wire                         ready,
    input  wire signed [15:0]           iq_re,
    input  wire signed [15:0]           iq_im,

    input  wire                         release,
    output reg                          symbol_complete,
    output reg                          full,
    output reg  [ADDR_WIDTH:0]          accepted_count,

    input  wire [ADDR_WIDTH-1:0]        read_addr,
    output wire signed [15:0]           read_re,
    output wire signed [15:0]           read_im
);

    reg [ADDR_WIDTH-1:0] write_index;
    reg signed [15:0] mem_re [0:DEPTH-1];
    reg signed [15:0] mem_im [0:DEPTH-1];

    assign ready = resetn && !full;
    assign read_re = mem_re[read_addr];
    assign read_im = mem_im[read_addr];

    always @(posedge clk) begin
        if (!resetn) begin
            write_index      <= {ADDR_WIDTH{1'b0}};
            symbol_complete  <= 1'b0;
            full             <= 1'b0;
            accepted_count   <= {(ADDR_WIDTH+1){1'b0}};
        end else begin
            symbol_complete <= 1'b0;

            if (release && full) begin
                write_index    <= {ADDR_WIDTH{1'b0}};
                full           <= 1'b0;
                accepted_count <= {(ADDR_WIDTH+1){1'b0}};
            end

            if (valid_in && ready) begin
                mem_re[write_index] <= iq_re;
                mem_im[write_index] <= iq_im;

                if (write_index == DEPTH-1) begin
                    write_index      <= {ADDR_WIDTH{1'b0}};
                    accepted_count   <= DEPTH;
                    full             <= 1'b1;
                    symbol_complete  <= 1'b1;
                end else begin
                    write_index      <= write_index + 1'b1;
                    accepted_count   <= accepted_count + 1'b1;
                end
            end
        end
    end

endmodule
