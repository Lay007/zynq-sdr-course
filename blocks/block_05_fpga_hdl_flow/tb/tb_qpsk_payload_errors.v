// Verify that the QPSK BER wrapper preserves the underlying preamble/payload
// split instead of exporting a permanent zero in the payload-error register.

`timescale 1ns/1ps

module tb_qpsk_payload_errors;
  localparam INDEX_W = 16;
  localparam SYMBOLS = 140;
  localparam BITS = 280;

  reg clk = 1'b0, rst = 1'b1, start = 1'b0, in_valid = 1'b0;
  reg [1:0] in_dibit = 2'b00;
  reg frame_bits [0:511];  // generated ROM is padded to MAX_FRAME_BITS
  wire busy, done;
  wire [INDEX_W-1:0] received_symbols, total_errors, payload_errors;
  wire [31:0] payload_error_segments;
  wire [INDEX_W-1:0] first_payload_error_index, last_payload_error_index;
  integer symbol_index, wait_cycles;

  qpsk_ber_counter #(
      .INDEX_W(INDEX_W), .MAX_FRAME_BITS(512),
      .LOCK_PREAMBLE_BITS(24), .LOCK_ERR_TOL(3)
  ) dut (
      .clk(clk), .rst(rst), .start(start), .abort(1'b0),
      .symbol_count(SYMBOLS[INDEX_W-1:0]), .preamble_count(16'd24),
      .in_valid(in_valid), .in_dibit(in_dibit),
      .busy(busy), .done(done), .quadrant_swapped(),
      .received_symbols(received_symbols), .total_bit_errors(total_errors),
      .payload_bit_errors(payload_errors),
      .payload_error_segments(payload_error_segments),
      .first_payload_error_index(first_payload_error_index),
      .last_payload_error_index(last_payload_error_index)
  );

  always #5 clk = ~clk;

  task run_case(
      input integer case_id,
      input integer expected_total_errors,
      input integer expected_payload_errors,
      input [31:0] expected_segments,
      input [INDEX_W-1:0] expected_first,
      input [INDEX_W-1:0] expected_last
  );
    integer bit_i, bit_q;
    begin
      rst = 1'b1; start = 1'b0; in_valid = 1'b0;
      repeat (3) @(negedge clk);
      rst = 1'b0;
      @(negedge clk); start = 1'b1;
      @(negedge clk); start = 1'b0;

      for (symbol_index = 0; symbol_index < SYMBOLS; symbol_index = symbol_index + 1) begin
        bit_i = 2*symbol_index;
        bit_q = 2*symbol_index+1;
        in_dibit[0] = frame_bits[2*symbol_index];
        in_dibit[1] = frame_bits[2*symbol_index+1];
        if ((case_id == 0 && bit_i == 5) ||
            (case_id == 1 && bit_i == 30) ||
            (case_id == 2 && (bit_i == 30 || bit_i == 100 || bit_i == 170 || bit_i == 250)))
          in_dibit[0] = ~in_dibit[0];
        if ((case_id == 0 && bit_q == 5) ||
            (case_id == 1 && bit_q == 30) ||
            (case_id == 2 && (bit_q == 30 || bit_q == 100 || bit_q == 170 || bit_q == 250)))
          in_dibit[1] = ~in_dibit[1];
        in_valid = 1'b1;
        @(negedge clk);
        in_valid = 1'b0;
        repeat (3) @(negedge clk);
      end

      wait_cycles = 0;
      while (!done && wait_cycles < 64) begin
        @(posedge clk);
        wait_cycles = wait_cycles + 1;
      end
      #1;
      if (received_symbols != SYMBOLS || total_errors != expected_total_errors ||
          payload_errors != expected_payload_errors ||
          payload_error_segments != expected_segments ||
          first_payload_error_index != expected_first ||
          last_payload_error_index != expected_last) begin
        $display("FAIL: case=%0d recv=%0d total=%0d payload=%0d seg=%08x first=%0d last=%0d done=%0d",
                 case_id, received_symbols, total_errors, payload_errors,
                 payload_error_segments, first_payload_error_index,
                 last_payload_error_index, done);
        $fatal(1);
      end
      $display("PASS case=%0d total=%0d payload=%0d seg=%08x first=%0d last=%0d",
               case_id, total_errors, payload_errors, payload_error_segments,
               first_payload_error_index, last_payload_error_index);
    end
  endtask

  initial begin
    $readmemb("blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem", frame_bits);
    run_case(0, 1, 0, 32'h00000000, 16'hffff, 16'hffff); // tolerated preamble error
    run_case(1, 1, 1, 32'h00000001, 16'd6, 16'd6);       // first payload quarter
    run_case(2, 4, 4, 32'h01010101, 16'd6, 16'd226);     // one error per quarter
    $display("PASS: QPSK payload-error telemetry reports region, quarters and first/last index");
    $finish;
  end
endmodule
