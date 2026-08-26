`timescale 1ns/1ps

// Shared-clock AXI4-Stream + AXI4-Lite integration wrapper for the educational
// SF7 detector. Stream traffic carries samples/results; AXI-Lite exposes stable
// identification, status, the last result snapshot, counters, and an IRQ.
module css_sf7_axi_accelerator #(
    parameter integer AXI_ADDR_W = 6,
    parameter integer AXI_DATA_W = 32,
    parameter TWIDDLE_I_FILE =
        "blocks/block_08_modulation_and_synchronization/tb/vectors/css_sf7_twiddle_i_q15.hex",
    parameter TWIDDLE_Q_FILE =
        "blocks/block_08_modulation_and_synchronization/tb/vectors/css_sf7_twiddle_q_q15.hex"
) (
    input  wire                         aclk,
    input  wire                         aresetn,

    input  wire                         s_axis_tvalid,
    output wire                         s_axis_tready,
    input  wire [31:0]                  s_axis_tdata,
    input  wire                         s_axis_tlast,
    output wire                         m_axis_tvalid,
    input  wire                         m_axis_tready,
    output wire [255:0]                 m_axis_tdata,
    output wire                         m_axis_tlast,

    input  wire [AXI_ADDR_W-1:0]        s_axi_awaddr,
    input  wire                         s_axi_awvalid,
    output reg                          s_axi_awready,
    input  wire [AXI_DATA_W-1:0]        s_axi_wdata,
    input  wire [(AXI_DATA_W/8)-1:0]    s_axi_wstrb,
    input  wire                         s_axi_wvalid,
    output reg                          s_axi_wready,
    output reg  [1:0]                   s_axi_bresp,
    output reg                          s_axi_bvalid,
    input  wire                         s_axi_bready,
    input  wire [AXI_ADDR_W-1:0]        s_axi_araddr,
    input  wire                         s_axi_arvalid,
    output reg                          s_axi_arready,
    output reg  [AXI_DATA_W-1:0]        s_axi_rdata,
    output reg  [1:0]                   s_axi_rresp,
    output reg                          s_axi_rvalid,
    input  wire                         s_axi_rready,

    output wire                         irq
);

    localparam integer AXI_STRB_W = AXI_DATA_W / 8;
    localparam [AXI_ADDR_W-1:0] REG_ID = 6'h00;
    localparam [AXI_ADDR_W-1:0] REG_VERSION = 6'h04;
    localparam [AXI_ADDR_W-1:0] REG_CONTROL = 6'h08;
    localparam [AXI_ADDR_W-1:0] REG_STATUS = 6'h0C;
    localparam [AXI_ADDR_W-1:0] REG_RESULT0 = 6'h10;
    localparam [AXI_ADDR_W-1:0] REG_RESULT1 = 6'h14;
    localparam [AXI_ADDR_W-1:0] REG_RESULT2 = 6'h18;
    localparam [AXI_ADDR_W-1:0] REG_RESULT3 = 6'h1C;
    localparam [AXI_ADDR_W-1:0] REG_RESULT4 = 6'h20;
    localparam [AXI_ADDR_W-1:0] REG_RESULT5 = 6'h24;
    localparam [AXI_ADDR_W-1:0] REG_RESULT6 = 6'h28;
    localparam [AXI_ADDR_W-1:0] REG_RESULT7 = 6'h2C;
    localparam [AXI_ADDR_W-1:0] REG_COMPLETED_COUNT = 6'h30;
    localparam [AXI_ADDR_W-1:0] REG_FRAME_ERROR_COUNT = 6'h34;
    localparam [AXI_DATA_W-1:0] CORE_ID = 32'h43535337; // "CSS7"
    localparam [AXI_DATA_W-1:0] CORE_VERSION = 32'h00010000;

    wire detector_busy;
    reg m_axis_tvalid_d;
    wire result_pulse = m_axis_tvalid && !m_axis_tvalid_d;

    reg irq_enable;
    reg done_sticky;
    reg frame_error_sticky;
    reg [255:0] last_result;
    reg [31:0] completed_count;
    reg [31:0] frame_error_count;

    reg [AXI_ADDR_W-1:0] awaddr_latched;
    reg awaddr_valid;
    reg [AXI_DATA_W-1:0] wdata_latched;
    reg [AXI_STRB_W-1:0] wstrb_latched;
    reg wdata_valid;
    reg [AXI_DATA_W-1:0] read_word;

    assign irq = irq_enable && done_sticky;

    css_sf7_axis_detector #(
        .TWIDDLE_I_FILE(TWIDDLE_I_FILE),
        .TWIDDLE_Q_FILE(TWIDDLE_Q_FILE)
    ) u_axis_detector (
        .aclk          (aclk),
        .aresetn       (aresetn),
        .s_axis_tvalid (s_axis_tvalid),
        .s_axis_tready (s_axis_tready),
        .s_axis_tdata  (s_axis_tdata),
        .s_axis_tlast  (s_axis_tlast),
        .m_axis_tvalid (m_axis_tvalid),
        .m_axis_tready (m_axis_tready),
        .m_axis_tdata  (m_axis_tdata),
        .m_axis_tlast  (m_axis_tlast),
        .detector_busy (detector_busy)
    );

    always @(*) begin
        case (s_axi_araddr)
            REG_ID: read_word = CORE_ID;
            REG_VERSION: read_word = CORE_VERSION;
            REG_CONTROL: read_word = {{(AXI_DATA_W-1){1'b0}}, irq_enable};
            REG_STATUS: read_word = {
                {(AXI_DATA_W-5){1'b0}},
                frame_error_sticky,
                done_sticky,
                m_axis_tvalid,
                s_axis_tready,
                detector_busy
            };
            REG_RESULT0: read_word = last_result[31:0];
            REG_RESULT1: read_word = last_result[63:32];
            REG_RESULT2: read_word = last_result[95:64];
            REG_RESULT3: read_word = last_result[127:96];
            REG_RESULT4: read_word = last_result[159:128];
            REG_RESULT5: read_word = last_result[191:160];
            REG_RESULT6: read_word = last_result[223:192];
            REG_RESULT7: read_word = last_result[255:224];
            REG_COMPLETED_COUNT: read_word = completed_count;
            REG_FRAME_ERROR_COUNT: read_word = frame_error_count;
            default: read_word = {AXI_DATA_W{1'b0}};
        endcase
    end

    always @(posedge aclk) begin
        if (!aresetn) begin
            s_axi_awready <= 1'b0;
            s_axi_wready <= 1'b0;
            s_axi_bresp <= 2'b00;
            s_axi_bvalid <= 1'b0;
            s_axi_arready <= 1'b0;
            s_axi_rdata <= {AXI_DATA_W{1'b0}};
            s_axi_rresp <= 2'b00;
            s_axi_rvalid <= 1'b0;
            irq_enable <= 1'b0;
            done_sticky <= 1'b0;
            frame_error_sticky <= 1'b0;
            last_result <= 256'd0;
            completed_count <= 32'd0;
            frame_error_count <= 32'd0;
            m_axis_tvalid_d <= 1'b0;
            awaddr_latched <= {AXI_ADDR_W{1'b0}};
            awaddr_valid <= 1'b0;
            wdata_latched <= {AXI_DATA_W{1'b0}};
            wstrb_latched <= {AXI_STRB_W{1'b0}};
            wdata_valid <= 1'b0;
        end else begin
            m_axis_tvalid_d <= m_axis_tvalid;

            s_axi_awready <= (!awaddr_valid) && (!s_axi_bvalid);
            s_axi_wready <= (!wdata_valid) && (!s_axi_bvalid);
            s_axi_arready <= (!s_axi_rvalid);

            if (s_axi_awready && s_axi_awvalid) begin
                awaddr_latched <= s_axi_awaddr;
                awaddr_valid <= 1'b1;
            end
            if (s_axi_wready && s_axi_wvalid) begin
                wdata_latched <= s_axi_wdata;
                wstrb_latched <= s_axi_wstrb;
                wdata_valid <= 1'b1;
            end

            if (awaddr_valid && wdata_valid && !s_axi_bvalid) begin
                if (awaddr_latched == REG_CONTROL) begin
                    if (wstrb_latched[0])
                        irq_enable <= wdata_latched[0];
                    if (wstrb_latched[1] && wdata_latched[8])
                        done_sticky <= 1'b0;
                    if (wstrb_latched[1] && wdata_latched[9])
                        frame_error_sticky <= 1'b0;
                    if (wstrb_latched[1] && wdata_latched[10]) begin
                        completed_count <= 32'd0;
                        frame_error_count <= 32'd0;
                    end
                end
                awaddr_valid <= 1'b0;
                wdata_valid <= 1'b0;
                s_axi_bvalid <= 1'b1;
                s_axi_bresp <= 2'b00;
            end
            if (s_axi_bvalid && s_axi_bready)
                s_axi_bvalid <= 1'b0;

            if (s_axi_arready && s_axi_arvalid) begin
                s_axi_rdata <= read_word;
                s_axi_rresp <= 2'b00;
                s_axi_rvalid <= 1'b1;
            end
            if (s_axi_rvalid && s_axi_rready)
                s_axi_rvalid <= 1'b0;

            if (result_pulse) begin
                last_result <= m_axis_tdata;
                done_sticky <= 1'b1;
                completed_count <= completed_count + 1'b1;
                if (m_axis_tdata[15]) begin
                    frame_error_sticky <= 1'b1;
                    frame_error_count <= frame_error_count + 1'b1;
                end
            end
        end
    end

endmodule
