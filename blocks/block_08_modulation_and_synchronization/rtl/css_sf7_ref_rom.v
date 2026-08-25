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
//
// A pure lookup function plus continuous assignments are used instead of an
// always @* case so address 0 is deterministic even when the address is already
// zero at simulation start and never transitions before the first accepted IQ.
module css_sf7_ref_rom (
    input  wire [6:0]              addr,
    output wire signed [15:0]      ref_re,
    output wire signed [15:0]      ref_im
);

    function [31:0] coeff;
        input [6:0] a;
        begin
            case (a)
                7'd0: coeff = 32'h7fff0000;
                7'd1: coeff = 32'h800bfcdc;
                7'd2: coeff = 32'h7f610c8c;
                7'd3: coeff = 32'h831de3f5;
                7'd4: coeff = 32'h764130fb;
                7'd5: coeff = 32'h975ab64c;
                7'd6: coeff = 32'h513362f1;
                7'd7: coeff = 32'hd1ef8895;
                7'd8: coeff = 32'h00007fff;
                7'd9: coeff = 32'h33df8afc;
                7'd10: coeff = 32'h9d0f5133;
                7'd11: coeff = 32'h7e1dea1e;
                7'd12: coeff = 32'h89bfcf05;
                7'd13: coeff = 32'h447a6c23;
                7'd14: coeff = 32'h0c8c809f;
                7'd15: coeff = 32'ha34d5842;
                7'd16: coeff = 32'h7fff0000;
                7'd17: coeff = 32'ha7bea34d;
                7'd18: coeff = 32'hf3747f61;
                7'd19: coeff = 32'h6c23bb86;
                7'd20: coeff = 32'h89bfcf05;
                7'd21: coeff = 32'h15e27e1d;
                7'd22: coeff = 32'h62f1aecd;
                7'd23: coeff = 32'h8afccc21;
                7'd24: coeff = 32'h00007fff;
                7'd25: coeff = 32'h776bd1ef;
                7'd26: coeff = 32'haecd9d0f;
                7'd27: coeff = 32'hb64c68a6;
                7'd28: coeff = 32'h764130fb;
                7'd29: coeff = 32'h1c0b831d;
                7'd30: coeff = 32'h809ff374;
                7'd31: coeff = 32'hfcdc7ff5;
                7'd32: coeff = 32'h7fff0000;
                7'd33: coeff = 32'h0324800b;
                7'd34: coeff = 32'h809ff374;
                7'd35: coeff = 32'he3f57ce3;
                7'd36: coeff = 32'h764130fb;
                7'd37: coeff = 32'h49b4975a;
                7'd38: coeff = 32'haecd9d0f;
                7'd39: coeff = 32'h88952e11;
                7'd40: coeff = 32'h00007fff;
                7'd41: coeff = 32'h750433df;
                7'd42: coeff = 32'h62f1aecd;
                7'd43: coeff = 32'hea1e81e3;
                7'd44: coeff = 32'h89bfcf05;
                7'd45: coeff = 32'h93dd447a;
                7'd46: coeff = 32'hf3747f61;
                7'd47: coeff = 32'h58425cb3;
                7'd48: coeff = 32'h7fff0000;
                7'd49: coeff = 32'h5cb3a7be;
                7'd50: coeff = 32'h0c8c809f;
                7'd51: coeff = 32'hbb8693dd;
                7'd52: coeff = 32'h89bfcf05;
                7'd53: coeff = 32'h81e315e2;
                7'd54: coeff = 32'h9d0f5133;
                7'd55: coeff = 32'hcc217504;
                7'd56: coeff = 32'h00007fff;
                7'd57: coeff = 32'h2e11776b;
                7'd58: coeff = 32'h513362f1;
                7'd59: coeff = 32'h68a649b4;
                7'd60: coeff = 32'h764130fb;
                7'd61: coeff = 32'h7ce31c0b;
                7'd62: coeff = 32'h7f610c8c;
                7'd63: coeff = 32'h7ff50324;
                7'd64: coeff = 32'h7fff0000;
                7'd65: coeff = 32'h7ff50324;
                7'd66: coeff = 32'h7f610c8c;
                7'd67: coeff = 32'h7ce31c0b;
                7'd68: coeff = 32'h764130fb;
                7'd69: coeff = 32'h68a649b4;
                7'd70: coeff = 32'h513362f1;
                7'd71: coeff = 32'h2e11776b;
                7'd72: coeff = 32'h00007fff;
                7'd73: coeff = 32'hcc217504;
                7'd74: coeff = 32'h9d0f5133;
                7'd75: coeff = 32'h81e315e2;
                7'd76: coeff = 32'h89bfcf05;
                7'd77: coeff = 32'hbb8693dd;
                7'd78: coeff = 32'h0c8c809f;
                7'd79: coeff = 32'h5cb3a7be;
                7'd80: coeff = 32'h7fff0000;
                7'd81: coeff = 32'h58425cb3;
                7'd82: coeff = 32'hf3747f61;
                7'd83: coeff = 32'h93dd447a;
                7'd84: coeff = 32'h89bfcf05;
                7'd85: coeff = 32'hea1e81e3;
                7'd86: coeff = 32'h62f1aecd;
                7'd87: coeff = 32'h750433df;
                7'd88: coeff = 32'h00007fff;
                7'd89: coeff = 32'h88952e11;
                7'd90: coeff = 32'haecd9d0f;
                7'd91: coeff = 32'h49b4975a;
                7'd92: coeff = 32'h764130fb;
                7'd93: coeff = 32'he3f57ce3;
                7'd94: coeff = 32'h809ff374;
                7'd95: coeff = 32'h0324800b;
                7'd96: coeff = 32'h7fff0000;
                7'd97: coeff = 32'hfcdc7ff5;
                7'd98: coeff = 32'h809ff374;
                7'd99: coeff = 32'h1c0b831d;
                7'd100: coeff = 32'h764130fb;
                7'd101: coeff = 32'hb64c68a6;
                7'd102: coeff = 32'haecd9d0f;
                7'd103: coeff = 32'h776bd1ef;
                7'd104: coeff = 32'h00007fff;
                7'd105: coeff = 32'h8afccc21;
                7'd106: coeff = 32'h62f1aecd;
                7'd107: coeff = 32'h15e27e1d;
                7'd108: coeff = 32'h89bfcf05;
                7'd109: coeff = 32'h6c23bb86;
                7'd110: coeff = 32'hf3747f61;
                7'd111: coeff = 32'ha7bea34d;
                7'd112: coeff = 32'h7fff0000;
                7'd113: coeff = 32'ha34d5842;
                7'd114: coeff = 32'h0c8c809f;
                7'd115: coeff = 32'h447a6c23;
                7'd116: coeff = 32'h89bfcf05;
                7'd117: coeff = 32'h7e1dea1e;
                7'd118: coeff = 32'h9d0f5133;
                7'd119: coeff = 32'h33df8afc;
                7'd120: coeff = 32'h00007fff;
                7'd121: coeff = 32'hd1ef8895;
                7'd122: coeff = 32'h513362f1;
                7'd123: coeff = 32'h975ab64c;
                7'd124: coeff = 32'h764130fb;
                7'd125: coeff = 32'h831de3f5;
                7'd126: coeff = 32'h7f610c8c;
                7'd127: coeff = 32'h800bfcdc;
                default: coeff = 32'h00000000;
            endcase
        end
    endfunction

    wire [31:0] packed_coeff = coeff(addr);
    assign ref_re = packed_coeff[31:16];
    assign ref_im = packed_coeff[15:0];

endmodule
