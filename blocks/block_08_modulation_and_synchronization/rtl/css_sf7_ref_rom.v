`timescale 1ns/1ps

// Block 8 CSS accelerator: SF7 reference upchirp ROM.
//
// The 128 complex coefficients are the Q1.15 quantization of the exact
// Lab 8.20/Lab 8.21 baseband definition for SF=7 and Fs=BW:
//
//   phase_cycles[n] = 0.5*n*n/128 - 0.5*n
//   reference[n]    = exp(j*2*pi*phase_cycles[n])
//
// Quantization is round(32767*x) per component, so +1.0 maps to +32767.
// The ROM stores the ordinary upchirp. css_dechirp_mul performs conjugation.
module css_sf7_ref_rom (
    input  wire [6:0]              addr,
    output reg  signed [15:0]      ref_re,
    output reg  signed [15:0]      ref_im
);

    always @* begin
        case (addr)
            7'd0: begin ref_re = 16'sd32767; ref_im = 16'sd0; end
            7'd1: begin ref_re = -16'sd32757; ref_im = -16'sd804; end
            7'd2: begin ref_re = 16'sd32609; ref_im = 16'sd3212; end
            7'd3: begin ref_re = -16'sd31971; ref_im = -16'sd7179; end
            7'd4: begin ref_re = 16'sd30273; ref_im = 16'sd12539; end
            7'd5: begin ref_re = -16'sd26790; ref_im = -16'sd18868; end
            7'd6: begin ref_re = 16'sd20787; ref_im = 16'sd25329; end
            7'd7: begin ref_re = -16'sd11793; ref_im = -16'sd30571; end
            7'd8: begin ref_re = 16'sd0; ref_im = 16'sd32767; end
            7'd9: begin ref_re = 16'sd13279; ref_im = -16'sd29956; end
            7'd10: begin ref_re = -16'sd25329; ref_im = 16'sd20787; end
            7'd11: begin ref_re = 16'sd32285; ref_im = -16'sd5602; end
            7'd12: begin ref_re = -16'sd30273; ref_im = -16'sd12539; end
            7'd13: begin ref_re = 16'sd17530; ref_im = 16'sd27683; end
            7'd14: begin ref_re = 16'sd3212; ref_im = -16'sd32609; end
            7'd15: begin ref_re = -16'sd23731; ref_im = 16'sd22594; end
            7'd16: begin ref_re = 16'sd32767; ref_im = 16'sd0; end
            7'd17: begin ref_re = -16'sd22594; ref_im = -16'sd23731; end
            7'd18: begin ref_re = -16'sd3212; ref_im = 16'sd32609; end
            7'd19: begin ref_re = 16'sd27683; ref_im = -16'sd17530; end
            7'd20: begin ref_re = -16'sd30273; ref_im = -16'sd12539; end
            7'd21: begin ref_re = 16'sd5602; ref_im = 16'sd32285; end
            7'd22: begin ref_re = 16'sd25329; ref_im = -16'sd20787; end
            7'd23: begin ref_re = -16'sd29956; ref_im = -16'sd13279; end
            7'd24: begin ref_re = 16'sd0; ref_im = 16'sd32767; end
            7'd25: begin ref_re = 16'sd30571; ref_im = -16'sd11793; end
            7'd26: begin ref_re = -16'sd20787; ref_im = -16'sd25329; end
            7'd27: begin ref_re = -16'sd18868; ref_im = 16'sd26790; end
            7'd28: begin ref_re = 16'sd30273; ref_im = 16'sd12539; end
            7'd29: begin ref_re = 16'sd7179; ref_im = -16'sd31971; end
            7'd30: begin ref_re = -16'sd32609; ref_im = -16'sd3212; end
            7'd31: begin ref_re = -16'sd804; ref_im = 16'sd32757; end
            7'd32: begin ref_re = 16'sd32767; ref_im = 16'sd0; end
            7'd33: begin ref_re = 16'sd804; ref_im = -16'sd32757; end
            7'd34: begin ref_re = -16'sd32609; ref_im = -16'sd3212; end
            7'd35: begin ref_re = -16'sd7179; ref_im = 16'sd31971; end
            7'd36: begin ref_re = 16'sd30273; ref_im = 16'sd12539; end
            7'd37: begin ref_re = 16'sd18868; ref_im = -16'sd26790; end
            7'd38: begin ref_re = -16'sd20787; ref_im = -16'sd25329; end
            7'd39: begin ref_re = -16'sd30571; ref_im = 16'sd11793; end
            7'd40: begin ref_re = 16'sd0; ref_im = 16'sd32767; end
            7'd41: begin ref_re = 16'sd29956; ref_im = 16'sd13279; end
            7'd42: begin ref_re = 16'sd25329; ref_im = -16'sd20787; end
            7'd43: begin ref_re = -16'sd5602; ref_im = -16'sd32285; end
            7'd44: begin ref_re = -16'sd30273; ref_im = -16'sd12539; end
            7'd45: begin ref_re = -16'sd27683; ref_im = 16'sd17530; end
            7'd46: begin ref_re = -16'sd3212; ref_im = 16'sd32609; end
            7'd47: begin ref_re = 16'sd22594; ref_im = 16'sd23731; end
            7'd48: begin ref_re = 16'sd32767; ref_im = 16'sd0; end
            7'd49: begin ref_re = 16'sd23731; ref_im = -16'sd22594; end
            7'd50: begin ref_re = 16'sd3212; ref_im = -16'sd32609; end
            7'd51: begin ref_re = -16'sd17530; ref_im = -16'sd27683; end
            7'd52: begin ref_re = -16'sd30273; ref_im = -16'sd12539; end
            7'd53: begin ref_re = -16'sd32285; ref_im = 16'sd5602; end
            7'd54: begin ref_re = -16'sd25329; ref_im = 16'sd20787; end
            7'd55: begin ref_re = -16'sd13279; ref_im = 16'sd29956; end
            7'd56: begin ref_re = 16'sd0; ref_im = 16'sd32767; end
            7'd57: begin ref_re = 16'sd11793; ref_im = 16'sd30571; end
            7'd58: begin ref_re = 16'sd20787; ref_im = 16'sd25329; end
            7'd59: begin ref_re = 16'sd26790; ref_im = 16'sd18868; end
            7'd60: begin ref_re = 16'sd30273; ref_im = 16'sd12539; end
            7'd61: begin ref_re = 16'sd31971; ref_im = 16'sd7179; end
            7'd62: begin ref_re = 16'sd32609; ref_im = 16'sd3212; end
            7'd63: begin ref_re = 16'sd32757; ref_im = 16'sd804; end
            7'd64: begin ref_re = 16'sd32767; ref_im = 16'sd0; end
            7'd65: begin ref_re = 16'sd32757; ref_im = 16'sd804; end
            7'd66: begin ref_re = 16'sd32609; ref_im = 16'sd3212; end
            7'd67: begin ref_re = 16'sd31971; ref_im = 16'sd7179; end
            7'd68: begin ref_re = 16'sd30273; ref_im = 16'sd12539; end
            7'd69: begin ref_re = 16'sd26790; ref_im = 16'sd18868; end
            7'd70: begin ref_re = 16'sd20787; ref_im = 16'sd25329; end
            7'd71: begin ref_re = 16'sd11793; ref_im = 16'sd30571; end
            7'd72: begin ref_re = 16'sd0; ref_im = 16'sd32767; end
            7'd73: begin ref_re = -16'sd13279; ref_im = 16'sd29956; end
            7'd74: begin ref_re = -16'sd25329; ref_im = 16'sd20787; end
            7'd75: begin ref_re = -16'sd32285; ref_im = 16'sd5602; end
            7'd76: begin ref_re = -16'sd30273; ref_im = -16'sd12539; end
            7'd77: begin ref_re = -16'sd17530; ref_im = -16'sd27683; end
            7'd78: begin ref_re = 16'sd3212; ref_im = -16'sd32609; end
            7'd79: begin ref_re = 16'sd23731; ref_im = -16'sd22594; end
            7'd80: begin ref_re = 16'sd32767; ref_im = 16'sd0; end
            7'd81: begin ref_re = 16'sd22594; ref_im = 16'sd23731; end
            7'd82: begin ref_re = -16'sd3212; ref_im = 16'sd32609; end
            7'd83: begin ref_re = -16'sd27683; ref_im = 16'sd17530; end
            7'd84: begin ref_re = -16'sd30273; ref_im = -16'sd12539; end
            7'd85: begin ref_re = -16'sd5602; ref_im = -16'sd32285; end
            7'd86: begin ref_re = 16'sd25329; ref_im = -16'sd20787; end
            7'd87: begin ref_re = 16'sd29956; ref_im = 16'sd13279; end
            7'd88: begin ref_re = 16'sd0; ref_im = 16'sd32767; end
            7'd89: begin ref_re = -16'sd30571; ref_im = 16'sd11793; end
            7'd90: begin ref_re = -16'sd20787; ref_im = -16'sd25329; end
            7'd91: begin ref_re = 16'sd18868; ref_im = -16'sd26790; end
            7'd92: begin ref_re = 16'sd30273; ref_im = 16'sd12539; end
            7'd93: begin ref_re = -16'sd7179; ref_im = 16'sd31971; end
            7'd94: begin ref_re = -16'sd32609; ref_im = -16'sd3212; end
            7'd95: begin ref_re = 16'sd804; ref_im = -16'sd32757; end
            7'd96: begin ref_re = 16'sd32767; ref_im = 16'sd0; end
            7'd97: begin ref_re = -16'sd804; ref_im = 16'sd32757; end
            7'd98: begin ref_re = -16'sd32609; ref_im = -16'sd3212; end
            7'd99: begin ref_re = 16'sd7179; ref_im = -16'sd31971; end
            7'd100: begin ref_re = 16'sd30273; ref_im = 16'sd12539; end
            7'd101: begin ref_re = -16'sd18868; ref_im = 16'sd26790; end
            7'd102: begin ref_re = -16'sd20787; ref_im = -16'sd25329; end
            7'd103: begin ref_re = 16'sd30571; ref_im = -16'sd11793; end
            7'd104: begin ref_re = 16'sd0; ref_im = 16'sd32767; end
            7'd105: begin ref_re = -16'sd29956; ref_im = -16'sd13279; end
            7'd106: begin ref_re = 16'sd25329; ref_im = -16'sd20787; end
            7'd107: begin ref_re = 16'sd5602; ref_im = 16'sd32285; end
            7'd108: begin ref_re = -16'sd30273; ref_im = -16'sd12539; end
            7'd109: begin ref_re = 16'sd27683; ref_im = -16'sd17530; end
            7'd110: begin ref_re = -16'sd3212; ref_im = 16'sd32609; end
            7'd111: begin ref_re = -16'sd22594; ref_im = -16'sd23731; end
            7'd112: begin ref_re = 16'sd32767; ref_im = 16'sd0; end
            7'd113: begin ref_re = -16'sd23731; ref_im = 16'sd22594; end
            7'd114: begin ref_re = 16'sd3212; ref_im = -16'sd32609; end
            7'd115: begin ref_re = 16'sd17530; ref_im = 16'sd27683; end
            7'd116: begin ref_re = -16'sd30273; ref_im = -16'sd12539; end
            7'd117: begin ref_re = 16'sd32285; ref_im = -16'sd5602; end
            7'd118: begin ref_re = -16'sd25329; ref_im = 16'sd20787; end
            7'd119: begin ref_re = 16'sd13279; ref_im = -16'sd29956; end
            7'd120: begin ref_re = 16'sd0; ref_im = 16'sd32767; end
            7'd121: begin ref_re = -16'sd11793; ref_im = -16'sd30571; end
            7'd122: begin ref_re = 16'sd20787; ref_im = 16'sd25329; end
            7'd123: begin ref_re = -16'sd26790; ref_im = -16'sd18868; end
            7'd124: begin ref_re = 16'sd30273; ref_im = 16'sd12539; end
            7'd125: begin ref_re = -16'sd31971; ref_im = -16'sd7179; end
            7'd126: begin ref_re = 16'sd32609; ref_im = 16'sd3212; end
            7'd127: begin ref_re = -16'sd32757; ref_im = -16'sd804; end
            default: begin ref_re = 16'sd0; ref_im = 16'sd0; end
        endcase
    end

endmodule
