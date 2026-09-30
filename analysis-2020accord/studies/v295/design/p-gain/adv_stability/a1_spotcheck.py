# -*- coding: utf-8 -*-
"""a1 -- reproduction gates R1-R3 with MY decoder / lane, and my lane vs the golden model tick for tick."""
import json
import os
import sys
from dataclasses import replace

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/model")
import adv_lib as A  # noqa: E402
import eps_lkas_chain_model as M  # noqa: E402

b294, h = A.load(A.IMG_V294, A.SHA_V294)
print("V294 sha OK", h[:12])
bc = A.write_candidate(b294)
diff = [a for a in range(0x13000, 0x100000) if b294[a] != bc[a]]
pages = sorted({a & ~0xFFF for a in diff})
print("candidate vs V294: %d bytes differ, pages %s, range 0x%X..0x%X" % (len(diff), [hex(p) for p in pages], diff[0], diff[-1]))
# compare with the designer's spec bytes (a report, the spec is theirs)
spec = json.load(open(os.path.join(HERE, "..", "out", "V295_p-gain_candidate_spec.json")))
bad = 0
for r in spec["records"]:
    rec = int(r["rec"], 16)
    mine = bytes(bc[rec:rec + 22]).hex()
    if mine != r["bytes_new"] and mine[4:] != r["bytes_new"]:
        # the spec's xy_block starts at rec+2 (20 bytes)
        if bytes(bc[rec + 2:rec + 22]).hex() != r["bytes_new"]:
            bad += 1
print("spec byte blocks vs my write: %d of %d records disagree" % (bad, len(spec["records"])))
# X knots per slot on V294 (report)
xs = {}
for slot in range(28):
    r, X, Y = A.record(b294, A.KP_BANK, slot)
    xs.setdefault(tuple(X), []).append(slot)
    assert all(y == 960 for y in Y)
print("V294 Kp X by slot:", {k: v for k, v in xs.items()})

c294 = A.cells(b294)
cc = A.cells(bc)
print("V294 cells:", {k: c294[k] for k in ("fb_a", "fb_b", "fb_clamp", "fb_op", "e_shift", "kp_x", "kp_y", "kd_y", "d_clamp",
                                             "ki", "p_clamp", "sum_clamp", "lag_a", "lag_b", "gain", "t_clamp", "idx_clamp")})
print("map X", c294["map_x"], "Y", c294["map_y"])
print("cand Kp slot7:", cc["kp_x"], cc["kp_y"])
b282, _ = A.load(A.IMG_V282)
c282 = A.cells(b282)
print("V282 cells:", {k: c282[k] for k in ("fb_a", "fb_b", "fb_clamp", "fb_op", "e_shift", "kp_x", "kp_y", "kd_x", "kd_y",
                                             "d_clamp", "ki", "p_clamp", "lag_a", "lag_b", "gain", "t_clamp")})

# ---- R1: Kp table at the designer's idx
kt = A.table(cc["kp_x"], cc["kp_y"])
want = {3: 1248, 6: 1248, 18: 1217, 34: 1167, 50: 1117, 75: 1039, 92: 986, 100: 960}
print("R1 Kp(idx) mine vs designer:", [(i, int(kt[i]), w) for i, w in want.items()],
      "PASS" if all(abs(int(kt[i]) - w) <= 1 for i, w in want.items()) else "FAIL")
gl = [M.lkas_rate_lerp(list(cc["kp_x"]), list(cc["kp_y"]), i) for i in range(256)]
print("  my LERP == golden lkas_rate_lerp on 0..255:", int(np.sum(np.array(gl) != kt)), "mismatches")

# ---- R3 surface
S294 = A.static_surface(c294)
Sc = A.static_surface(cc)
S294n = np.array([A.MyLane(c294) and 0 for _ in range(1)])
first294 = int(np.argmax(S294 >= S294.max()))
firstc = int(np.argmax(Sc >= Sc.max()))
print("R3 rail V294 %d first idx %d ; cand %d first idx %d" % (S294.max(), first294, Sc.max(), firstc))
tw = {3: (30, 40), 6: (61, 80), 18: (184, 233), 34: (350, 426), 50: (516, 600), 75: (773, 837), 92: (949, 974)}
print("  static T mine (V294 -> cand) vs designer:", [(i, int(S294[i]), int(Sc[i]), w) for i, w in tw.items()])
d = Sc - S294
print("  max static increase %+d at idx %d ; monotone cand: %s (min step %d) ; monotone V294 %s" % (
    d.max(), int(np.argmax(d)), bool(np.all(np.diff(Sc) >= 0)), int(np.diff(Sc).min()), bool(np.all(np.diff(S294) >= 0))))


def neg_surface(c):
    out = []
    for i in range(241):
        L = A.MyLane(c)
        sp = -int(L.map_t[i])
        T = 0
        for _ in range(4000):
            T, _ = L.tick(0, sp, i)
        out.append(T)
    return np.array(out)


N294, Nc = neg_surface(c294), neg_surface(cc)
print("  negative rail V294 %d cand %d" % (N294.min(), Nc.min()))
# local slope, exact per idx (difference) and +-8 central
ds = np.diff(Sc.astype(float)) / A.WIRE_PER_IDX
d294 = np.diff(S294.astype(float)) / A.WIRE_PER_IDX
print("  per-idx slope ratio cand/V294 (5-idx means): ", [(i, round(float(np.mean(ds[i:i + 5]) / np.mean(d294[i:i + 5])), 3))
                                                      for i in (0, 5, 10, 20, 40, 60, 80, 90, 95, 100, 120)])
np.savez(os.path.join(HERE, "a1_surface.npz"), S294=S294, Sc=Sc, N294=N294, Nc=Nc)

# ---- R2 |P/x| at 20 Hz
f = np.array([13.0, 16.0, 20.0, 25.0])
for nm, c, kp, kd in (("V294", c294, 960, 0), ("cand", cc, 1248, 0), ("V282", c282, c282["kp_y"][0], c282["kd_y"][0])):
    print("R2 |P/x| %s at %s Hz: %s" % (nm, f, np.round(A.P_per_x_mag(c, f, kp, kd), 3)))

# ---- lane vs golden model, tick for tick
def gcal(c):
    return replace(M.Calibration(), fb_clamp=c["fb_clamp"], fb_lag_a=c["fb_a"], fb_lag_b=c["fb_b"], fb_op=c["fb_op"],
                   e_shift=c["e_shift"], kp_x=tuple(c["kp_x"]), kp_y=tuple(c["kp_y"]), kd_x=tuple(c["kd_x"]),
                   kd_y=tuple(c["kd_y"]), pid_d_clamp=c["d_clamp"], pid_ki=c["ki"], pid_err_deadband=c["deadband"],
                   pid_i_clamp=c["i_clamp"], pid_p_clamp=c["p_clamp"], sum_clamp=c["sum_clamp"], out_lag_a=c["lag_a"],
                   out_lag_b=c["lag_b"], lkas_forward_gain=c["gain"], out_clamp=c["t_clamp"],
                   assist_map_x=tuple(c["map_x"]), assist_map_y=tuple(c["map_y"]))


rng = np.random.default_rng(7)
for nm, c in (("V294", c294), ("cand", cc), ("V282", c282)):
    cal = gcal(c)
    L = A.MyLane(c)
    st = M.EpsState()
    N = 20000
    mism = 0
    wire = 0
    x = 0
    for n in range(N):
        if n % 10 == 0:
            wire = int(np.clip(wire + rng.integers(-150, 151), -3900, 3900))
            idx, sp = L.demand(wire)
        x = int(np.clip(x + rng.integers(-60, 61), -11000, 11000))
        T, _ = L.tick(x, sp, idx)
        fb = M.lkas_fb_lag(x, st, cal)
        r = M.lkas_rate_pid_tick(sp, fb, idx, st, cal, pol=1, taper=254)
        mism += int(r["T"] != T)
    print("lane vs golden %s: %d mismatching T of %d ticks" % (nm, mism, N))
