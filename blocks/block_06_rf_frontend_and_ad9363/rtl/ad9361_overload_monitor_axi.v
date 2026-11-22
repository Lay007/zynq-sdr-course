// Minimal, independent 32-bit AXI4-Lite register interface for the event monitor.
// AW and W channels are accepted independently. One outstanding write/read.
// CSR map: 00 sticky, 04 clock ticks, 08 clear (write 1), 0C sampled pins,
// 20..3C eight rising-edge counts, 40..5C eight last-event clock ticks.
module ad9361_overload_monitor_axi (
    input wire clk,
    input wire rst_n,
    input wire [7:0] ctrl_out_async,
    input wire [7:0] s_axi_awaddr,
    input wire [2:0] s_axi_awprot,
    input wire s_axi_awvalid,
    output wire s_axi_awready,
    input wire [31:0] s_axi_wdata,
    input wire [3:0] s_axi_wstrb,
    input wire s_axi_wvalid,
    output wire s_axi_wready,
    output reg [1:0] s_axi_bresp,
    output reg s_axi_bvalid,
    input wire s_axi_bready,
    input wire [7:0] s_axi_araddr,
    input wire [2:0] s_axi_arprot,
    input wire s_axi_arvalid,
    output wire s_axi_arready,
    output reg [31:0] s_axi_rdata,
    output reg [1:0] s_axi_rresp,
    output reg s_axi_rvalid,
    input wire s_axi_rready
);
    reg have_aw, have_w;
    reg [7:0] write_addr;
    reg [31:0] write_data;
    reg [3:0] write_strb;
    reg clear_pulse;
    wire [7:0] sampled, sticky;
    wire [31:0] ticks;
    wire [255:0] counts, last_ticks;

    assign s_axi_awready = !have_aw && !s_axi_bvalid;
    assign s_axi_wready = !have_w && !s_axi_bvalid;
    assign s_axi_arready = !s_axi_rvalid;

    ad9361_overload_monitor monitor (
        .clk(clk), .rst_n(rst_n), .clear(clear_pulse),
        .ctrl_out_async(ctrl_out_async),
        .ctrl_out_sampled(sampled), .sticky(sticky), .ticks(ticks),
        .event_counts(counts), .last_timestamps(last_ticks)
    );

    function [31:0] read_csr;
        input [7:0] addr;
        input [7:0] flags;
        input [7:0] pins;
        input [31:0] time_now;
        input [255:0] event_data;
        input [255:0] timestamp_data;
        integer idx;
        begin
            read_csr = 32'b0;
            if (addr == 8'h00)
                read_csr = {24'b0, flags};
            else if (addr == 8'h04)
                read_csr = time_now;
            else if (addr == 8'h0C)
                read_csr = {24'b0, pins};
            else if (addr >= 8'h20 && addr <= 8'h3C && addr[1:0] == 2'b00) begin
                idx = (addr - 8'h20) >> 2;
                read_csr = event_data[idx*32 +: 32];
            end else if (addr >= 8'h40 && addr <= 8'h5C && addr[1:0] == 2'b00) begin
                idx = (addr - 8'h40) >> 2;
                read_csr = timestamp_data[idx*32 +: 32];
            end
        end
    endfunction

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            have_aw <= 1'b0;
            have_w <= 1'b0;
            write_addr <= 8'b0;
            write_data <= 32'b0;
            write_strb <= 4'b0;
            s_axi_bvalid <= 1'b0;
            s_axi_bresp <= 2'b00;
            s_axi_rvalid <= 1'b0;
            s_axi_rresp <= 2'b00;
            s_axi_rdata <= 32'b0;
            clear_pulse <= 1'b0;
        end else begin
            clear_pulse <= 1'b0;
            if (s_axi_awvalid && s_axi_awready) begin
                have_aw <= 1'b1;
                write_addr <= s_axi_awaddr;
            end
            if (s_axi_wvalid && s_axi_wready) begin
                have_w <= 1'b1;
                write_data <= s_axi_wdata;
                write_strb <= s_axi_wstrb;
            end
            if (have_aw && have_w && !s_axi_bvalid) begin
                s_axi_bvalid <= 1'b1;
                s_axi_bresp <= (write_addr == 8'h08) ? 2'b00 : 2'b10;
                if (write_addr == 8'h08 && write_strb[0] && write_data[0])
                    clear_pulse <= 1'b1;
                have_aw <= 1'b0;
                have_w <= 1'b0;
            end
            if (s_axi_bvalid && s_axi_bready)
                s_axi_bvalid <= 1'b0;

            if (s_axi_arvalid && s_axi_arready) begin
                s_axi_rvalid <= 1'b1;
                s_axi_rresp <= 2'b00;
                s_axi_rdata <= read_csr(s_axi_araddr, sticky, sampled,
                                         ticks, counts, last_ticks);
            end
            if (s_axi_rvalid && s_axi_rready)
                s_axi_rvalid <= 1'b0;
        end
    end
endmodule
