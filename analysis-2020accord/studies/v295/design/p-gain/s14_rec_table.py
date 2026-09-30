# -*- coding: utf-8 -*-
"""s14_rec_table.py -- the recommendation's delivered surface at the r71b operating points (golden-model march):
T_V294, T_rec, static ratio, local slope (T per wire count), Kp(idx), trim gain K_alpha(idx) = 0.210 * Kp/960 below the
2 Hz pole, the trim cap C*Kp/256 through the chain, and the largest static torque increase.  ANALYSIS ONLY."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pg_lib as G
H = G.H
from s8_finalists import finalists
base, F = finalists()
rec = F[0]
S0, S1 = G.surface_table(base), G.surface_table(rec)
kp = H.lerp_table(rec.kp_x, rec.kp_y, 241)
print("rec", rec.name, rec.kp_x, rec.kp_y)
print("idx  wire   T_V294  T_rec  ratio  slope_V294  slope_rec (T/wire)  ratio  Kp   K_alpha(T per deg/s^2)  trim cap T")
for i in (1, 3, 6, 8, 10, 14, 18, 25, 34, 43, 50, 57, 65, 75, 92, 100, 120, 150, 184, 200, 238, 240):
    s0, s1 = G.local_slope(base, i), G.local_slope(rec, i)
    cap = round(rec.fb_clamp * kp[i] / 256 * 254 / 256 * 0.990234 * rec.gain / 32768)
    print("%3d %5.0f  %6.0f %6.0f  %5.3f   %.3f       %.3f              %.2f  %4d   %.3f   %d" % (
        i, i * H.WIRE_PER_IDX, S0[i], S1[i], S1[i] / S0[i] if S0[i] else np.nan, s0, s1, s1 / s0, kp[i], 0.210 * kp[i] / 960, cap))
d = S1 - S0
print("largest static increase: +%d T at idx %d (wire %.0f); rail both %d/%d; first rail idx V294 %d rec %d" % (
    d.max(), d.argmax(), d.argmax() * H.WIRE_PER_IDX, S0.max(), S1.max(), np.argmax(S0 >= S0.max()), np.argmax(S1 >= S1.max())))
print("relay torque: 45 wire counts -> idx %d -> T V294 %d, rec %d" % (int(45 / H.WIRE_PER_IDX + 0.5), S0[int(45 / H.WIRE_PER_IDX + 0.5)], S1[int(45 / H.WIRE_PER_IDX + 0.5)]))
