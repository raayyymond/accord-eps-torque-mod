# -*- coding: utf-8 -*-
"""ADV-A a3: int32 hunt.  Exact integer fixed points of s' = (a*s>>10) + (b*x>>10) at |x| = 12000 (= 1500.0 deg/s, the
guard AND the plausibility bound, x = 8 counts per deg/s), the reachable-set bound by monotonicity, a hostile
trajectory search (reversals at the guard), every other 32-bit product's reachable worst case, and the b at which
margin 2.0 / 1.0 is lost."""
import json, os, sys, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import advA_lane as A  # noqa: E402

J = json.load(open(os.path.join(HERE, "a1_cells.json")))
I32 = 2 ** 31


def fp(a, b, x, s0=0, n=400000):
    """iterate from s0 until repeat; returns (settled s, max |s| on the way, max |a*s| on the way, ticks)"""
    s, seen, mx, mas = s0, set(), abs(s0), abs(a * s0)
    for k in range(n):
        s2 = ((a * s) >> 10) + ((b * x) >> 10)
        mas = max(mas, abs(a * s))
        if s2 == s:
            return s, mx, mas, k
        s = s2; mx = max(mx, abs(s))
    raise RuntimeError("no fixed point")


for nm in ("v294", "v295"):
    c = J[nm]; a, b = c["fb_a"], c["fb_b"]
    sp_, _, masp, kp_ = fp(a, b, 12000); sm_, _, masm, km_ = fp(a, b, -12000)
    worst = max(abs(a * sp_), abs(a * sm_))
    print("%s a=%d b=%d: s*(+12000)=%d (%d ticks) s*(-12000)=%d (%d ticks); max|a*s|=%d margin %.4f ; |b*x|max=%d"
          % (nm, a, b, sp_, kp_, sm_, km_, worst, I32 / worst, b * 12000))
    # monotonicity: s' is non-decreasing in s and in x (a>0, b>0, floor monotone) -> reachable s from 0 is within [s*-, s*+]
    ok = all(((a * s) >> 10) <= ((a * (s + 1)) >> 10) for s in range(-1_000_000, 1_000_000, 997)) and a > 0 and b > 0
    print("   monotone in s (sampled 2006 points) and a,b > 0:", ok)
    # also: s* is an ATTRACTOR from ABOVE -- could any state above s*+ be reachable? only if s0 > s*+; s boots 0 and
    # restarts at 0 (sentinel), so no.  Check that from s0 = s*+ + 1e5 the orbit decays (contraction) anyway:
    sh, mxh, mash, _ = fp(a, b, 12000, s0=sp_ + 100000)
    print("   from s0 = s*+ + 100000: settles %d, max|a*s| on the way %d (margin %.3f)" % (sh, mash, I32 / mash))

# hostile trajectories on V295: random reversals/steps at the guard, 200 x 20000 ticks, scalar mirror
c5 = J["v295"]
rng = random.Random(7)
L = A.Lane(c5)
mx = {}
for trial in range(200):
    L.reset()
    x = 12000
    for k in range(20000):
        if rng.random() < 0.002:
            x = -x
        if rng.random() < 0.0005:
            x = rng.choice((12000, -12000, 12001, 0))      # includes bails
        L.tick(x, L.sp_of(240, rng.choice((1, -1))), 240, pol=1)
        for kk in ("bx", "as", "pp", "mS", "S_lb", "la_o", "y_ramp", "y_gain"):
            if kk in L.last:
                mx[kk] = max(mx.get(kk, 0), abs(L.last[kk]))
print("V295 hostile march (200 x 20000 ticks, reversals at +-12000, bails): max |product|:")
for k, v in mx.items():
    print("   %-7s %12d  margin %.3f" % (k, v, I32 / v if v else float("inf")))

# every other product's analytic worst case (b-independent except a*s via s, b*x)
c = c5
E_max = (max(c["map_y"]) << c["e_shift"]) + c["fb_clamp"]
print("E max |4*1032 + 1024| = %d ; E*Kp = %d (margin %.1f)" % (E_max, E_max * max(c["kp_y"]), I32 / (E_max * max(c["kp_y"]))))
S_max = (255 * c["p_clamp"]) >> 8
o_max = c["sum_clamp_u"] * c["lag_b"] / (1024 - c["lag_a"])
print("taper*P max 255*%d = %d ; S*lb max %d ; la*o max ~%d (o <= %.0f) ; y*ramp max ~%d"
      % (c["p_clamp"], 255 * c["p_clamp"], c["sum_clamp_u"] * c["lag_b"], int(c["lag_a"] * o_max), o_max,
         int(2 * o_max / 32 * 0x8000)))

# b at which the margin 2.0 and 1.0 are lost at a = 1011
a = c5["fb_a"]
def margin(b):
    sp_, _, _, _ = fp(a, b, 12000); sm_, _, _, _ = fp(a, b, -12000)
    return I32 / max(abs(a * sp_), abs(a * sm_))
for target in (2.0, 1.0):
    lo, hi = 567, 4000
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if margin(mid) >= target:
            lo = mid
        else:
            hi = mid
    print("largest b with margin >= %.1f at a=%d: %d (margin %.4f); b+1 -> %.4f" % (target, a, lo, margin(lo), margin(lo + 1)))
print("margin at b=1050: %.4f ; b=1051: %.4f" % (margin(1050), margin(1051)))
