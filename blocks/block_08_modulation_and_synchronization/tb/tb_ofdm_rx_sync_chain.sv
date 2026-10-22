`timescale 1ns/1ps

// Issue #48, stage 4b: a continuous received stream -> ofdm_frame_sync -> ofdm_axi_modem receiver.
//
// +IQ=<file>        received samples "re im" (Q1.15), one per line, a continuous stream with silence,
//                   the sync preamble, the training symbol(s) and the data (tools/ofdm_rf_link.py);
// +SYNC_OUT=<file>  every sample the frame synchronizer hands to the modem, "re im last";
// +BITS_OUT=<file>  every decided carrier, "data_index bits".
//
// The samples arrive one every SAMPLE_GAP clocks (48 = 2.083 MS/s at 100 MHz, as on the board;
// tools/run_ofdm_sync_chain.py passes that). The modem is reset before the stream starts, so the first
// symbol of the frame trains it. One RESULT line: frames found / missed, samples handed over, output
// FIFO overflows, symbols decided, the modem's flags.
//
// Without plusargs the bench checks itself on committed vectors
// (tools/generate_ofdm_sync_chain_vectors.py: one frame, SNR 30 dB, CFO 3 kHz, fractional delay):
// exactly one frame found, no overflow, no frame error, every data bit pair right.
module tb_ofdm_rx_sync_chain;
    parameter integer FRAME_SYMBOLS = 5;     // the committed vectors: 1 training + 4 data symbols
    parameter integer CE_TRAIN_SYMBOLS = 1;
    parameter integer SAMPLE_GAP = 12;       // CI: the modem receiver keeps up only from 9-12 clocks per sample on (8 overflowed)
    localparam integer DATA_PAIRS = 48 * (FRAME_SYMBOLS - CE_TRAIN_SYMBOLS);

    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg rst = 1'b1;

    wire              rx_ready;
    reg               in_valid = 1'b0;
    reg signed [15:0] in_re = 0, in_im = 0;
    wire              s_valid, s_last, s_start;
    wire signed [15:0] s_re, s_im;
    wire [15:0]       found, missed, overflows;

    ofdm_frame_sync sync (
        .clk(clk), .rst(rst), .dc_rst(rst), .frame_symbols(FRAME_SYMBOLS[7:0]),
        .in_valid(in_valid), .in_re(in_re), .in_im(in_im),
        .out_valid(s_valid), .out_ready(rx_ready), .out_re(s_re), .out_im(s_im), .out_last(s_last),
        .frame_start(s_start), .frames_found(found), .frames_missed(missed), .overflows(overflows)
    );

    wire        rxo_valid, rxo_last;
    wire [7:0]  rxo_data;
    wire        txo_valid, txo_last, tx_ready;
    wire [31:0] txo_data;
    wire        awready, wready, bvalid, arready, rvalid;
    wire [1:0]  bresp, rresp;
    wire [31:0] rdata;

    ofdm_axi_modem #(.CE_TRAIN_SYMBOLS(CE_TRAIN_SYMBOLS)) modem (
        .aclk(clk), .aresetn(!rst),
        .s_axis_tx_tvalid(1'b0), .s_axis_tx_tready(tx_ready), .s_axis_tx_tdata(8'd0), .s_axis_tx_tlast(1'b0),
        .m_axis_tx_tvalid(txo_valid), .m_axis_tx_tready(1'b1), .m_axis_tx_tdata(txo_data), .m_axis_tx_tlast(txo_last),
        .s_axis_rx_tvalid(s_valid), .s_axis_rx_tready(rx_ready), .s_axis_rx_tdata({s_im, s_re}), .s_axis_rx_tlast(s_last),
        .m_axis_rx_tvalid(rxo_valid), .m_axis_rx_tready(1'b1), .m_axis_rx_tdata(rxo_data), .m_axis_rx_tlast(rxo_last),
        .s_axi_awaddr(6'd0), .s_axi_awvalid(1'b0), .s_axi_awready(awready),
        .s_axi_wdata(32'd0), .s_axi_wstrb(4'd0), .s_axi_wvalid(1'b0), .s_axi_wready(wready),
        .s_axi_bresp(bresp), .s_axi_bvalid(bvalid), .s_axi_bready(1'b1),
        .s_axi_araddr(6'd0), .s_axi_arvalid(1'b0), .s_axi_arready(arready),
        .s_axi_rdata(rdata), .s_axi_rresp(rresp), .s_axi_rvalid(rvalid), .s_axi_rready(1'b1)
    );

    integer in_fd, sync_fd = 0, bits_fd = 0, r, re, im, n_in = 0, n_sync = 0, n_sym = 0, n_pairs = 0;
    integer exp_fd, errors = 0, k;
    reg selfcheck = 1'b0;
    reg [1023:0] in_name, sync_name, bits_name;
    reg [1:0] expected [0:1023];
    reg [1:0] decided [0:1023];
    reg [1023:0] seen;

    always @(posedge clk) begin
        if (s_valid && rx_ready) begin
            if (!selfcheck) $fwrite(sync_fd, "%0d %0d %0d\n", s_re, s_im, s_last);
            n_sync = n_sync + 1;
        end
        if (rxo_valid) begin
            if (!selfcheck) $fwrite(bits_fd, "%0d %0d\n", rxo_data[7:2], rxo_data[1:0]);
            if (n_sym * 48 + rxo_data[7:2] < 1024) begin
                decided[n_sym * 48 + rxo_data[7:2]] = rxo_data[1:0];
                seen[n_sym * 48 + rxo_data[7:2]] = 1'b1;
            end
            n_pairs = n_pairs + 1;
            if (rxo_last) n_sym = n_sym + 1;
        end
    end

    initial begin
        seen = 0;
        if (!$value$plusargs("IQ=%s", in_name)) begin
            selfcheck = 1'b1;
            in_name = "verification/vectors/block08_ofdm_sync_chain_iq.txt";
            exp_fd = $fopen("verification/vectors/block08_ofdm_sync_chain_bits.txt", "r");
            for (k = 0; k < DATA_PAIRS; k = k + 1) begin
                r = $fscanf(exp_fd, "%d\n", re);
                expected[k] = re[1:0];
            end
            $fclose(exp_fd);
        end else if (!$value$plusargs("SYNC_OUT=%s", sync_name) || !$value$plusargs("BITS_OUT=%s", bits_name)) begin
            $display("FAIL: with +IQ, +SYNC_OUT and +BITS_OUT are required");
            $fatal(1);
        end else begin
            sync_fd = $fopen(sync_name, "w");
            bits_fd = $fopen(bits_name, "w");
        end
        in_fd = $fopen(in_name, "r");
        if (in_fd == 0) begin
            $display("FAIL: cannot open %0s", in_name);
            $fatal(1);
        end
        repeat (10) @(posedge clk);
        rst = 1'b0;
        repeat (10) @(posedge clk);
        r = $fscanf(in_fd, "%d %d\n", re, im);
        while (r == 2) begin
            in_re <= re[15:0];
            in_im <= im[15:0];
            in_valid <= 1'b1;
            @(posedge clk);
            in_valid <= 1'b0;
            repeat (SAMPLE_GAP - 1) @(posedge clk);
            n_in = n_in + 1;
            r = $fscanf(in_fd, "%d %d\n", re, im);
        end
        repeat (40000) @(posedge clk);
        if (!selfcheck) begin
            $fclose(sync_fd);
            $fclose(bits_fd);
        end
        $display("RESULT inputs=%0d frames_found=%0d frames_missed=%0d sync_samples=%0d overflows=%0d rx_symbols=%0d rx_frame_error=%0d trained=%0d",
                 n_in, found, missed, n_sync, overflows, n_sym, modem.rx_frame_error_sticky, modem.ce_trained);
        if (selfcheck) begin
            for (k = 0; k < DATA_PAIRS; k = k + 1)
                if (!seen[k] || decided[k] !== expected[k]) errors = errors + 1;
            if (found == 1 && missed == 0 && overflows == 0 && n_sym == FRAME_SYMBOLS - CE_TRAIN_SYMBOLS &&
                !modem.rx_frame_error_sticky && errors == 0) begin
                $display("PASS tb_ofdm_rx_sync_chain: frame found, %0d data symbols decided, %0d bit pairs right",
                         n_sym, DATA_PAIRS);
            end else begin
                $display("FAIL tb_ofdm_rx_sync_chain: %0d wrong or missing bit pairs", errors);
                $fatal(1);
            end
        end
        $finish;
    end
endmodule
