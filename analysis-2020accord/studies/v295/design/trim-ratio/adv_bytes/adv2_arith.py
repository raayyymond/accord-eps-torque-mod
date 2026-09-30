# -*- coding: utf-8 -*-
"""adv2_arith.py -- ADV bytes+instrument: the integer arithmetic of V294 + b 964 on the adversary's OWN mirror.

 (1) cross-check the mirror: vs the harness Lane (random ticks, b 567 and 964) and vs plib's march of r71b (b 567, 1.02 M
     ticks, bit-exact required)                                                         [two independent implementations]
 (2) the fb state supremum at |x| = 12000 under the floor asymmetry, both signs; every int32 margin; adversarial x
     sequences (square waves at every period 2..400 ticks, full swing +-12000) to hunt a transient above the fixed point
 (3) the delivered surface at x = 0, 241 idx x 5 taper states, both signs, b 567 vs 964: equality, monotonicity, rail
 (4) constant-rate turns: steady r26 == 0 at constant x for b 964 (the trim has no DC), 49 x values
 (5) zero-command torque with r26 pinned at +-C (steady), and the largest |T| at idx 0 over a max-acceleration chirp
 (6) restart pulse after a one-tick bail at 10/30/100/300 deg/s: peak |dT| and duration > 50 T
 (7) |P/x| at 20 Hz (time-domain sinusoid) and K_alpha (constant-alpha ramp), b 567 / 964
"""
import math
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import adv_mirror as AM  # noqa: E402

c294 = AM.load_cells()
assert c294["sha"] == "3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85"
c964 = dict(c294, b=964)
print("cells from the V294 image: a %d b %d C %d shl %d op %s Kp %s map %s/%s Pcl %d Scl %d la %d lb %d gain %d Tcl %d"
      % (c294["a"], c294["b"], c294["C"], c294["shl"], c294["op"], c294["kpY"], c294["mapX"], c294["mapY"], c294["Pcl"],
         c294["Scl"], c294["la"], c294["lb"], c294["gain"], c294["Tcl"]))
print("taper B %s/%s  taper D %s/%s" % (c294["tBX"], c294["tBY"], c294["tDX"], c294["tDY"]))

# ------------------------------------------------------------------ (1a) vs the harness Lane
sys.path.insert(0, os.path.join(HERE, "..", "..", "harness"))
import v295_harness as H  # noqa: E402

rng = random.Random(7)
bad = 0
nt = 0
for bb in (567, 964):
    hc = H.Cells.v294().replace(fb_b=bb)
    HL = H.Lane([hc])
    ML = AM.Lane(dict(c294, b=bb))
    x = 0
    for k in range(3000):
        if k % 10 == 0:
            idx = rng.randrange(0, 241)
            sgn = rng.choice((-1, 1))
            sp = sgn * ML.map[idx]
            F = rng.choice((254, 254, 254, 178, 76, 203))
        x = max(-12000, min(12000, x + rng.randint(-400, 400))) if rng.random() > 0.002 else rng.choice((0, 12000, -12000, 900))
        t_h, _ = HL.tick(np.array([x]), np.array([sp]), np.array([idx]), np.array([F]))
        t_m = ML.tick(x, sp, idx, F)
        nt += 1
        if int(t_h[0]) != t_m:
            bad += 1
print("\n(1a) mirror vs harness Lane: %d random ticks (b 567 and 964, all 241 idx, tapers 254/178/76/203): %d mismatches"
      % (nt, bad))

# ------------------------------------------------------------------ (1b) vs plib's march on r71b (b 567), full route
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "plant"))
import plib as P  # noqa: E402

d = P.load()
x1k = np.clip(np.round(d["x1k"]), -12000, 12000).astype(int).tolist()
sgn = d["sgn"].astype(int).tolist()
idx = d["idx"].astype(int).tolist()
m = d["m"].astype(int).tolist()
T567 = np.zeros(len(x1k), np.int64)
T964 = np.zeros(len(x1k), np.int64)
R964 = np.zeros(len(x1k), np.int32)
L1, L2 = AM.Lane(c294), AM.Lane(c964)
for i in range(len(x1k)):
    k = i // 10
    sp1 = sgn[k] * L1.map[idx[k]]
    T567[i] = L1.tick(x1k[i], sp1, idx[k], m[k])
    T964[i] = L2.tick(x1k[i], sp1, idx[k], m[k])
    R964[i] = L2.r26
eq = np.array_equal(d["sg"] * T567, d["T1k_live"].astype(np.int64))
print("(1b) mirror b567 march of r71b (%d ticks) == plib T1k_live bit for bit: %s ; max |a*s| seen b567 %d b964 %d ; "
      "max |x*b| b964 %d" % (len(x1k), eq, L1.max_as, L2.max_as, L2.max_bx))
np.savez_compressed(os.path.join(HERE, "_adv_march_r71b.npz"), T567=T567, T964=T964, R964=R964, sg=d["sg"])
eng1k = np.repeat(d["eng"], 10)[:len(x1k)]
print("     r71b engaged ticks: |r26| == C (1024) for b964 on %.5f %% ; max |T| b567 %d b964 %d ; p99.99 |T-T567| %.0f max %d"
      % (100 * np.mean(np.abs(R964[eng1k]) >= 1024), np.abs(T567[eng1k]).max(), np.abs(T964[eng1k]).max(),
         np.percentile(np.abs(T964 - T567)[eng1k], 99.99), np.abs(T964 - T567)[eng1k].max()))

# ------------------------------------------------------------------ (2) fb state supremum, int32
print("\n(2) fb state at the bail edge and adversarial sequences")
for bb in (567, 964, 1134, 2301):
    for xs in (12000, -12000):
        Lx = AM.Lane(dict(c294, b=bb))
        prev = None
        for k in range(20000):
            try:
                Lx.fb(xs)
            except AM.Ovf as e:
                print("   b %4d x %+6d : OVERFLOW %s" % (bb, xs, e))
                break
            if Lx.s == prev:
                break
            prev = Lx.s
        prod = abs(c294["a"] * Lx.s)
        print("   b %4d x %+6d : fixed point s* %+d after %d ticks ; |a*s*| %d ; int32 margin 2^31/|a*s| = %.3f"
              % (bb, xs, Lx.s, k, prod, (1 << 31) / max(1, prod)))
# adversarial: square waves of every half-period 1..400 ticks at +-12000, and a random walk at full swing
worst = 0
for hp in list(range(1, 60)) + list(range(60, 401, 7)):
    Lx = AM.Lane(c964)
    for k in range(6000):
        Lx.fb(12000 if (k // hp) % 2 == 0 else -12000)
    worst = max(worst, Lx.max_as)
Lx = AM.Lane(c964)
for k in range(200000):
    Lx.fb(rng.choice((12000, -12000, 12000, 11999, -12000)))
worst = max(worst, Lx.max_as)
print("   b 964 adversarial square waves (half-periods 1..400) + 200k random full-swing ticks: max |a*s_old| %d "
      "-> margin %.3f (no Ovf raised)" % (worst, (1 << 31) / worst))

# ------------------------------------------------------------------ (3) surface at x = 0
print("\n(3) delivered surface T(idx) at x = 0, steady (4000 ticks), 241 idx x tapers x both signs")


def steady_T(c, sp, idx, F, x=0, n=4000):
    Lx = AM.Lane(c)
    T = None
    for _ in range(n):
        T = Lx.tick(x, sp, idx, F)
    return T, Lx


Fs = sorted({((f1 * f2) & 0xFFFF) >> 8 for f1 in (255, 205) for f2 in (255, 243, 218, 179, 77)})
diffs = 0
nonmono = {567: 0, 964: 0}
rail = {}
for F in Fs:
    for sg in (1, -1):
        prevT = {567: None, 964: None}
        for i in range(0, 241):
            for bb, c in ((567, c294), (964, c964)):
                T, _ = steady_T(c, sg * AM.lerp(c["mapX"], c["mapY"], i), i, F, n=600)
                if prevT[bb] is not None and sg * T < sg * prevT[bb]:
                    nonmono[bb] += 1
                prevT[bb] = T
                if bb == 567:
                    t567 = T
                else:
                    if T != t567:
                        diffs += 1
                if i == 240 and F == 254:
                    rail[(bb, sg)] = T
print("   taper states %s ; points %d ; b964 != b567 at %d points ; non-monotone steps b567 %d b964 %d ; rail %s"
      % (Fs, len(Fs) * 2 * 241, diffs, nonmono[567], nonmono[964], rail))

# ------------------------------------------------------------------ (4) constant-rate turns: r26 -> 0 exactly
nz = 0
for xv in list(range(-12000, 12001, 500)):
    Lx = AM.Lane(c964)
    for _ in range(3000):
        Lx.fb(xv)
    r = Lx.fb(xv)
    nz += (r != 0)
print("\n(4) b964 constant x (49 values -12000..12000): steady r26 != 0 in %d cases (0 = the trim has no DC)" % nz)

# ------------------------------------------------------------------ (5) zero-command torque
print("\n(5) zero command (idx 0, sp 0), r26 pinned at +-C:")


class Pin(AM.Lane):
    def fb(self, x):
        return x


for C in (1024,):
    for r in (C, -C):
        Lx = Pin(c964)
        for _ in range(4000):
            T = Lx.tick(r, 0, 0, 254)
        print("   r26 %+d -> steady T %+d" % (r, T))
# reachability of the cap: a max-acceleration chirp at idx 0 through the real fb former
for bb, c in ((567, c294), (964, c964)):
    Lx = AM.Lane(c)
    mx = 0
    for k in range(20000):
        f = 0.2 + 20 * k / 20000
        xv = int(round(2400 * math.sin(2 * math.pi * (0.2 * k / 1000 + 10 * (k / 1000) ** 2 / 20))))
        T = Lx.tick(xv, 0, 0, 254)
        mx = max(mx, abs(T))
    print("   b %d: max |T| at zero command over a 300 deg/s-amplitude chirp 0.2-20 Hz: %d" % (bb, mx))

# ------------------------------------------------------------------ (6) restart pulse
print("\n(6) restart pulse: steady rotation at w deg/s (x = 8w), idx 60 held, then ONE bail tick (|x| > 12000 or a guard)")
for bb, c in ((567, c294), (964, c964)):
    row = []
    for w in (10, 30, 100, 300):
        xv = 8 * w
        sp = AM.lerp(c["mapX"], c["mapY"], 60)
        La = AM.Lane(c)
        Lb = AM.Lane(c)
        for _ in range(5000):
            La.tick(xv, sp, 60)
            Lb.tick(xv, sp, 60)
        pk, dur = 0, 0
        for k in range(2000):
            ta = La.tick(xv, sp, 60)
            tb = Lb.tick(20000 if k == 0 else xv, sp, 60)      # one bail tick then the restart
            dd = abs(tb - ta)
            pk = max(pk, dd)
            dur += dd > 50
        row.append("%d deg/s: peak %d T, >50 T for %d ms" % (w, pk, dur))
    print("   b %d: %s" % (bb, " | ".join(row)))

# ------------------------------------------------------------------ (7) |P/x| at 20 Hz and K_alpha
print("\n(7) linear gains by time-domain march")
for bb, c in ((567, c294), (964, c964)):
    Lx = AM.Lane(c)
    A = 2000
    ps, xs = [], []
    for k in range(4000):
        xv = int(round(A * math.sin(2 * math.pi * 20 * k / 1000)))
        Lx.tick(xv, 0, 60)
        if k >= 2000:
            ps.append(Lx.P)
            xs.append(xv)
    ps, xs = np.array(ps, float), np.array(xs, float)
    ph = np.exp(-2j * math.pi * 20 * np.arange(len(ps)) / 1000)
    gpx = abs(np.sum(ps * ph)) / abs(np.sum(xs * ph))
    # K_alpha: constant alpha ramp (deg/s^2) at idx 60, trim torque = T(ramp) - T(no trim) after settling
    al = 200.0
    La = AM.Lane(c)
    Ln = AM.Lane(dict(c, C=0))
    sp = AM.lerp(c["mapX"], c["mapY"], 60)
    for k in range(3000):
        xv = int(round(8 * al * k / 1000))
        ta = La.tick(xv, sp, 60)
        tn = Ln.tick(xv, sp, 60)
    print("   b %d: |P/x| at 20 Hz = %.3f ; K_alpha (ramp %.0f deg/s^2, 3 s) = %.4f T per deg/s^2"
          % (bb, gpx, al, abs(ta - tn) / al))
