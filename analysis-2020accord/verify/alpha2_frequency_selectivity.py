# -*- coding: utf-8 -*-
"""alpha2 (0xC40DC) frequency selectivity: the gp-0x6b26 lane is |1-z^-1| * |H_ema(alpha2/64)|.

EMA-A in FUN_00041464 is  state += (diff * alpha2) >> 6  => alpha = alpha2/64, and its input is a
FIRST DIFFERENCE (0x41602 sub r7,r9), so the lane is a differentiator whose response RISES with
frequency. Lowering alpha2 therefore cuts HIGH bands far more than low ones.
"""
import numpy as np
fs = 1000.0
lane = lambda a2, f: abs(1 - np.exp(-1j * 2 * np.pi * f / fs)) * abs(
    (a2 / 64.0) / (1 - (1 - a2 / 64.0) * np.exp(-1j * 2 * np.pi * f / fs)))
print("   freq       a2=22      a2=14      a2=8      8/14     what lives there")
for f, lbl in ((3, 'LKAS command band -- UNTOUCHED'), (7.8, 'oscillation / damper'),
               (21, 'grind #1 lower'), (23.4, 'GRIND #1 PEAK'), (26, 'grind #1 upper'), (50, '')):
    a, b, c = lane(22, f), lane(14, f), lane(8, f)
    print("   %5.1f Hz  %.6f   %.6f   %.6f  %.3fx   %s" % (f, a, b, c, c / b, lbl))
r78 = lane(8, 7.8) / lane(14, 7.8)
r23 = lane(8, 23.4) / lane(14, 23.4)
print("\n   damper %+.1f %%   grind #1 %+.1f %%   SELECTIVITY %.2fx"
      % (100 * (r78 - 1), 100 * (r23 - 1), (1 - r23) / (1 - r78)))
print("   V94 cut this same lane to 0.167x and the operator ABORTED; 14->8 is 1/20th of that.")
