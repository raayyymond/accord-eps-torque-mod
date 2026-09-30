"""ADV-bytes step 4: the integer arithmetic of A1017 re-derived with MY OWN mirror (pure Python ints, written from the
Ghidra listing 0x28F4C..0x28FBE read this session and the census section 2 for the rest), then spot-checked against
the shared harness Lane and the golden model.  Every cal is read from the V294 IMAGE.

(1) spot-check: my tick == harness Lane tick == golden model, random inputs, a = 1011 and 1017
(2) int32: exact worst-case |a*s| (integer fixed point at x = +-12000, and the invariant-interval argument)
(3) settling: every x in [-12000, 12000] -> r26 settles to exactly 0 (no dither) at a = 1017 (and 1011)
(4) restart pulse (bail -> s_old := 0) at 10/30/100/300 deg/s: peak |T|, ms above 50 T
(5) delivered surface at constant rate: T(idx) for all 241 idx at x = 0 and x = const, both a; rail
(6) HF: |r26/x| ratio A1017/V294 at 5-30 Hz (closed form of the integer filter's linear part)
"""
import math, os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
IMG = ("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-"
       "FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
B = open(IMG, "rb").read()
s16 = lambda a: struct.unpack_from("<h", B, a)[0]
u16 = lambda a: struct.unpack_from("<H", B, a)[0]
u32 = lambda a: struct.unpack_from("<I", B, a)[0]
I32 = 1 << 31

def rec(bank, sel=7):
    r = u32(bank + 4 * sel); n = u16(r)
    return [u16(r + 2 + 2 * i) for i in range(n)], [u16(r + 2 + 2 * n + 2 * i) for i in range(n)]

def lerp(X, Y, v):     # firmware LERP: flat outside, trunc-toward-zero divide (golden model lkas_rate_lerp)
    if v <= X[0]: return Y[0]
    if v >= X[-1]: return Y[-1]
    i = 1
    while X[i] <= v: i += 1
    num = (Y[i] - Y[i - 1]) * (v - X[i - 1]); den = X[i] - X[i - 1]
    q = abs(num) // den
    return Y[i - 1] + (q if num >= 0 else -q)

CAL = dict(a=s16(0xC63E8), b=u16(0xC63EA), C=u16(0xC62E6), la=s16(0xC63EC), lb=u16(0xC63EE), pcl=u16(0xC61BC),
           scl=u16(0xC61BE), tcl=u16(0xC61B4), gain=s16(0xBF000 + u16(0x2A1F0)))
KPX, KPY = rec(0xCB994); MAPX, MAPY = rec(0xC9A88)
esh = u16(0x29D76) & 0x1F
print("cells read from the V294 image:", CAL, "Kp", KPX, KPY, "map", MAPX, MAPY, "e_shift", esh)
assert CAL["a"] == 1011 and CAL["b"] == 567 and esh == 2

def wrap(v): return ((v + I32) % (1 << 32)) - I32

class Mine:
    """my own mirror: fb former (listing 0x28F4C..0x28FBE, subr), E = sp<<2 - r26, P = clamp(E*Kp>>8), Ki = Kd = 0,
    S = clamp(m*P>>8), output lag, T = clamp(y*gain>>15).  wrap() models the 32-bit low word; `ovf` records any wrap."""
    def __init__(s, a): s.a, s.s, s.restart, s.o, s.ovf = a, 0, False, 0, []
    def tick(s, x, sp, idx, m=254):
        c = CAL
        if abs(x) > 12000:                    # bail: s untouched, sentinel 2, PID skipped, S = 0 into the lag
            s.restart = True; S = 0; r26 = 0
        else:
            s_old = 0 if s.restart else s.s
            p1 = s.a * s_old; p2 = x * c["b"]
            if wrap(p1) != p1 or wrap(p2) != p2: s.ovf.append(("a*s", p1))
            s_new = (wrap(p1) >> 10) + (wrap(p2) >> 10)
            r26 = s_new - s_old
            s.s = s_new; s.restart = False
            r26 = max(-c["C"], min(c["C"], r26))
            E = (sp << esh) - r26
            P = max(-c["pcl"], min(c["pcl"], (E * lerp(KPX, KPY, idx)) >> 8))
            S = max(-c["scl"], min(c["scl"], (m * P) >> 8))
        o2 = ((c["la"] * s.o) >> 10) + ((S * c["lb"]) >> 10)
        y = (s.o + o2) >> 5; s.o = o2
        T = max(-c["tcl"], min(c["tcl"], (y * c["gain"]) >> 15))
        return T, r26

out = []
def pr(*a):
    t = " ".join(str(v) for v in a); print(t); out.append(t)

# ---------------- (1) spot-check vs the harness Lane and the golden model
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
import v295_harness as H  # noqa: E402
import eps_lkas_chain_model as GM  # noqa: E402
base = H.Cells.v294()
rng = np.random.default_rng(1)
for a in (1011, 1017):
    c = base.replace(fb_a=a, name="a%d" % a)
    L = H.Lane([c]); me = Mine(a)
    cal = H.golden_cal(c); st = GM.EpsState()
    n = 20000; mism_h = mism_g = 0
    xs = np.cumsum(rng.integers(-40, 41, n)).clip(-11000, 11000)          # a wandering rate, occasional big jumps
    xs[rng.integers(0, n, 30)] = rng.integers(-12000, 12001, 30)
    idxs = np.repeat(rng.integers(0, 241, n // 10 + 1), 10)[:n]
    sgn = np.repeat(rng.choice([-1, 1], n // 10 + 1), 10)[:n]
    for i in range(n):
        idx = int(idxs[i]); sp = int(sgn[i]) * lerp(MAPX, MAPY, idx)
        t_me, r_me = me.tick(int(xs[i]), sp, idx)
        t_h, r_h = L.tick(np.array([xs[i]]), np.array([sp]), np.array([idx]), np.array([254]))
        if t_me != int(t_h[0]) or r_me != int(r_h[0]): mism_h += 1
    pr(f"(1) a={a}: my mirror vs harness Lane on {n} random ticks: {mism_h} mismatches (T and r26); my int32 wraps: {len(me.ovf)}")
# golden model fb former alone vs mine (the golden model has no lane-level batch; compare r26 of lkas_fb_lag)
for a in (1011, 1017):
    c = base.replace(fb_a=a); cal = H.golden_cal(c); st = GM.EpsState(); me = Mine(a); mm = 0
    xs = np.cumsum(rng.integers(-60, 61, 20000)).clip(-12000, 12000)
    for x in xs:
        r_g = GM.lkas_fb_lag(int(x), st, cal, lane_live=True)
        s_old = me.s; p = (a * s_old >> 10) + (int(x) * 567 >> 10); r = max(-1024, min(1024, p - s_old)); me.s = p
        mm += (r != r_g)
    pr(f"    a={a}: my fb former vs golden lkas_fb_lag on 20000 ticks: {mm} mismatches")

# ---------------- (2) int32 worst case: integer fixed point at x = +-12000, reached from s = 0 (monotone)
for a in (1011, 1017, 1018, 1020):
    ext = {}
    for x in (12000, -12000):
        s = 0
        for k in range(200000):
            sn = ((a * s) >> 10) + ((x * 567) >> 10)
            if sn == s: break
            s = sn
        ext[x] = (s, k)
    smax = max(abs(ext[12000][0]), abs(ext[-12000][0]))
    pr(f"(2) a={a} b=567: fixed point s(+12000) {ext[12000][0]} (tick {ext[12000][1]}), s(-12000) {ext[-12000][0]} ; "
       f"max|a*s| {a*smax:.4e} -> margin 2^31/|a*s| = {I32/(a*smax):.3f} ; closed form b_max(a) = {I32*(1024-a)/(12000*a):.0f}")
pr("    invariant: f_x(s) = floor(a s/1024) + floor(567 x/1024) is non-decreasing in s and in x, so the interval "
   "[s*(-12000), s*(+12000)] is invariant from s = 0 (boot, restart) -- |s| can never exceed the fixed point.")
# brute check: random x in [-12000,12000] for 2e6 ticks with slams between the extremes
for a in (1017,):
    s = 0; mx = 0
    xs = rng.choice([12000, -12000, 0], 400000, p=[0.45, 0.45, 0.1])
    xs = np.repeat(xs, 5)
    for x in xs:
        s = ((a * s) >> 10) + ((int(x) * 567) >> 10); mx = max(mx, abs(a * s))
    pr(f"    brute slam test a={a}: 2e6 ticks alternating +-12000 holds: max|a*s| {mx:.4e} (margin {I32/mx:.3f})")

# ---------------- (3) settling for every x
for a in (1011, 1017):
    xs = np.arange(-12000, 12001, dtype=np.int64)
    worst_settle = 0; stuck = 0
    for start in ("zero", "hi", "lo"):
        s = np.zeros_like(xs)
        if start == "hi": s[:] = 972000 if a == 1017 else 524000
        if start == "lo": s[:] = -972000 if a == 1017 else -524000
        settled = np.full(len(xs), -1)
        for k in range(8000):
            sn = ((a * s) >> 10) + ((xs * 567) >> 10)
            r = sn - s
            newly = (r == 0) & (settled < 0)
            settled[newly] = k
            s = sn
        # after settling, confirm r stays 0 for 2000 more ticks
        still = np.zeros(len(xs), bool)
        for k in range(2000):
            sn = ((a * s) >> 10) + ((xs * 567) >> 10); still |= (sn != s); s = sn
        stuck += int(np.sum(settled < 0)) + int(still.sum())
        worst_settle = max(worst_settle, int(settled.max()))
    pr(f"(3) a={a}: every x in [-12000,12000], 3 starts: r26 reaches exactly 0 and stays (x not settling / re-dithering: {stuck}); "
       f"worst ticks to exact 0: {worst_settle}")

# ---------------- (4) restart pulse (x held, lane only, sp = 0, taper 254) -- my mirror, and the harness function
for a in (1011, 1017):
    row = []
    for w in (10.0, 30.0, 100.0, 300.0):
        me = Mine(a); x = int(round(-8 * w))
        # settle the fb state at constant x first (the real pre-bail state), then force a bail tick
        for _ in range(20000): me.tick(x, 0, 0)
        me.tick(20000, 0, 0)                      # a bail tick (|x| > 12000 stands in for any of the four bail causes)
        T = [abs(me.tick(x, 0, 0)[0]) for _ in range(3000)]
        row.append(f"{w:.0f} deg/s: peak {max(T)} T, {sum(t > 50 for t in T)} ms > 50 T")
    h = H.restart_pulse(base.replace(fb_a=a))
    pr(f"(4) a={a}: mine: " + " | ".join(row))
    pr(f"    harness restart_pulse: " + " | ".join(f"{k:.0f}: peak {v['peak']}, {v['ms_above_50']} ms" for k, v in h.items()))

# ---------------- (5) delivered surface: all 241 idx, x = 0 and x = const, both a; rail
for xc in (0, 800, -2400):
    diffs = 0; rails = {}
    surf = {}
    for a in (1011, 1017):
        vals = []
        for idx in range(0, 241):
            for sg in (1, -1):
                me = Mine(a); sp = sg * lerp(MAPX, MAPY, idx)
                for _ in range(3000): T, _ = me.tick(xc, sp, idx)
                vals.append(T)
        surf[a] = vals
    diffs = sum(1 for u, v in zip(surf[1011], surf[1017]) if u != v)
    pos = surf[1011][0::2]
    mono = all(pos[i + 1] >= pos[i] for i in range(len(pos) - 1))
    pr(f"(5) constant x = {xc}: T(idx) for 241 idx x 2 signs, a 1011 vs 1017: {diffs} differ ; rail +{max(surf[1017][0::2])}/"
       f"{min(surf[1017][1::2])} ; monotone in idx (+ side): {mono}")

# ---------------- (6) HF ratio of the fb operand's linear part (b held)
for f in (2, 3, 5, 9, 13, 17, 20, 25, 30):
    z1 = np.exp(-2j * np.pi * f * 1e-3)
    h = lambda a: (567 / 1024) * (1 - z1) / (1 - a / 1024 * z1)
    rr = h(1017) / h(1011)
    pr(f"(6) f {f:>2} Hz: |r26/x| A1017/V294 = {abs(rr):.4f}, phase {math.degrees(np.angle(rr)):+.1f} deg")
open(os.path.join(HERE, "advb4_arith_out.txt"), "w").write("\n".join(out) + "\n")
