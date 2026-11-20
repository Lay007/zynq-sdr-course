| Mode | LUT | FF | DSP48E1 | BRAM tiles | WNS (ns) | WHS (ns) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| NCO table | 239 | 33 | 0 | 0 | +5.071 | −0.223 |
| NCO CORDIC | 233 | 118 | 0 | 0 | +3.701 | −0.266 |
| FFT one-clock butterfly, logic | 8986 | 2247 | 4 | 0 | −11.261 | −0.266 |
| FFT pipelined butterfly, logic | 7834 | 2387 | 4 | 0 | +0.748 | −0.266 |
| FFT pipelined butterfly, BRAM | 909 | 319 | 4 | 1 | +2.099 | −0.266 |

Vivado 2020.1 routed all five variants on `xc7z020clg400-2` with a 100 MHz target. Compared with the pipelined design that stores working points in logic, BRAM reduced LUT use from 7834 to 909 and added seven clocks per frame. The one-clock butterfly failed setup. All variants have negative hold slack under the idealized port delays. Clock distribution and port placement are defined in the integrated design, so these standalone runs leave full timing closure open.
