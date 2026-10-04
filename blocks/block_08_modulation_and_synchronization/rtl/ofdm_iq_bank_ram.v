`timescale 1ns/1ps
// One bank of the OFDM IFFT/FFT working memory in block RAM (BRAM_MEMORY = 1):
// 32 complex Q1.15 words, one synchronous write port and one synchronous read
// port (simple dual-port RAM). rdata shows the word at raddr one clock later.
// A read and a write in the same clock always use different addresses in the
// transform schedule, so the read-during-write behaviour does not matter.
module ofdm_iq_bank_ram (
    input  wire        clk,
    input  wire        we,
    input  wire [4:0]  waddr,
    input  wire [31:0] wdata,
    input  wire [4:0]  raddr,
    output reg  [31:0] rdata
);

    (* ram_style = "block" *) reg [31:0] mem [0:31];

    integer k;
    initial
        for (k = 0; k < 32; k = k + 1)
            mem[k] = 32'd0;

    always @(posedge clk) begin
        if (we)
            mem[waddr] <= wdata;
        rdata <= mem[raddr];
    end

endmodule
