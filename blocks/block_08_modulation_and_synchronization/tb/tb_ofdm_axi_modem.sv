`timescale 1ns/1ps

// Self-checking test of ofdm_axi_modem, the AXI4-Stream + AXI4-Lite packaging
// of the Block 8 OFDM chain:
//   1. ID/VERSION registers;
//   2. a training symbol, then SYMBOLS data symbols: s_axis_tx -> m_axis_tx
//      -> channel rotated by ANGLE_DEG -> s_axis_rx -> m_axis_rx, with random
//      stalls on the TX->RX link and random m_axis_rx_tready, BER=0;
//   3. counters, phase, coefficient and channel-equalizer registers;
//   4. CONTROL[0] datapath reset clears the counters, the coefficient and the
//      channel training; a new training symbol and one data symbol pass;
//   5. CONTROL[1] retrains: another training symbol and one data symbol pass;
//   6. a misplaced s_axis_rx_tlast sets the sticky RX frame error, and
//      CONTROL[8] clears it.
module tb_ofdm_axi_modem;
    parameter integer ANGLE_DEG = 120;
    parameter integer NORMALIZE = 1;
    localparam integer SYMBOLS = 3;
    localparam integer PAIRS = 48 * SYMBOLS;
    localparam integer ALL_PAIRS = 48 * (SYMBOLS + 2);

    localparam [5:0] REG_ID = 6'h00;
    localparam [5:0] REG_VERSION = 6'h04;
    localparam [5:0] REG_CONTROL = 6'h08;
    localparam [5:0] REG_STATUS = 6'h0C;
    localparam [5:0] REG_TX_SAT = 6'h10;
    localparam [5:0] REG_FFT_SAT = 6'h14;
    localparam [5:0] REG_EQ_SAT = 6'h18;
    localparam [5:0] REG_TX_SYMBOLS = 6'h1C;
    localparam [5:0] REG_RX_SYMBOLS = 6'h20;
    localparam [5:0] REG_PHASE = 6'h24;
    localparam [5:0] REG_COEFF = 6'h28;
    localparam [5:0] REG_CE_SAT = 6'h2C;
    localparam [5:0] REG_CE_TRAINED = 6'h30;

    reg aclk = 1'b0;
    always #5 aclk = ~aclk;
    reg aresetn = 1'b0;

    reg s_axis_tx_tvalid = 1'b0;
    wire s_axis_tx_tready;
    reg [7:0] s_axis_tx_tdata = 8'd0;
    wire m_axis_tx_tvalid;
    wire m_axis_tx_tready;
    wire [31:0] m_axis_tx_tdata;
    wire m_axis_tx_tlast;

    wire s_axis_rx_tvalid;
    wire s_axis_rx_tready;
    wire [31:0] s_axis_rx_tdata;
    wire s_axis_rx_tlast;
    wire m_axis_rx_tvalid;
    reg m_axis_rx_tready = 1'b0;
    wire [7:0] m_axis_rx_tdata;
    wire m_axis_rx_tlast;

    reg [5:0] s_axi_awaddr = 6'd0;
    reg s_axi_awvalid = 1'b0;
    wire s_axi_awready;
    reg [31:0] s_axi_wdata = 32'd0;
    reg [3:0] s_axi_wstrb = 4'h0;
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

    // TX -> channel -> RX link, with random stalls, or driven by the test
    // directly when inject_rx is set.
    reg link_open = 1'b0;
    reg inject_rx = 1'b0;
    reg inject_valid = 1'b0;
    reg inject_last = 1'b0;

    real angle_rad;
    integer rot_c;
    integer rot_s;
    integer prod_re;
    integer prod_im;
    reg signed [15:0] channel_re;
    reg signed [15:0] channel_im;
    wire signed [15:0] tx_re = m_axis_tx_tdata[15:0];
    wire signed [15:0] tx_im = m_axis_tx_tdata[31:16];

    function automatic signed [15:0] round_clip_q15;
        input integer value;
        integer rounded;
        begin
            rounded = (value >= 0) ? ((value + 16384) >>> 15) : -(((-value) + 16384) >>> 15);
            if (rounded > 32767)
                round_clip_q15 = 16'sh7fff;
            else if (rounded < -32768)
                round_clip_q15 = 16'sh8000;
            else
                round_clip_q15 = rounded[15:0];
        end
    endfunction

    always @* begin
        prod_re = tx_re * rot_c - tx_im * rot_s;
        prod_im = tx_re * rot_s + tx_im * rot_c;
        channel_re = round_clip_q15(prod_re);
        channel_im = round_clip_q15(prod_im);
    end

    assign s_axis_rx_tvalid = inject_rx ? inject_valid : (m_axis_tx_tvalid && link_open);
    assign s_axis_rx_tdata = inject_rx ? 32'd0 : {channel_im, channel_re};
    assign s_axis_rx_tlast = inject_rx ? inject_last : m_axis_tx_tlast;
    assign m_axis_tx_tready = !inject_rx && s_axis_rx_tready && link_open;

    ofdm_axi_modem #(.NORMALIZE(NORMALIZE)) dut (
        .aclk(aclk), .aresetn(aresetn),
        .s_axis_tx_tvalid(s_axis_tx_tvalid), .s_axis_tx_tready(s_axis_tx_tready),
        .s_axis_tx_tdata(s_axis_tx_tdata), .s_axis_tx_tlast(1'b0),
        .m_axis_tx_tvalid(m_axis_tx_tvalid), .m_axis_tx_tready(m_axis_tx_tready),
        .m_axis_tx_tdata(m_axis_tx_tdata), .m_axis_tx_tlast(m_axis_tx_tlast),
        .s_axis_rx_tvalid(s_axis_rx_tvalid), .s_axis_rx_tready(s_axis_rx_tready),
        .s_axis_rx_tdata(s_axis_rx_tdata), .s_axis_rx_tlast(s_axis_rx_tlast),
        .m_axis_rx_tvalid(m_axis_rx_tvalid), .m_axis_rx_tready(m_axis_rx_tready),
        .m_axis_rx_tdata(m_axis_rx_tdata), .m_axis_rx_tlast(m_axis_rx_tlast),
        .s_axi_awaddr(s_axi_awaddr), .s_axi_awvalid(s_axi_awvalid), .s_axi_awready(s_axi_awready),
        .s_axi_wdata(s_axi_wdata), .s_axi_wstrb(s_axi_wstrb), .s_axi_wvalid(s_axi_wvalid),
        .s_axi_wready(s_axi_wready), .s_axi_bresp(s_axi_bresp), .s_axi_bvalid(s_axi_bvalid),
        .s_axi_bready(s_axi_bready),
        .s_axi_araddr(s_axi_araddr), .s_axi_arvalid(s_axi_arvalid), .s_axi_arready(s_axi_arready),
        .s_axi_rdata(s_axi_rdata), .s_axi_rresp(s_axi_rresp), .s_axi_rvalid(s_axi_rvalid),
        .s_axi_rready(s_axi_rready)
    );

    reg [1:0] expected_bits [0:ALL_PAIRS-1];
    integer data_idx = 0;
    integer rx_symbol = 0;
    integer rx_pairs_in_symbol = 0;
    integer recovered_count = 0;
    integer bit_errors = 0;
    integer errors = 0;
    integer stall_cycles = 0;
    integer i;
    integer timeout;
    integer expected_phase;
    integer phase_error;
    integer seed = 32'h0FD1;
    reg [31:0] word;

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
        end
    endtask

    task automatic expect_reg;
        input [5:0] addr;
        input [31:0] expected;
        reg [31:0] value;
        begin
            axi_read(addr, value);
            if (value !== expected) begin
                $display("FAIL register 0x%02h expected 0x%08h got 0x%08h", addr, expected, value);
                errors = errors + 1;
            end
        end
    endtask

    // Random stalls on the TX->RX link and on the RX bit sink.
    always @(negedge aclk) begin
        link_open <= ($random(seed) & 3) != 0;
        m_axis_rx_tready <= ($random(seed) & 3) != 0;
        if (!link_open || !m_axis_rx_tready)
            stall_cycles = stall_cycles + 1;
    end

    always @(posedge aclk) begin
        if (aresetn && m_axis_rx_tvalid && m_axis_rx_tready) begin
            // Bits leave in FFT bin order: data indices 24..47 (bins 1..26),
            // then 0..23 (bins 38..63).
            if (m_axis_rx_tdata[7:2] !== (rx_pairs_in_symbol + 24) % 48) begin
                $display("FAIL symbol %0d pair %0d carries data index %0d, expected %0d",
                         rx_symbol, rx_pairs_in_symbol, m_axis_rx_tdata[7:2],
                         (rx_pairs_in_symbol + 24) % 48);
                errors = errors + 1;
            end
            if (m_axis_rx_tlast !== (rx_pairs_in_symbol == 47)) begin
                $display("FAIL symbol %0d pair %0d tlast=%0b", rx_symbol, rx_pairs_in_symbol, m_axis_rx_tlast);
                errors = errors + 1;
            end
            if (m_axis_rx_tdata[1:0] !== expected_bits[rx_symbol * 48 + m_axis_rx_tdata[7:2]]) begin
                bit_errors = bit_errors +
                    (m_axis_rx_tdata[1] !== expected_bits[rx_symbol * 48 + m_axis_rx_tdata[7:2]][1]) +
                    (m_axis_rx_tdata[0] !== expected_bits[rx_symbol * 48 + m_axis_rx_tdata[7:2]][0]);
            end
            recovered_count = recovered_count + 1;
            if (m_axis_rx_tlast) begin
                rx_symbol = rx_symbol + 1;
                rx_pairs_in_symbol = 0;
            end else begin
                rx_pairs_in_symbol = rx_pairs_in_symbol + 1;
            end
        end
    end

    task automatic send_value;
        input [1:0] value;
        begin
            @(negedge aclk);
            s_axis_tx_tdata = {6'd0, value};
            s_axis_tx_tvalid = 1'b1;
            @(posedge aclk);
            while (!s_axis_tx_tready)
                @(posedge aclk);
            @(negedge aclk);
            s_axis_tx_tvalid = 1'b0;
        end
    endtask

    // One data symbol; its bits are scored on m_axis_rx.
    task automatic send_data_symbol;
        integer k;
        reg [1:0] value;
        begin
            for (k = 0; k < 48; k = k + 1) begin
                value = {data_idx[0], (data_idx[1] ^ data_idx[0] ^ data_idx[6])};
                expected_bits[data_idx] = value;
                data_idx = data_idx + 1;
                send_value(value);
            end
        end
    endtask

    // The channel equalizer's training symbol (train_bits() of ofdm_channel_equalizer).
    task automatic send_training_symbol;
        integer k;
        reg [5:0] d;
        begin
            for (k = 0; k < 48; k = k + 1) begin
                d = k;
                send_value({d[0] ^ d[3], d[1] ^ d[2] ^ d[4]});
            end
        end
    endtask

    task automatic wait_pairs;
        input integer target;
        begin
            timeout = 0;
            while ((recovered_count < target) && (timeout < 60000)) begin
                @(posedge aclk);
                timeout = timeout + 1;
            end
            if (recovered_count != target) begin
                $display("FAIL expected %0d recovered pairs, got %0d", target, recovered_count);
                errors = errors + 1;
            end
        end
    endtask

    initial begin
        angle_rad = ANGLE_DEG * 3.14159265358979 / 180.0;
        rot_c = $rtoi($floor(32768.0 * $cos(angle_rad) + 0.5));
        rot_s = $rtoi($floor(32768.0 * $sin(angle_rad) + 0.5));
        if (rot_c > 32767) rot_c = 32767;
        if (rot_s > 32767) rot_s = 32767;

        repeat (4) @(posedge aclk);
        aresetn = 1'b1;
        repeat (2) @(posedge aclk);

        // 1. Identification.
        expect_reg(REG_ID, 32'h4F46444D);
        expect_reg(REG_VERSION, 32'h00020000);
        expect_reg(REG_STATUS, 32'd0);

        // 2. Training symbol, then traffic through the rotated channel.
        send_training_symbol();
        for (i = 0; i < SYMBOLS; i = i + 1)
            send_data_symbol();
        wait_pairs(PAIRS);
        if (bit_errors != 0) begin
            $display("FAIL BER nonzero: %0d/%0d bit errors", bit_errors, 2 * PAIRS);
            errors = errors + 1;
        end

        // 3. Counters and measurements. The training symbol is sent but never
        // leaves m_axis_rx. The channel equalizer has already removed the
        // channel phase from the pilots, so the pilot tracker sees about 0.
        expect_reg(REG_STATUS, 32'h40);
        expect_reg(REG_TX_SAT, 32'd0);
        expect_reg(REG_FFT_SAT, 32'd0);
        expect_reg(REG_EQ_SAT, 32'd0);
        expect_reg(REG_CE_SAT, 32'd0);
        expect_reg(REG_CE_TRAINED, 32'd1);
        expect_reg(REG_TX_SYMBOLS, SYMBOLS + 1);
        expect_reg(REG_RX_SYMBOLS, SYMBOLS);
        axi_read(REG_PHASE, word);
        expected_phase = 0;
        phase_error = $signed(word) - expected_phase;
        if (phase_error > 32767) phase_error = phase_error - 65536;
        if (phase_error < -32768) phase_error = phase_error + 65536;
        if (phase_error > 64 || phase_error < -64) begin
            $display("FAIL PHASE register %0d, expected about %0d", $signed(word), expected_phase);
            errors = errors + 1;
        end
        if (word[31:16] !== {16{word[15]}})
            fail("PHASE register is not sign-extended");
        axi_read(REG_COEFF, word);
        $display("INFO after %0d symbols: PHASE=%0d COEFF=(%0d,%0d), %0d stall cycles",
                 SYMBOLS, $signed(dut.last_phase), $signed(word[15:0]), $signed(word[31:16]), stall_cycles);

        // 4. Datapath reset.
        axi_write(REG_CONTROL, 32'h1);
        expect_reg(REG_CONTROL, 32'h1);
        expect_reg(REG_STATUS, 32'h1);
        axi_write(REG_CONTROL, 32'h0);
        expect_reg(REG_TX_SYMBOLS, 32'd0);
        expect_reg(REG_RX_SYMBOLS, 32'd0);
        expect_reg(REG_COEFF, {16'd0, 16'd16384});
        expect_reg(REG_CE_TRAINED, 32'd0);
        expect_reg(REG_STATUS, 32'd0);
        send_training_symbol();
        send_data_symbol();
        wait_pairs(PAIRS + 48);
        expect_reg(REG_STATUS, 32'h40);
        expect_reg(REG_CE_TRAINED, 32'd1);
        expect_reg(REG_RX_SYMBOLS, 32'd1);

        // 5. Retrain through CONTROL[1]: the next symbol trains again.
        axi_write(REG_CONTROL, 32'h2);
        expect_reg(REG_CONTROL, 32'h0);
        send_training_symbol();
        send_data_symbol();
        wait_pairs(PAIRS + 96);
        expect_reg(REG_CE_TRAINED, 32'd2);
        expect_reg(REG_RX_SYMBOLS, 32'd2);
        expect_reg(REG_TX_SYMBOLS, 32'd4);
        if (bit_errors != 0) begin
            $display("FAIL BER nonzero after reset/retrain: %0d bit errors", bit_errors);
            errors = errors + 1;
        end

        // 6. Misplaced tlast on s_axis_rx: sticky RX frame error, then clear.
        inject_rx = 1'b1;
        @(negedge aclk);
        inject_valid = 1'b1;
        inject_last = 1'b0;
        repeat (9) begin
            @(posedge aclk);
            while (!s_axis_rx_tready)
                @(posedge aclk);
            @(negedge aclk);
        end
        inject_last = 1'b1;
        @(posedge aclk);
        while (!s_axis_rx_tready)
            @(posedge aclk);
        @(negedge aclk);
        inject_valid = 1'b0;
        inject_last = 1'b0;
        repeat (2) @(posedge aclk);
        axi_read(REG_STATUS, word);
        if (word[4] !== 1'b1)
            fail("misplaced s_axis_rx_tlast did not set STATUS[4]");
        axi_write(REG_CONTROL, 32'h100);
        axi_read(REG_STATUS, word);
        if (word[4] !== 1'b0)
            fail("CONTROL[8] did not clear STATUS[4]");
        expect_reg(REG_CONTROL, 32'h0);

        if (errors == 0) begin
            $display("PASS: ofdm_axi_modem (NORMALIZE=%0d) %0d-degree channel recovered %0d/%0d bits in %0d symbols after a training symbol, BER=0; reset, retrain, registers and sticky errors checked",
                     NORMALIZE, ANGLE_DEG, 2 * (PAIRS + 96), 2 * (PAIRS + 96), SYMBOLS + 2);
            $finish;
        end else begin
            $display("FAIL tb_ofdm_axi_modem errors=%0d", errors);
            $fatal(1);
        end
    end
endmodule
