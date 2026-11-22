// AD9361 CTRL_OUT asynchronous event capture. No assumptions about PCB pins.
// Counts sampled rising edges, not the duration of a threshold condition.
// A 2-FF synchronizer cannot guarantee capture of pulses shorter than clk period.
module ad9361_overload_monitor (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         clear,
    input  wire [7:0]   ctrl_out_async,
    output wire [7:0]   ctrl_out_sampled,
    output reg  [7:0]   sticky,
    output reg  [31:0]  ticks,
    output wire [255:0] event_counts,
    output wire [255:0] last_timestamps
);
    reg [7:0] sync_meta, sync_data, sync_prev;
    reg [31:0] counter [0:7];
    reg [31:0] last_tick [0:7];
    wire [7:0] rising = sync_data & ~sync_prev;
    integer i;

    assign ctrl_out_sampled = sync_data;
    genvar g;
    generate
        for (g = 0; g < 8; g = g + 1) begin : map_output
            assign event_counts[g*32 +: 32] = counter[g];
            assign last_timestamps[g*32 +: 32] = last_tick[g];
        end
    endgenerate

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sync_meta <= 8'b0;
            sync_data <= 8'b0;
            sync_prev <= 8'b0;
            sticky <= 8'b0;
            ticks <= 32'b0;
            for (i = 0; i < 8; i = i + 1) begin
                counter[i] <= 32'b0;
                last_tick[i] <= 32'b0;
            end
        end else begin
            sync_meta <= ctrl_out_async;
            sync_data <= sync_meta;
            sync_prev <= sync_data;
            ticks <= ticks + 1'b1;
            if (clear) begin
                sticky <= 8'b0;
                for (i = 0; i < 8; i = i + 1) begin
                    counter[i] <= 32'b0;
                    last_tick[i] <= 32'b0;
                end
            end else begin
                sticky <= sticky | rising;
                for (i = 0; i < 8; i = i + 1) begin
                    if (rising[i]) begin
                        if (counter[i] != 32'hFFFFFFFF)
                            counter[i] <= counter[i] + 1'b1;
                        last_tick[i] <= ticks;
                    end
                end
            end
        end
    end
endmodule
