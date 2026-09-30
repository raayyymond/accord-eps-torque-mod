# -*- coding: utf-8 -*-
"""a11 -- (d) nonlinear traps, from the arithmetic and from an open-loop byte-exact march of r71b (recorded 0xE4 + 1 kHz x):
  D2 P clamp binding (V294 vs candidate), fb clamp C binding, max |T|;
  D3 per-frame torque step at the Honda slew cap (123 counts/frame) over every idx (the idx-100 kink included);
  restart pulse after a bail (|x| > 12000) at 10/30/100/300 deg/s, wheel held (lane only);
  the arithmetic bound: where can |E|*Kp(idx) >> 8 reach 15360 at all (E <= 4*map(idx) + C)."""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness")
import adv_lib as A  # noqa: E402
import adv_sim as SIM  # noqa: E402
import v295_harness as H  # noqa: E402

out = open(os.path.join(HERE, "a11_traps_out.txt"), "w")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    out.write(s + "\n")


b294, _ = A.load(A.IMG_V294, A.SHA_V294)
C294 = A.cells(b294)
CC = A.cells(A.write_candidate(b294))
map_t = A.table(C294["map_x"], C294["map_y"])
for nm, c in (("V294", C294), ("cand", CC)):
    kt = A.table(c["kp_x"], c["kp_y"])
    reach = [i for i in range(241) if ((4 * int(map_t[i]) + c["fb_clamp"]) * int(kt[i])) >> 8 >= c["p_clamp"]]
    P("%s: P clamp reachable (|E| <= 4*map + C) only at idx >= %s ; at r26 = 0 from idx %s" % (
        nm, reach[0] if reach else None, next((i for i in range(241) if ((4 * int(map_t[i])) * int(kt[i])) >> 8 >= c["p_clamp"]), None)))

# D3: per-frame torque step at the slew cap, every idx (static surface difference over 123 wire counts ~ 7.6 idx)
sf = np.load(os.path.join(HERE, "a1_surface.npz"))
S294, Sc = sf["S294"].astype(float), sf["Sc"].astype(float)
w = np.arange(0, 3870, 1)
idx_of = lambda wire: np.minimum(np.abs(((65025 * (-4 * wire)) >> 16) >> 6), 240)  # noqa: E731
st294 = np.abs(S294[idx_of(w + 123)] - S294[idx_of(w)])
stc = np.abs(Sc[idx_of(w + 123)] - Sc[idx_of(w)])
P("D3 static torque change over one max-slew frame (123 wire counts): V294 max %.0f T (at wire %d) ; cand max %.0f T (at wire %d) ; ratio of maxima %.2f ; across the idx-100 kink (wire 1500-1700): V294 %.0f cand %.0f" % (
    st294.max(), int(w[np.argmax(st294)]), stc.max(), int(w[np.argmax(stc)]), stc.max() / st294.max(),
    st294[1500:1700].max(), stc[1500:1700].max()))
# local slope (per idx) around the kink, exact
d294 = np.diff(S294)
dc = np.diff(Sc)
P("   exact per-idx surface increments near idx 100 (V294 / cand): %s" % [(i, int(d294[i]), int(dc[i])) for i in range(94, 106)])

# restart pulse: lane only, x jumps above 12000 (bail) then back to a held rate
for nm, c in (("V294", C294), ("cand", CC)):
    row = []
    for dps in (10.0, 30.0, 100.0, 300.0):
        L = A.MyLane(c)
        idx, sp = L.demand(0)
        x = int(round(8 * dps))
        for _ in range(3000):
            L.tick(x, sp, idx)
        L.tick(12001, sp, idx)
        Ts = []
        for _ in range(600):
            T, _ = L.tick(x, sp, idx)
            Ts.append(T)
        Ts = np.abs(np.array(Ts))
        row.append("%3.0f deg/s: peak %d T, >50 T for %d ms" % (dps, Ts.max(), int(np.sum(Ts > 50))))
    P("restart pulse %s (idx 0, the strongest Kp): %s" % (nm, " ; ".join(row)))

# open-loop march of r71b (hands-off engaged + all engaged)
d = H.route()
x1k = np.clip(np.round(d["x1k"]), -12000, 12000).astype(np.int64)
e4 = np.round(d["e4_f"]).astype(np.int64)
eng = d["eng"].astype(bool)
ho = d["ho"].astype(bool)
L = SIM.VLane([C294, CC])
nF = len(e4)
pcl = np.zeros((2, nF), bool)
ccl = np.zeros((2, nF), bool)
Tm = np.zeros((2, nF))
for k in range(nF):
    idx, sp = L.demand(np.array([e4[k], e4[k]]))
    for t in range(10):
        n = k * 10 + t
        if n >= len(x1k):
            break
        T, Pv, r26 = L.tick(np.array([x1k[n], x1k[n]]), sp, idx)
        pcl[:, k] |= np.abs(Pv) >= 15360
        ccl[:, k] |= np.abs(r26) >= 1024
        Tm[:, k] = np.maximum(Tm[:, k], np.abs(T))
for nm, j in (("V294", 0), ("cand", 1)):
    P("r71b open-loop march %s (hands-off engaged frames %d): P clamp on %d frames (%.4f %%), fb clamp on %d, max |T| %.0f ; all engaged: P clamp %d, max |T| %.0f" % (
        nm, int((eng & ho).sum()), int((pcl[j] & eng & ho).sum()), 100.0 * (pcl[j] & eng & ho).sum() / max((eng & ho).sum(), 1),
        int((ccl[j] & eng & ho).sum()), Tm[j][eng & ho].max(), int((pcl[j] & eng).sum()), Tm[j][eng].max()))
out.close()
