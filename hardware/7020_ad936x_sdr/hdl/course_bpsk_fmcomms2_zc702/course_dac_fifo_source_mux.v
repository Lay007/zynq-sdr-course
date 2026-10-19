// Selects what gets written into axi_ad9361_dac_fifo: the vendor DAC stream (DMA/DDS,
// unpacked by util_ad9361_dac_upack) or the course modem's burst.
//
// THE WRITE CADENCE MUST NOT DEPEND ON THE SELECTION. axi_ad9361_dac_fifo is a rate-crossing
// FIFO whose read side (the AD9361 DAC) drains continuously and never pauses. If the write
// strobe stops while the read side keeps going, the FIFO's occupancy shifts, and the
// occupancy is exactly the latency our burst sees on its way to the antenna.
//
// The modem's own `tx_valid` is low while its mapper -> upsampler -> RRC pipeline fills and
// again while it flushes, so muxing the VALID as well as the data cost the FIFO a fixed
// number of writes on every burst. Measured consequence: the frame arrival at the receiver
// was not jittery, it was a deterministic period-6 staircase over the burst index --
// arrivals 87, 89, 108, 86, 88, 101 repeating forever, walking the mod-8 sampler phases
// 7,1,4,6,0,5. The fixed-phase RX sampler then landed anywhere from dead centre (BER 0) to
// exactly between two symbols (no frame lock), and the on-chip BER followed the phase
// bit-for-bit. Re-arming the DDS/DAC `sync_start_enable` did not touch it; the staircase
// walked straight through the re-arm, because the state lives in this FIFO, not in the DDS.
//
// The cadence used to be the vendor stream's strobe (`vendor_valid`, the unpacker's answer).
// That was rigid only while a DMA buffer was running. With no vendor stream (board B, whose
// course image had no DAC driver; issue #67) the strobe was dead, the FIFO was written only
// during a burst, and between bursts the DAC kept playing the last word written: a carrier at
// the LO as strong as the burst. So the cadence now comes from the FIFO itself: its read
// request to the unpacker (`fifo_rd_req`, util_rfifo din_valid), delayed by the one clock the
// unpacker takes to answer (util_upack2 registers fifo_rd_valid). While a DMA buffer runs and
// keeps up, that is the same strobe as before, word for word. When the DMA has nothing (no
// stream, or an underflow), the request is still there and the FIFO gets zeros, or the modem's
// samples during a burst. The DAC then outputs silence between bursts by itself.
//
// A third source (issue #48): ofdm_radio_core's burst, select_ofdm / ofdm_tx_sample_bus, same bus
// format and the same cadence rule. The BPSK/QPSK bridge wins if both select at once. A build
// without the OFDM core ties select_ofdm and the bus to 0.

module course_dac_fifo_source_mux #(
    parameter integer W = 16
) (
    input  wire               clk,              // util_ad9361_divclk, the FIFO's write clock
    input  wire               fifo_rd_req,      // axi_ad9361_dac_fifo/din_valid_0
    input  wire               select_bpsk,
    input  wire [15:0]        vendor_data_0,
    input  wire [15:0]        vendor_data_1,
    input  wire [15:0]        vendor_data_2,
    input  wire [15:0]        vendor_data_3,
    input  wire               vendor_valid,
    input  wire               vendor_unf,
    input  wire [(2*W):0]     bpsk_tx_sample_bus,
    input  wire               select_ofdm,
    input  wire [(2*W):0]     ofdm_tx_sample_bus,
    output wire [15:0]        fifo_data_0,
    output wire [15:0]        fifo_data_1,
    output wire [15:0]        fifo_data_2,
    output wire [15:0]        fifo_data_3,
    output wire               fifo_valid,
    output wire               fifo_unf
);

wire               bpsk_valid;
wire signed [W-1:0] bpsk_i;
wire signed [W-1:0] bpsk_q;

assign bpsk_valid = bpsk_tx_sample_bus[2*W];
assign bpsk_i = bpsk_tx_sample_bus[(2*W)-1:W];
assign bpsk_q = bpsk_tx_sample_bus[W-1:0];

// The FIFO's request, aligned with the unpacker's answer to it.
reg req_d = 1'b0;
always @(posedge clk) req_d <= fifo_rd_req;

wire               ofdm_valid = ofdm_tx_sample_bus[2*W];
wire signed [W-1:0] ofdm_i = ofdm_tx_sample_bus[(2*W)-1:W];
wire signed [W-1:0] ofdm_q = ofdm_tx_sample_bus[W-1:0];

// Modem sample when the burst is streaming, silence on its pipeline edges.
wire        take_bpsk = select_bpsk;
wire        take_ofdm = !select_bpsk && select_ofdm;
wire        burst_valid = take_bpsk ? bpsk_valid : ofdm_valid;
wire [15:0] burst_i   = !burst_valid ? 16'sd0 : take_bpsk ? bpsk_i[15:0] : ofdm_i[15:0];
wire [15:0] burst_q   = !burst_valid ? 16'sd0 : take_bpsk ? bpsk_q[15:0] : ofdm_q[15:0];
wire        take_burst = take_bpsk || take_ofdm;

// Vendor words only when the unpacker actually delivered them; zeros otherwise.
wire [15:0] vend_0 = vendor_valid ? vendor_data_0 : 16'd0;
wire [15:0] vend_1 = vendor_valid ? vendor_data_1 : 16'd0;
wire [15:0] vend_2 = vendor_valid ? vendor_data_2 : 16'd0;
wire [15:0] vend_3 = vendor_valid ? vendor_data_3 : 16'd0;

// Broadcast the modem burst on BOTH TX channels (TX1 = data_0/1, TX2 = data_2/3)
// so the frame is available on the TX2 SMA too -- lets the host test a TX2->RX2
// cable path (in case the TX1/RX1 channel/balun is degraded) without a re-route.
assign fifo_data_0 = take_burst ? burst_i : vend_0;
assign fifo_data_1 = take_burst ? burst_q : vend_1;
assign fifo_data_2 = take_burst ? burst_i : vend_2;
assign fifo_data_3 = take_burst ? burst_q : vend_3;

// Cadence: the FIFO's own (delayed) request, plus the old strobes as belt and braces. With a
// running DMA, req_d and vendor_valid coincide; during a burst the modem rides the same cadence.
assign fifo_valid  = req_d | vendor_valid | (take_burst & burst_valid);
assign fifo_unf    = take_burst ? 1'b0 : vendor_unf;

endmodule
