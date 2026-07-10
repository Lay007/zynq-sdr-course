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
// So write on the vendor strobe unconditionally and mux only the DATA. During the burst the
// modem shares the same sample clock and produces one sample per strobe, so its samples ride
// the vendor cadence 1:1; on the pipeline edges it contributes silence, which is what the
// air should carry there anyway.

module course_dac_fifo_source_mux #(
    parameter integer W = 16
) (
    input  wire               select_bpsk,
    input  wire [15:0]        vendor_data_0,
    input  wire [15:0]        vendor_data_1,
    input  wire [15:0]        vendor_data_2,
    input  wire [15:0]        vendor_data_3,
    input  wire               vendor_valid,
    input  wire               vendor_unf,
    input  wire [(2*W):0]     bpsk_tx_sample_bus,
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

// Modem sample when the burst is streaming, silence on its pipeline edges.
wire        take_bpsk = select_bpsk;
wire [15:0] burst_i   = bpsk_valid ? bpsk_i[15:0] : 16'sd0;
wire [15:0] burst_q   = bpsk_valid ? bpsk_q[15:0] : 16'sd0;

// Broadcast the modem burst on BOTH TX channels (TX1 = data_0/1, TX2 = data_2/3)
// so the frame is available on the TX2 SMA too — lets the host test a TX2->RX2
// cable path (in case the TX1/RX1 channel/balun is degraded) without a re-route.
assign fifo_data_0 = take_bpsk ? burst_i : vendor_data_0;
assign fifo_data_1 = take_bpsk ? burst_q : vendor_data_1;
assign fifo_data_2 = take_bpsk ? burst_i : vendor_data_2;
assign fifo_data_3 = take_bpsk ? burst_q : vendor_data_3;

// Cadence follows the vendor strobe, so the FIFO sees the same number of writes per DAC read
// whether or not the modem is transmitting: its occupancy -- and therefore our burst's
// latency to the antenna -- stops depending on how many bursts have gone before.
//
// The `| bpsk_valid` term is deliberate belt-and-braces. If the vendor stream is running
// (a cyclic DMA buffer, which every course script starts) `vendor_valid` is the continuous
// per-sample strobe and the OR changes nothing -- the cadence is rigid, which is the fix. If
// the vendor stream were ever stopped, `vendor_valid` would be dead and this degrades to the
// old `bpsk_valid` behaviour rather than silencing the transmitter outright.
assign fifo_valid  = take_bpsk ? (vendor_valid | bpsk_valid) : vendor_valid;
assign fifo_unf    = take_bpsk ? 1'b0 : vendor_unf;

endmodule
