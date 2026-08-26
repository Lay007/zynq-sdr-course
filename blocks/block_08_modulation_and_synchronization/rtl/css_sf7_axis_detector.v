`timescale 1ns/1ps

// AXI4-Stream boundary for the educational SF7 sequential detector.
//
// Input beat (32 bits):
//   [15:0]  signed Q1.15 I
//   [31:16] signed Q1.15 Q
// Exactly 128 accepted beats form a symbol. TLAST must be asserted only on beat
// 127. A TLAST mismatch does not alter grouping; it marks the emitted result.
//
// Output beat (256 bits):
//   [6:0]    peak bin
//   [7]      reserved, zero
//   [14:8]   second bin
//   [15]     input TLAST/frame error
//   [31:16]  dechirp saturation count
//   [95:32]  peak magnitude squared
//   [159:96] second magnitude squared
//   [255:160] reserved, zero
// One result beat is held until M_AXIS accepts it; TLAST is always asserted for
// that one-beat result packet.
module css_sf7_axis_detector #(
    parameter TWIDDLE_I_FILE =
        "blocks/block_08_modulation_and_synchronization/tb/vectors/css_sf7_twiddle_i_q15.hex",
    parameter TWIDDLE_Q_FILE =
        "blocks/block_08_modulation_and_synchronization/tb/vectors/css_sf7_twiddle_q_q15.hex"
) (
    input  wire          aclk,
    input  wire          aresetn,

    input  wire          s_axis_tvalid,
    output wire          s_axis_tready,
    input  wire [31:0]   s_axis_tdata,
    input  wire          s_axis_tlast,

    output reg           m_axis_tvalid,
    input  wire          m_axis_tready,
    output reg  [255:0]  m_axis_tdata,
    output wire          m_axis_tlast,

    output wire          detector_busy
);

    wire core_ready;
    wire core_busy;
    wire core_done;
    wire [6:0] peak_bin;
    wire [6:0] second_bin;
    wire signed [63:0] peak_magnitude_squared;
    wire signed [63:0] second_magnitude_squared;
    wire [15:0] dechirp_overflow_count;

    reg [6:0] input_beat_index;
    reg input_frame_error;

    wire input_transfer = s_axis_tvalid && s_axis_tready;
    wire output_transfer = m_axis_tvalid && m_axis_tready;
    wire expected_tlast = (input_beat_index == 7'd127);

    assign s_axis_tready = core_ready &&
                           ((!m_axis_tvalid) || m_axis_tready) &&
                           (!core_done);
    assign m_axis_tlast = 1'b1;
    assign detector_busy = core_busy || m_axis_tvalid;

    css_sf7_sequential_detector #(
        .TWIDDLE_I_FILE(TWIDDLE_I_FILE),
        .TWIDDLE_Q_FILE(TWIDDLE_Q_FILE)
    ) u_detector (
        .clk                       (aclk),
        .resetn                    (aresetn),
        .valid_in                  (input_transfer),
        .ready                     (core_ready),
        .iq_re                     (s_axis_tdata[15:0]),
        .iq_im                     (s_axis_tdata[31:16]),
        .busy                      (core_busy),
        .done                      (core_done),
        .peak_bin                  (peak_bin),
        .second_bin                (second_bin),
        .peak_magnitude_squared    (peak_magnitude_squared),
        .second_magnitude_squared (second_magnitude_squared),
        .dechirp_overflow_count    (dechirp_overflow_count)
    );

    always @(posedge aclk) begin
        if (!aresetn) begin
            input_beat_index <= 7'd0;
            input_frame_error <= 1'b0;
            m_axis_tvalid <= 1'b0;
            m_axis_tdata <= 256'd0;
        end else begin
            if (output_transfer)
                m_axis_tvalid <= 1'b0;

            if (input_transfer) begin
                if (input_beat_index == 7'd0)
                    input_frame_error <= (s_axis_tlast != expected_tlast);
                else if (s_axis_tlast != expected_tlast)
                    input_frame_error <= 1'b1;

                if (expected_tlast)
                    input_beat_index <= 7'd0;
                else
                    input_beat_index <= input_beat_index + 1'b1;
            end

            if (core_done) begin
                m_axis_tvalid <= 1'b1;
                m_axis_tdata <= {
                    96'd0,
                    second_magnitude_squared,
                    peak_magnitude_squared,
                    dechirp_overflow_count,
                    input_frame_error,
                    second_bin,
                    1'b0,
                    peak_bin
                };
            end
        end
    end

endmodule
