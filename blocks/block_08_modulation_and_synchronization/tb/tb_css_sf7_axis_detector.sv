`timescale 1ns/1ps

module tb_css_sf7_axis_detector;

    localparam integer N = 128;
    localparam integer MAX_RESULT_CYCLES = 17000;

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
    wire detector_busy;

    integer input_file;
    integer expected_file;
    integer case_index;
    integer sample_index;
    integer input_re;
    integer input_im;
    integer expected_peak;
    integer expected_second;
    integer expected_overflow;
    integer scan_count;
    integer wait_cycles;
    integer errors = 0;
    reg [255:0] held_result;

    always #5 aclk = ~aclk;

    css_sf7_axis_detector dut (
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

    task automatic fail;
        input [511:0] message;
        begin
            $display("FAIL %0s", message);
            errors = errors + 1;
        end
    endtask

    task automatic send_symbol;
        input integer inject_early_tlast;
        begin
            @(negedge aclk);
            for (sample_index = 0; sample_index < N; sample_index = sample_index + 1) begin
                scan_count = $fscanf(input_file, "%d %d", input_re, input_im);
                if (scan_count != 2) begin
                    $display("FAIL truncated AXIS input case=%0d sample=%0d", case_index, sample_index);
                    $fatal(1);
                end
                while (s_axis_tready !== 1'b1)
                    @(negedge aclk);
                s_axis_tvalid = 1'b1;
                s_axis_tdata = {input_im[15:0], input_re[15:0]};
                s_axis_tlast = (sample_index == 127) ||
                               (inject_early_tlast && sample_index == 17);
                @(negedge aclk);
            end
            s_axis_tvalid = 1'b0;
            s_axis_tdata = 32'd0;
            s_axis_tlast = 1'b0;
        end
    endtask

    task automatic check_result;
        input integer expected_frame_error;
        integer hold_cycle;
        begin
            wait_cycles = 0;
            while (m_axis_tvalid !== 1'b1 && wait_cycles < MAX_RESULT_CYCLES) begin
                @(posedge aclk);
                #1;
                wait_cycles = wait_cycles + 1;
            end
            if (m_axis_tvalid !== 1'b1) begin
                $display("FAIL AXIS result timeout case=%0d", case_index);
                $fatal(1);
            end

            held_result = m_axis_tdata;
            if (m_axis_tlast !== 1'b1)
                fail("result packet must assert TLAST");
            if (s_axis_tready !== 1'b0)
                fail("stalled result must backpressure the next input symbol");

            for (hold_cycle = 0; hold_cycle < 5; hold_cycle = hold_cycle + 1) begin
                @(posedge aclk);
                #1;
                if (m_axis_tvalid !== 1'b1 || m_axis_tdata !== held_result)
                    fail("result changed while M_AXIS was stalled");
            end

            if (m_axis_tdata[6:0] !== expected_peak[6:0])
                fail("packed peak bin mismatch");
            if (m_axis_tdata[14:8] !== expected_second[6:0])
                fail("packed second bin mismatch");
            if (m_axis_tdata[15] !== expected_frame_error[0])
                fail("packed frame error mismatch");
            if (m_axis_tdata[31:16] !== expected_overflow[15:0])
                fail("packed overflow count mismatch");
            if (m_axis_tdata[95:32] <= m_axis_tdata[159:96])
                fail("packed peak magnitude is not greater than second magnitude");
            if (m_axis_tdata[255:160] !== 96'd0)
                fail("reserved result bits are not zero");

            @(negedge aclk);
            m_axis_tready = 1'b1;
            @(posedge aclk);
            #1;
            if (m_axis_tvalid !== 1'b0)
                fail("result valid did not clear after handshake");
            @(negedge aclk);
            m_axis_tready = 1'b0;
        end
    endtask

    initial begin
        input_file = $fopen(
            "blocks/block_08_modulation_and_synchronization/tb/vectors/css_sf7_detector_input.txt",
            "r"
        );
        expected_file = $fopen(
            "blocks/block_08_modulation_and_synchronization/tb/vectors/css_sf7_detector_expected.txt",
            "r"
        );
        if (input_file == 0 || expected_file == 0) begin
            $display("FAIL missing generated SF7 AXIS vectors");
            $fatal(1);
        end

        repeat (3) @(posedge aclk);
        #1;
        if (s_axis_tready !== 1'b0 || m_axis_tvalid !== 1'b0 || detector_busy !== 1'b0)
            fail("AXIS wrapper reset outputs are not idle");

        @(negedge aclk);
        aresetn = 1'b1;
        @(posedge aclk);
        #1;
        if (s_axis_tready !== 1'b1)
            fail("AXIS wrapper did not become ready after reset");

        for (case_index = 0; case_index < 2; case_index = case_index + 1) begin
            scan_count = $fscanf(
                expected_file,
                "%d %d %d",
                expected_peak,
                expected_second,
                expected_overflow
            );
            if (scan_count != 3) begin
                $display("FAIL truncated AXIS expected case=%0d", case_index);
                $fatal(1);
            end

            send_symbol(case_index == 1);
            check_result(case_index == 1);
        end

        $fclose(input_file);
        $fclose(expected_file);

        if (errors == 0)
            $display("PASS tb_css_sf7_axis_detector cases=2 backpressure=5");
        else begin
            $display("FAIL tb_css_sf7_axis_detector errors=%0d", errors);
            $fatal(1);
        end
        $finish;
    end

endmodule
