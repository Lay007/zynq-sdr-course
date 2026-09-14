`timescale 1ns/1ps

// Block 8 OFDM RX RTL: split one natural-order 64-bin FFT frame into
// 48 data carriers, four pilots and discarded DC/guard carriers.
//
// The carrier plan is the exact inverse of ofdm_subcarrier_allocator:
//   used  = -26..-1, +1..+26
//   pilot = -21, -7, +7, +21
//   data  = the remaining 48 used carriers.
//
// data_index follows the Lab 8.5/Python data_k order (negative frequencies
// first, then positive frequencies), even though bins arrive in natural FFT
// order. pilot_slot follows pilot_ref = [-21, -7, +7, +21].
//
// Data and pilot sinks are independently backpressured. Null carriers are
// consumed immediately. The upstream FFT therefore cannot lose a carrier when
// either selected downstream path stalls.
module ofdm_subcarrier_extractor (
    input  wire                resetn,

    input  wire                bin_valid,
    output wire                bin_ready,
    input  wire signed [15:0]  bin_re,
    input  wire signed [15:0]  bin_im,
    input  wire [5:0]          bin_index,
    input  wire                bin_last,

    output wire                data_valid,
    input  wire                data_ready,
    output wire signed [15:0]  data_re,
    output wire signed [15:0]  data_im,
    output wire [5:0]          data_bin_index,
    output wire [5:0]          data_index,
    output wire                data_last,

    output wire                pilot_valid,
    input  wire                pilot_ready,
    output wire signed [15:0]  pilot_re,
    output wire signed [15:0]  pilot_im,
    output wire [5:0]          pilot_bin_index,
    output wire [1:0]          pilot_slot,
    output wire signed [15:0]  pilot_ref_re
);

    wire is_pilot = (bin_index == 6'd43) || // k = -21
                    (bin_index == 6'd57) || // k = -7
                    (bin_index == 6'd7)  || // k = +7
                    (bin_index == 6'd21);   // k = +21

    wire is_null = (bin_index == 6'd0) ||
                   ((bin_index >= 6'd27) && (bin_index <= 6'd37));
    wire is_data = !is_pilot && !is_null;

    function automatic [5:0] data_index_for_bin;
        input [5:0] natural_bin;
        begin
            if ((natural_bin >= 6'd1) && (natural_bin <= 6'd6))
                data_index_for_bin = natural_bin + 6'd23;
            else if ((natural_bin >= 6'd8) && (natural_bin <= 6'd20))
                data_index_for_bin = natural_bin + 6'd22;
            else if ((natural_bin >= 6'd22) && (natural_bin <= 6'd26))
                data_index_for_bin = natural_bin + 6'd21;
            else if ((natural_bin >= 6'd38) && (natural_bin <= 6'd42))
                data_index_for_bin = natural_bin - 6'd38;
            else if ((natural_bin >= 6'd44) && (natural_bin <= 6'd56))
                data_index_for_bin = natural_bin - 6'd39;
            else
                data_index_for_bin = natural_bin - 6'd40;
        end
    endfunction

    function automatic [1:0] pilot_slot_for_bin;
        input [5:0] natural_bin;
        begin
            case (natural_bin)
                6'd43: pilot_slot_for_bin = 2'd0;
                6'd57: pilot_slot_for_bin = 2'd1;
                6'd7:  pilot_slot_for_bin = 2'd2;
                default: pilot_slot_for_bin = 2'd3;
            endcase
        end
    endfunction

    assign bin_ready = resetn &&
                       (is_data ? data_ready :
                        (is_pilot ? pilot_ready : 1'b1));

    assign data_valid = resetn && bin_valid && is_data;
    assign data_re = bin_re;
    assign data_im = bin_im;
    assign data_bin_index = bin_index;
    assign data_index = data_index_for_bin(bin_index);
    assign data_last = data_valid && bin_last;

    assign pilot_valid = resetn && bin_valid && is_pilot;
    assign pilot_re = bin_re;
    assign pilot_im = bin_im;
    assign pilot_bin_index = bin_index;
    assign pilot_slot = pilot_slot_for_bin(bin_index);
    assign pilot_ref_re = (bin_index == 6'd21) ? 16'sh8000 : 16'sd32767;

endmodule
