`timescale 1ns/1ps

// Reusable asynchronous Q1.15 coefficient ROM for generated detector tables.
// The generator runs before simulation and synthesis. Initial zeroing avoids
// simulator-dependent X values during the time-zero readmemh delta cycle.
module css_q15_rom #(
    parameter integer DEPTH = 128,
    parameter integer ADDR_W = 7,
    parameter FILE = ""
) (
    input  wire [ADDR_W-1:0] addr,
    output wire signed [15:0] dout
);

    reg signed [15:0] mem [0:DEPTH-1];
    integer i;

    initial begin
        for (i = 0; i < DEPTH; i = i + 1)
            mem[i] = 16'sd0;
        $readmemh(FILE, mem);
    end

    assign dout = mem[addr];

endmodule
