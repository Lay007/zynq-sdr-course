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
      .payload_bit_errors(payload_errors)
  );

  always #5 clk = ~clk;

  task run_with_error(input integer error_bit, input integer expected_payload_errors);
    begin
      rst = 1'b1; start = 1'b0; in_valid = 1'b0;
      repeat (3) @(negedge clk);
      rst = 1'b0;
      @(negedge clk); start = 1'b1;
      @(negedge clk); start = 1'b0;

      for (symbol_index = 0; symbol_index < SYMBOLS; symbol_index = symbol_index + 1) begin
        in_dibit[0] = frame_bits[2*symbol_index];
        in_dibit[1] = frame_bits[2*symbol_index+1];
        if (error_bit == 2*symbol_index)
          in_dibit[0] = ~in_dibit[0];
        if (error_bit == 2*symbol_index+1)
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
      if (received_symbols != SYMBOLS || total_errors != 1 ||
          payload_errors != expected_payload_errors) begin
        $display("FAIL: error_bit=%0d recv=%0d total=%0d payload=%0d done=%0d",
                 error_bit, received_symbols, total_errors, payload_errors, done);
        $fatal(1);
      end
      $display("PASS case: error_bit=%0d total=%0d payload=%0d",
               error_bit, total_errors, payload_errors);
    end
  endtask

  initial begin
    $readmemb("blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem", frame_bits);
    run_with_error(5, 0);   // tolerated preamble error
    run_with_error(30, 1);  // payload error
    $display("PASS: QPSK payload-error telemetry distinguishes preamble from payload");
    $finish;
  end
endmodule
