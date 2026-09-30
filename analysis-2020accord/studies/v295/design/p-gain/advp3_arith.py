"""ADV-bytes (p-gain) step 3: arithmetic from the adversary's own lane (advp_lane) AND the golden model (second method).
Delivered surface at 241 idx (fb 0 and fb +-C), monotonicity, rail, first-rail idx, largest increase, int32 extremes,
zero-command torque, restart pulse."""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "model"))
import advp_lane as AL
import eps_lkas_chain_model as M
from dataclasses import replace

X294, Y294 = (0, 68, 112, 136, 208), (960,) * 5
XC, YC = (0, 8, 54, 100, 208), (1248, 1248, 1104, 960, 960)
k294, kc = AL.kp_table(X294, Y294), AL.kp_table(XC, YC)
# ---- Kp by idx, own LERP vs golden
g = [M.lkas_rate_lerp(list(XC), list(YC), i) for i in range(241)]
mm = [i for i in range(241) if g[i] != kc[i]]
print("Kp LERP own-listing vs golden, 241 idx: mismatches", mm)
print("Kp range over idx 0..255:", min(kc), max(kc), " monotone non-increasing:", all(kc[i + 1] <= kc[i] for i in range(255)))
print("Kp at idx 0,3,6,8,9,18,34,50,54,55,75,92,99,100,101,208,240:", [kc[i] for i in (0, 3, 6, 8, 9, 18, 34, 50, 54, 55, 75, 92, 99, 100, 101, 208, 240)])
# the X4 boundary is 208 (unchanged) and idx clamp 240: Kp for 208..240 is Y4 = 960
# ---- surface, own march vs golden surface, fb = 0 and +-1024
cal0 = M.Calibration()
def gcal(X, Y):
    return replace(cal0, fb_clamp=1024, fb_lag_a=1011, fb_lag_b=567, fb_op="diff", e_shift=2, kp_x=tuple(X), kp_y=tuple(Y),
                   kd_x=(0, 11, 22, 32), kd_y=(0, 0, 0, 0), pid_d_clamp=0, pid_ki=0, pid_err_deadband=4, pid_i_clamp=10240,
                   pid_p_clamp=15360, sum_clamp=15360, out_lag_a=992, out_lag_b=507, lkas_forward_gain=5346, out_clamp=3072,
                   assist_map_x=AL.MAP_X, assist_map_y=AL.MAP_Y)
res = {}
for nm, (X, Y), kt in (("V294", (X294, Y294), k294), ("CAND", (XC, YC), kc)):
    cal = gcal(X, Y)
    for fb in (0, 1024, -1024):
        own = [AL.surface(kt, i, r26=fb)[0] for i in range(241)]
        gold = [M.lkas_rate_pid_surface(i, cal, fb=fb, taper=254)["T"] for i in range(241)]
        res[(nm, fb)] = own
        mis = [i for i in range(241) if own[i] != gold[i]]
        print(f"{nm} fb {fb:+5d}: own vs golden surface mismatches {len(mis)} {mis[:5]}; T(0) {own[0]} T(240) {own[240]} max {max(own)} min {min(own)}")
s294, sc = res[("V294", 0)], res[("CAND", 0)]
nonmono = [i for i in range(240) if sc[i + 1] < sc[i]]
print("CAND fb0 non-monotone steps:", nonmono)
print("V294 fb0 non-monotone steps:", [i for i in range(240) if s294[i + 1] < s294[i]])
rail_c = min(i for i in range(241) if sc[i] == max(sc)); rail_v = min(i for i in range(241) if s294[i] == max(s294))
print("rail: V294 %d first at idx %d ; CAND %d first at idx %d" % (max(s294), rail_v, max(sc), rail_c))
d = [sc[i] - s294[i] for i in range(241)]
print("largest static increase %+d T at idx %d ; any change at idx >= 100: %s" % (max(d), d.index(max(d)), [i for i in range(100, 241) if d[i] != 0]))
print("negative-side rail (sgn -1): own surface with sp negative:")
# negative side: sp = -map; mirror by marching with sgn -1 at the surface: use AL.march on a constant frame
for nm, kt in (("V294", k294), ("CAND", kc)):
    T = AL.march([-1] * 300, [240] * 300, [254] * 300, kt, trim=False)
    print("   %s idx 240 sgn -1: T %d" % (nm, T[-1]))
# local slope ratio (T per idx) CAND/V294, idx 2..150
sl = [((sc[i + 1] - sc[i - 1]) / max(s294[i + 1] - s294[i - 1], 1)) for i in range(2, 151)]
print("local slope ratio idx 2..150: min %.3f at idx %d, max %.3f" % (min(sl), 2 + sl.index(min(sl)), max(sl)))
print("static ratio at idx 3,6,18,34,50,75,92: ", [round(sc[i] / s294[i], 3) for i in (3, 6, 18, 34, 50, 75, 92)])
# trim cap / zero-command torque
for nm, kt in (("V294", k294), ("CAND", kc)):
    print("  %s zero-command (idx 0) with r26 = -1024 / +1024: T %d / %d" % (nm, AL.surface(kt, 0, r26=-1024)[0], AL.surface(kt, 0, r26=1024)[0]))
# ---- int32 extremes over every reachable (idx, r26) at the candidate
worstEK = max(abs(((AL.MAP_T[i] << 2) + 1024) * kc[i]) for i in range(241))
print("max |E*Kp| over idx (|E| <= 4*sp+1024): %d  margin %.1f ; V294 %d" % (worstEK, 2 ** 31 / worstEK, max(((AL.MAP_T[i] << 2) + 1024) * 960 for i in range(241))))
num = max(abs((YC[k] - YC[k - 1]) * (XC[k] - XC[k - 1])) for k in range(1, 5))
print("max |LERP numerator| %d" % num)
Lmax = 15360 * 507 / 32.0
print("output lag state bound |L| <= %.0f ; |la*L| <= %.3g ; |S*lb| <= %.3g ; y <= %.0f (sxh 32767) ; y*gain <= %.3g" % (Lmax, 992 * Lmax, 15360 * 507, Lmax / 16, Lmax / 16 * 5346))
# ---- restart pulse: after a bail the next tick restarts s from 0 with x constant (wheel moving at R deg/s)
def restart(kt, idx, R):
    x = int(8 * R)
    s, L, peak, n50 = 0, 0, 0, 0
    Ts = []
    for i in range(3000):
        sn = ((1011 * s) >> 10) + ((567 * x) >> 10)
        r26 = max(-1024, min(1024, sn - s)); s = sn
        E = (AL.MAP_T[idx] << 2) - r26
        P = max(-15360, min(15360, (E * kt[idx]) >> 8))
        S = max(-15360, min(15360, (254 * P) >> 8))
        L2 = ((992 * L) >> 10) + ((S * 507) >> 10); y = (L + L2) >> 5; L = L2
        T = max(-3072, min(3072, (y * 5346) >> 15))
        Ts.append(T)
    T0 = Ts[-1]
    dev = [abs(t - T0) for t in Ts]
    return max(dev), sum(1 for v in dev if v > 50)
for nm, kt in (("V294", k294), ("CAND", kc)):
    print("  restart pulse %s idx 0: " % nm, [restart(kt, 0, R) for R in (10, 30, 100, 300)], " (peak |dT|, ms > 50 T)")
json.dump({"surf_v294": s294, "surf_cand": sc, "kp_cand": kc[:241]}, open(os.path.join(HERE, "out", "advp3_arith.json"), "w"))
