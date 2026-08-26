`timescale 1ns/1ps

module tb_css_sf7_axi_accelerator;

    localparam integer AXI_ADDR_W = 6;
    localparam integer AXI_DATA_W = 32;
    localparam integer N = 128;
    localparam integer MAX_RESULT_CYCLES = 17000;
    localparam [5:0] REG_ID = 6'h00;
    localparam [5:0] REG_VERSION = 6'h04;
    localparam [5:0] REG_CONTROL = 6'h08;
    localparam [5:0] REG_STATUS = 6'h0C;
    localparam [5:0] REG_RESULT0 = 6'h10;
    localparam [5:0] REG_COMPLETED_COUNT = 6'h30;
    localparam [5:0] REG_FRAME_ERROR_COUNT = 6'h34;

    reg aclk = 1'b0;
    reg aresetn = 1'b0;
    reg s_axis_tvalid = 1'b0;
    wire s_axis_tready;
    reg [31:0] s_axis_tdata = 32'd0;
    reg s_axis_tlast = 1'b0;
    wire m_axis_tvalid;
    reg m_axis_tready = 1'b0;
    wire [255:0] m_axis_tdata;
    wire m_axis_tlast;

    reg [5:0] s_axi_awaddr = 6'd0;
    reg s_axi_awvalid = 1'b0;
    wire s_axi_awready;
    reg [31:0] s_axi_wdata = 32'd0;
    reg [3:0] s_axi_wstrb = 4'd0;
    reg s_axi_wvalid = 1'b0;
    wire s_axi_wready;
    wire [1:0] s_axi_bresp;
    wire s_axi_bvalid;
    reg s_axi_bready = 1'b0;
    reg [5:0] s_axi_araddr = 6'd0;
    reg s_axi_arvalid = 1'b0;
    wire s_axi_arready;
    wire [31:0] s_axi_rdata;
    wire [1:0] s_axi_rresp;
    wire s_axi_rvalid;
    reg s_axi_rready = 1'b0;
    wire irq;

    integer input_file;
    integer sample_index;
    integer input_re;
    integer input_im;
    integer scan_count;
    integer wait_cycles;
    integer word_index;
    integer errors = 0;
    reg [31:0] readback_word;
    reg [255:0] result_snapshot;

    always #5 aclk = ~aclk;

    css_sf7_axi_accelerator dut (
        .aclk(aclk), .aresetn(aresetn),
        .s_axis_tvalid(s_axis_tvalid), .s_axis_tready(s_axis_tready),
        .s_axis_tdata(s_axis_tdata), .s_axis_tlast(s_axis_tlast),
        .m_axis_tvalid(m_axis_tvalid), .m_axis_tready(m_axis_tready),
        .m_axis_tdata(m_axis_tdata), .m_axis_tlast(m_axis_tlast),
        .s_axi_awaddr(s_axi_awaddr), .s_axi_awvalid(s_axi_awvalid),
        .s_axi_awready(s_axi_awready), .s_axi_wdata(s_axi_wdata),
        .s_axi_wstrb(s_axi_wstrb), .s_axi_wvalid(s_axi_wvalid),
        .s_axi_wready(s_axi_wready), .s_axi_bresp(s_axi_bresp),
        .s_axi_bvalid(s_axi_bvalid), .s_axi_bready(s_axi_bready),
        .s_axi_araddr(s_axi_araddr), .s_axi_arvalid(s_axi_arvalid),
        .s_axi_arready(s_axi_arready), .s_axi_rdata(s_axi_rdata),
        .s_axi_rresp(s_axi_rresp), .s_axi_rvalid(s_axi_rvalid),
        .s_axi_rready(s_axi_rready), .irq(irq)
    );

    task automatic fail;
        input [511:0] message;
        begin
            $display("FAIL %0s", message);
            errors = errors + 1;
        end
    endtask

    task automatic axi_write;
        input [5:0] addr;
        input [31:0] data;
        reg aw_done;
        reg w_done;
        begin
            aw_done = 1'b0;
            w_done = 1'b0;
            @(negedge aclk);
            s_axi_awaddr = addr;
            s_axi_awvalid = 1'b1;
            s_axi_wdata = data;
            s_axi_wstrb = 4'hF;
            s_axi_wvalid = 1'b1;
            s_axi_bready = 1'b1;
            while (!aw_done || !w_done) begin
                @(posedge aclk);
                if (s_axi_awvalid && s_axi_awready)
                    aw_done = 1'b1;
                if (s_axi_wvalid && s_axi_wready)
                    w_done = 1'b1;
                @(negedge aclk);
                if (aw_done)
                    s_axi_awvalid = 1'b0;
                if (w_done)
                    s_axi_wvalid = 1'b0;
            end
            while (!s_axi_bvalid)
                @(posedge aclk);
            if (s_axi_bresp != 2'b00)
                fail("AXI-Lite write response is not OKAY");
            @(negedge aclk);
            s_axi_bready = 1'b0;
            s_axi_awaddr = 6'd0;
            s_axi_wdata = 32'd0;
            s_axi_wstrb = 4'd0;
        end
    endtask

    task automatic axi_read;
        input [5:0] addr;
        output [31:0] data;
        reg ar_done;
        begin
            ar_done = 1'b0;
            @(negedge aclk);
            s_axi_araddr = addr;
            s_axi_arvalid = 1'b1;
            s_axi_rready = 1'b1;
            while (!ar_done) begin
                @(posedge aclk);
                if (s_axi_arvalid && s_axi_arready)
                    ar_done = 1'b1;
                @(negedge aclk);
                if (ar_done)
                    s_axi_arvalid = 1'b0;
            end
            while (!s_axi_rvalid)
                @(posedge aclk);
            if (s_axi_rresp != 2'b00)
                fail("AXI-Lite read response is not OKAY");
            data = s_axi_rdata;
            @(negedge aclk);
            s_axi_rready = 1'b0;
            s_axi_araddr = 6'd0;
        end
    endtask

    initial begin
        input_file = $fopen(
            "blocks/block_08_modulation_and_synchronization/tb/vectors/css_sf7_detector_input.txt",
            "r"
        );
        if (input_file == 0) begin
            $display("FAIL missing generated AXI accelerator vectors");
            $fatal(1);
        end

        repeat (3) @(posedge aclk);
        #1;
        if (irq !== 1'b0 || m_axis_tvalid !== 1'b0)
            fail("AXI accelerator reset outputs are not idle");
        @(negedge aclk);
        aresetn = 1'b1;

        axi_read(REG_ID, readback_word);
        if (readback_word !== 32'h43535337)
            fail("AXI-Lite ID register mismatch");
        axi_read(REG_VERSION, readback_word);
        if (readback_word !== 32'h00010000)
            fail("AXI-Lite version register mismatch");
        axi_read(REG_STATUS, readback_word);
        if (readback_word[4:0] !== 5'b00010)
            fail("AXI-Lite reset status mismatch");

        axi_write(REG_CONTROL, 32'h00000001);
        axi_read(REG_CONTROL, readback_word);
        if (readback_word !== 32'h00000001)
            fail("IRQ enable readback mismatch");

        @(negedge aclk);
        for (sample_index = 0; sample_index < N; sample_index = sample_index + 1) begin
            scan_count = $fscanf(input_file, "%d %d", input_re, input_im);
            if (scan_count != 2) begin
                $display("FAIL truncated accelerator input sample=%0d", sample_index);
                $fatal(1);
            end
            while (s_axis_tready !== 1'b1)
                @(negedge aclk);
            s_axis_tvalid = 1'b1;
            s_axis_tdata = {input_im[15:0], input_re[15:0]};
            s_axis_tlast = (sample_index == 17) || (sample_index == 127);
            @(negedge aclk);
        end
        s_axis_tvalid = 1'b0;
        s_axis_tdata = 32'd0;
        s_axis_tlast = 1'b0;

        wait_cycles = 0;
        while (irq !== 1'b1 && wait_cycles < MAX_RESULT_CYCLES) begin
            @(posedge aclk);
            #1;
            wait_cycles = wait_cycles + 1;
        end
        if (irq !== 1'b1) begin
            $display("FAIL AXI accelerator IRQ timeout");
            $fatal(1);
        end
        if (m_axis_tvalid !== 1'b1 || m_axis_tlast !== 1'b1)
            fail("AXI result packet is not pending at IRQ");
        result_snapshot = m_axis_tdata;
        if (result_snapshot[15] !== 1'b1)
            fail("AXI result did not retain injected TLAST error");

        axi_read(REG_STATUS, readback_word);
        if (readback_word[4:0] !== 5'b11101)
            fail("AXI-Lite completed status mismatch");
        for (word_index = 0; word_index < 8; word_index = word_index + 1) begin
            axi_read(REG_RESULT0 + word_index * 4, readback_word);
            if (readback_word !== result_snapshot[word_index*32 +: 32])
                fail("AXI-Lite result snapshot mismatch");
        end
        axi_read(REG_COMPLETED_COUNT, readback_word);
        if (readback_word !== 32'd1)
            fail("completed symbol count mismatch");
        axi_read(REG_FRAME_ERROR_COUNT, readback_word);
        if (readback_word !== 32'd1)
            fail("frame error count mismatch");

        @(negedge aclk);
        m_axis_tready = 1'b1;
        @(posedge aclk);
        #1;
        @(negedge aclk);
        m_axis_tready = 1'b0;
        axi_read(REG_STATUS, readback_word);
        if (readback_word[4:0] !== 5'b11010)
            fail("status did not preserve sticky bits after result transfer");

        axi_write(REG_CONTROL, 32'h00000701);
        if (irq !== 1'b0)
            fail("IRQ did not clear with done sticky flag");
        axi_read(REG_STATUS, readback_word);
        if (readback_word[4:0] !== 5'b00010)
            fail("status sticky flags did not clear");
        axi_read(REG_COMPLETED_COUNT, readback_word);
        if (readback_word !== 32'd0)
            fail("completed counter did not clear");
        axi_read(REG_FRAME_ERROR_COUNT, readback_word);
        if (readback_word !== 32'd0)
            fail("frame error counter did not clear");
        axi_read(6'h3C, readback_word);
        if (readback_word !== 32'd0)
            fail("undefined AXI-Lite register is not zero");

        $fclose(input_file);
        if (errors == 0)
            $display("PASS tb_css_sf7_axi_accelerator registers=14 irq=1");
        else begin
            $display("FAIL tb_css_sf7_axi_accelerator errors=%0d", errors);
            $fatal(1);
        end
        $finish;
    end

endmodule
