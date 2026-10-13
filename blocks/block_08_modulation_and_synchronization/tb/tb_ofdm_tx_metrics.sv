`timescale 1ns/1ps

// OFDM TX output for the level / PAPR / spectrum measurements of issue #48.
//
// Random bits (seeded) -> ofdm_tx_cp16_path -> sample sink that never stalls.
// The bench checks what the measurement relies on: exactly 80 samples per
// symbol, a cyclic prefix that repeats the symbol tail, no IFFT saturation and
// no frame error. With +DUMP=<file> it also writes every output sample as
// "re im" per line; tools/measure_ofdm_tx_metrics.py runs it with many symbols
// and computes peak / RMS dBFS, PAPR, occupied bandwidth and guard-band
// leakage from that file. In CI it runs with the defaults and writes nothing.
module tb_ofdm_tx_metrics;
    parameter integer MODULATION = 0;   // 0 = QPSK, 1 = Gray 16-QAM
    parameter integer SYMBOLS = 8;
    parameter integer SEED = 1;
    localparam integer BITS_W = (MODULATION != 0) ? 4 : 2;
    localparam integer GROUPS = 48 * SYMBOLS;

    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg resetn = 1'b0;
    reg bits_valid = 1'b0;
    wire bits_ready;
    reg [BITS_W-1:0] bits_in = {BITS_W{1'b0}};

    wire sample_valid, sample_last, sample_is_cp, frame_error;
    wire signed [15:0] sample_re, sample_im;
    wire [6:0] sample_index;
    wire [15:0] total_saturation_count;

    ofdm_tx_cp16_path #(.MODULATION(MODULATION)) dut (
        .clk(clk), .resetn(resetn),
        .bits_valid(bits_valid), .bits_ready(bits_ready), .bits_in(bits_in),
        .sample_valid(sample_valid), .sample_ready(1'b1),
        .sample_re(sample_re), .sample_im(sample_im),
        .sample_index(sample_index), .sample_is_cp(sample_is_cp), .sample_last(sample_last),
        .ifft_busy(), .total_saturation_count(total_saturation_count),
        .frame_error(frame_error)
    );

    integer seed = SEED;
    integer sent = 0;
    integer received = 0;
    integer errors = 0;
    integer dump_fd = 0;
    integer timeout = 0;
    integer k;
    reg [1023:0] dump_path;
    reg signed [15:0] sym_re [0:79];
    reg signed [15:0] sym_im [0:79];

    // Bit source: a new random group whenever the TX accepts one.
    always @(posedge clk) begin
        if (resetn) begin
            if (bits_valid && bits_ready) begin
                sent = sent + 1;
                if (sent == GROUPS) begin
                    bits_valid <= 1'b0;
                end else begin
                    bits_in <= $random(seed);
                end
            end
        end
    end

    // Sample sink: dump, and check each 80-sample symbol as it completes.
    always @(posedge clk) begin
        if (resetn && sample_valid) begin
            if (dump_fd != 0)
                $fwrite(dump_fd, "%0d %0d\n", sample_re, sample_im);
            sym_re[received % 80] = sample_re;
            sym_im[received % 80] = sample_im;
            if (sample_index != (received % 80)) begin
                $display("FAIL sample %0d has index %0d", received, sample_index);
                errors = errors + 1;
            end
            if (sample_last != ((received % 80) == 79)) begin
                $display("FAIL sample_last at sample %0d", received);
                errors = errors + 1;
            end
            if ((received % 80) == 79) begin
                for (k = 0; k < 16; k = k + 1) begin
                    if (sym_re[k] !== sym_re[64 + k] || sym_im[k] !== sym_im[64 + k]) begin
                        $display("FAIL symbol %0d: CP sample %0d differs from the tail", received / 80, k);
                        errors = errors + 1;
                    end
                end
            end
            received = received + 1;
        end
    end

    initial begin
        if ($value$plusargs("DUMP=%s", dump_path)) begin
            dump_fd = $fopen(dump_path, "w");
            if (dump_fd == 0) begin
                $display("FAIL cannot open the dump file");
                $fatal(1);
            end
        end
        repeat (4) @(posedge clk);
        resetn = 1'b1;
        @(negedge clk);
        bits_in = $random(seed);
        bits_valid = 1'b1;

        while (received < 80 * SYMBOLS && timeout < 1000 * SYMBOLS + 1000) begin
            @(posedge clk);
            timeout = timeout + 1;
        end
        repeat (200) @(posedge clk);

        if (dump_fd != 0)
            $fclose(dump_fd);
        if (received != 80 * SYMBOLS) begin
            $display("FAIL expected %0d samples, got %0d", 80 * SYMBOLS, received);
            errors = errors + 1;
        end
        if (total_saturation_count != 0) begin
            $display("FAIL IFFT saturation count %0d", total_saturation_count);
            errors = errors + 1;
        end
        if (frame_error) begin
            $display("FAIL frame_error");
            errors = errors + 1;
        end
        if (errors == 0) begin
            $display("PASS: tb_ofdm_tx_metrics MODULATION=%0d, %0d symbols, %0d samples, no saturation",
                     MODULATION, SYMBOLS, received);
            $finish;
        end else begin
            $display("FAIL tb_ofdm_tx_metrics errors=%0d", errors);
            $fatal(1);
        end
    end
endmodule
