# -*- coding: utf-8 -*-
"""ab2_arith.py -- ADV bytes: the integer arithmetic of candidate A (b 1106) vs V294 (b 567) on MY lane (ab2_lane.py),
cross-checked against the golden model (second method) and against plib's route march (third).
  [1] my lane == golden model tick-for-tick (random ticks incl. bails/restarts), b 567 and 1106
  [2] int32: exact reachable |a*s| bound (monotone-map argument + exact fixed points), margin, b for margin 2.0 / 1.0
  [3] the delivered surface at all 241 idx x both signs x constant wheel rate: A vs V294, incl. the output-lag
      fixed-point-interval trajectory dependence
  [4] the rail (P-clamp) and the zero-command trim cap with r26 forced to +-C
  [5] the restart pulse after a filter bail, several rates, peak and time above 50 T
  [6] floor-asymmetry DC bias under zero-mean x noise
  [7] r71b: my V294 march == plib T1k_live (1.02 M ticks); clamp/rail/int32 census V294 vs A on the real route
ANALYSIS ONLY."""
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ab2_lane as AL  # noqa: E402

KIT = "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, KIT + "/analysis-2020accord/model")
from dataclasses import replace  # noqa: E402
import eps_chain_core as EC  # noqa: E402
import eps_chain_control as ECC  # noqa: E402

c294 = AL.cells()
cA = AL.cells(b_override=1106)
print("cells from image: a %d b %d C %d shl %d op %s Kp %d Pcl %d Scl %d lag %d/%d gain %d lane %d taper_rest %d"
      % (c294["a"], c294["b"], c294["C"], c294["shl"], c294["op"], c294["Kp"], c294["Pcl"], c294["Scl"], c294["la"],
         c294["lb"], c294["gain"], c294["lane"], c294["taper_rest"]))
print("map rec 0x%X X %s Y %s ; Kp rec 0x%X %s" % (c294["map_rec"], c294["mapX"], c294["mapY"], c294["kp_rec"], c294["kpY"]))

# ------------------------------------------------------------------ [1] vs golden model
def golden_cal(b):
    v293 = replace(EC.Calibration(), fb_clamp=0, kd_y=(0, 0, 0, 0), pid_d_clamp=0, kp_y=(120,) * 5)
    return replace(v293, fb_clamp=1024, fb_lag_a=1011, fb_lag_b=b, kp_y=(960,) * 5, fb_op="diff", e_shift=2)


def cross(b, n=40000, seed=1):
    rng = random.Random(seed)
    c = AL.cells(b_override=b)
    me = AL.Lane(c)
    cal = golden_cal(b)
    st = EC.EpsState()
    live = False
    mism = 0
    x = 0
    idx = 0
    for i in range(n):
        if i % 10 == 0:
            idx = rng.randrange(0, 241)
            sgn = rng.choice((-1, 1))
        x = max(-12000, min(12000, x + rng.randint(-60, 60))) if rng.random() > 0.001 else rng.randint(-12000, 12000)
        bail = rng.random() < 0.0005
        sp = sgn * c["SP"][idx]
        taper = rng.choice((254, 254, 254, 179, 77, 0, 205))
        T, r26, P, S = me.tick(x, sp, taper=taper, bail=bail)
        if bail:
            ECC.lkas_output_lag(0, st, cal)
            live = False
            gT = None
        else:
            fb = ECC.lkas_fb_lag(x, st, cal, lane_live=live)
            live = True
            g = ECC.lkas_rate_pid_tick(sp, fb, idx, st, cal, taper=taper)
            gT = g["T"]
            if (gT, fb, g["P"], g["S"]) != (T, r26, P, S):
                mism += 1
        if bail and me.L != st.out_lag_s:
            mism += 1
    return mism


for b in (567, 1106):
    print("[1] my lane vs golden model, b %d: %d mismatches in 40,000 ticks (random x walk, bails 0.05 %%, tapers)" % (b, cross(b)))

# ------------------------------------------------------------------ [2] int32
def fixed_point(a, b, x):
    s = 0
    for _ in range(400000):
        sn = ((a * s) >> 10) + ((x * b) >> 10)
        if sn == s:
            return s
        s = sn
    raise RuntimeError


for b in (567, 1106, 1134, 1150):
    lo, hi = fixed_point(1011, b, -12000), fixed_point(1011, b, 12000)
    m = max(abs(1011 * lo), abs(1011 * hi))
    print("[2] b %4d: s fixed points at x=-12000/+12000: %d / %d ; max|a*s| %d ; int32 margin %.3f"
          % (b, lo, hi, m, (2 ** 31 - 1) / m))
# largest b with margin >= 2 and >= 1 (exact)
for target in (2.0, 1.0):
    bb = 567
    while True:
        lo = fixed_point(1011, bb + 1, -12000)
        if (2 ** 31 - 1) / abs(1011 * lo) < target:
            break
        bb += 1
    print("[2] largest b with int32 margin >= %.1f at a 1011: %d" % (target, bb))
# monotone-map check: random bounded x walks never exceed the fixed points
cA_l = AL.Lane(cA)
rng = random.Random(7)
lo, hi = fixed_point(1011, 1106, -12000), fixed_point(1011, 1106, 12000)
viol = 0
for i in range(200000):
    x = rng.choice((12000, -12000, rng.randint(-12000, 12000)))
    cA_l.fb(x)
    if not (lo <= cA_l.s <= hi):
        viol += 1
print("[2] 200,000 adversarial ticks (x in {+-12000, random}): state outside [%d, %d]: %d ; max|a*s| seen %d ; wraps %d"
      % (lo, hi, viol, cA_l.max_as, cA_l.wrap))

# ------------------------------------------------------------------ [3] surface
def settle(c, idx, sgn, x, ticks=6000):
    L = AL.Lane(c)
    T = None
    for _ in range(ticks):
        T, r26, P, S = L.tick(x, sgn * c["SP"][idx])
    return T, r26


diffs = []
for x in (0, 800, -800, 12000, -12000):
    nd = 0
    worst = 0
    for idx in range(241):
        for sgn in (1, -1):
            t0, r0 = settle(c294, idx, sgn, x)
            t1, r1 = settle(cA, idx, sgn, x)
            if t0 != t1 or r0 != 0 or r1 != 0:
                nd += 1
                worst = max(worst, abs(t0 - t1))
    diffs.append((x, nd, worst))
    print("[3] constant x=%6d: idx x sign cells where settled T(A) != T(V294) or r26 != 0: %d of 482 (worst |dT| %d)" % (x, nd, worst))
# monotonicity of the V294(=A) surface
Ts = [settle(cA, i, 1, 0)[0] for i in range(241)]
Tn = [settle(cA, i, -1, 0)[0] for i in range(241)]
mono = all(Ts[i + 1] <= Ts[i] for i in range(240)) or all(Ts[i + 1] >= Ts[i] for i in range(240))
monon = all(Tn[i + 1] <= Tn[i] for i in range(240)) or all(Tn[i + 1] >= Tn[i] for i in range(240))
print("[3] A surface at x=0: T(idx 0/60/120/180/240) = %s / %s ; monotone: + %s, - %s ; rail + %d - %d"
      % ([Ts[i] for i in (0, 60, 120, 180, 240)], [Tn[i] for i in (0, 60, 120, 180, 240)], mono, monon, max(Ts + Tn), min(Ts + Tn)))

# ------------------------------------------------------------------ [4] rail and trim cap with r26 forced
def forced(c, idx, sgn, r26, ticks=4000):
    L = AL.Lane(c)
    T = None
    for _ in range(ticks):
        T, _, P, S = L.tick(0, sgn * c["SP"][idx], fb_force=r26)
    return T


rail = []
for c, nm in ((c294, "V294"), (cA, "A")):
    vals = [forced(c, i, s, r) for i in (0, 120, 179, 200, 240) for s in (1, -1) for r in (-1024, 0, 1024)]
    print("[4] %s: max/min T over idx {0,120,179,200,240} x sign x r26 {-C,0,+C}: %+d / %+d ; zero-command T at r26=+-C: %+d / %+d"
          % (nm, max(vals), min(vals), forced(c, 0, 1, 1024), forced(c, 0, 1, -1024)))

# ------------------------------------------------------------------ [5] restart pulse
def restart(c, X, idx=0, sgn=1, pre=3000, post=1500):
    L = AL.Lane(c)
    for _ in range(pre):
        T_ff, _, _, _ = L.tick(X, sgn * c["SP"][idx])
    L.tick(X, sgn * c["SP"][idx], bail=True)
    tr = []
    for _ in range(post):
        T, r26, P, S = L.tick(X, sgn * c["SP"][idx])
        tr.append(T - T_ff)
    tr = np.array(tr)
    return int(np.max(np.abs(tr))), int(np.sum(np.abs(tr) > 50)), T_ff


for X in (80, 240, 800, 2400, 12000):
    r0, rA = restart(c294, X), restart(cA, X)
    r0b, rAb = restart(c294, X, idx=120), restart(cA, X, idx=120)
    print("[5] restart after one bail tick, x=%5d (%6.0f deg/s): peak |dT| V294 %4d (%3d ms > 50 T)  A %4d (%3d ms) ;"
          " at idx 120: V294 %4d  A %4d" % (X, X / 8.0, r0[0], r0[1], rA[0], rA[1], r0b[0], rAb[0]))

# ------------------------------------------------------------------ [6] DC bias from floors
rng = np.random.default_rng(3)
for sig in (1, 4, 16):
    xs = np.round(rng.normal(0, sig, 20000)).astype(int).tolist()
    for idx in (0, 120):
        m = []
        for c in (c294, cA):
            L = AL.Lane(c)
            acc = [L.tick(x, c["SP"][idx])[0] for x in xs]
            m.append(np.mean(acc[2000:]))
        print("[6] x ~ N(0,%2d) 20 s, idx %3d: mean T V294 %.3f  A %.3f  (A - V294 %+.3f T)" % (sig, idx, m[0], m[1], m[1] - m[0]))

# ------------------------------------------------------------------ [7] r71b
d = np.load(KIT + "/analysis-2020accord/studies/v295/plant/_scratch/cache/plant_r71b_v294.npz")
x1k = np.clip(np.round(d["x1k"]), -12000, 12000).astype(np.int64).tolist()
idx100, sgn100, m100 = d["idx"], d["sgn"], d["m"]
sg = int(d["sg"])
res = {}
for c, nm in ((c294, "V294"), (cA, "A")):
    r26, mx = AL.r26_series(x1k, c)
    r26 = np.array(r26, dtype=np.int64)
    sp1k = np.repeat(sgn100 * np.array(c["SP"])[idx100], 10)[: len(r26)]
    m1k = np.repeat(m100, 10)[: len(r26)]
    E = (sp1k << c["shl"]) - r26
    Praw = (E * c["Kp"]) >> 8
    P = np.clip(Praw, -c["Pcl"], c["Pcl"])
    S = np.clip((P * m1k) >> 8, -c["Scl"], c["Scl"])
    T = np.array(AL.lag_series(S.tolist(), c), dtype=np.int64)
    res[nm] = dict(T=T, r26=r26, Praw=Praw, P=P, mx=mx)
eng = np.repeat(d["eng"], 10)[: len(res["V294"]["T"])]
same = np.array_equal(sg * res["V294"]["T"], d["T1k_live"].astype(np.int64))
print("[7] my V294 route march == plib T1k_live on all %d ticks: %s ; == plib r26_1k: %s"
      % (len(eng), same, np.array_equal(res["V294"]["r26"], d["r26_1k"].astype(np.int64))))
for nm in ("V294", "A"):
    r = res[nm]
    e = eng
    print("[7] %-4s engaged ticks %d: |r26|==C %.4f %% ; P at clamp %.4f %% ; |T|>=2000 %.4f %% ; |T|>=2400 %.4f %% ;"
          " max|T| %d ; p99.9 |r26| %d ; max |a*s| on route %d (margin %.1f)"
          % (nm, e.sum(), 100 * np.mean(np.abs(r["r26"][e]) >= 1024), 100 * np.mean(np.abs(r["Praw"][e]) > 15360),
             100 * np.mean(np.abs(r["T"][e]) >= 2000), 100 * np.mean(np.abs(r["T"][e]) >= 2400), np.max(np.abs(r["T"][e])),
             np.percentile(np.abs(r["r26"][e]), 99.9), r["mx"], (2 ** 31 - 1) / max(1, r["mx"])))
dT = (res["A"]["T"] - res["V294"]["T"])[eng]
print("[7] A - V294 delivered torque on the recorded motion (engaged): rms %.2f T, p99 %.1f, max %d"
      % (np.sqrt(np.mean(dT ** 2.0)), np.percentile(np.abs(dT), 99), np.max(np.abs(dT))))
np.savez_compressed(os.path.join(HERE, "_scratch_ab2_route.npz"), T294=res["V294"]["T"].astype(np.int32),
                    TA=res["A"]["T"].astype(np.int32), r294=res["V294"]["r26"].astype(np.int32), rA=res["A"]["r26"].astype(np.int32))
